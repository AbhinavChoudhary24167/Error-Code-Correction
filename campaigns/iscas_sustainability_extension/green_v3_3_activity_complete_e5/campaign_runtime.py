"""Global wall-clock budgeting for the GREEN v3.3 campaign.

The budget belongs to the campaign, not to an individual subprocess.  A
persisted start/deadline pair is therefore the single source of truth across
all jobs and every resume invocation.  Optional per-job limits may be shorter,
but they can never extend the campaign deadline.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import time
from typing import Any, Callable, Iterable, Mapping, Sequence


CAMPAIGN_BUDGET_SECONDS = 15 * 60 * 60
BUDGET_SCOPE = "ENTIRE_CAMPAIGN"
CUTOFF_STATUS = "CAMPAIGN_RUNTIME_CUTOFF"


def _iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for attempt in range(10):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            # OneDrive/antivirus can briefly hold the destination on Windows.
            # Retrying preserves atomic replacement without weakening the
            # persisted-deadline guarantee.
            if attempt == 9:
                raise
            time.sleep(0.05 * (attempt + 1))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class CampaignDeadline:
    """An immutable, persisted campaign-level deadline."""

    start_timestamp: float
    deadline_timestamp: float
    budget_seconds: int

    @classmethod
    def create(cls, *, now: float, budget_seconds: int = CAMPAIGN_BUDGET_SECONDS) -> "CampaignDeadline":
        if budget_seconds <= 0:
            raise ValueError("campaign budget must be positive")
        if budget_seconds > CAMPAIGN_BUDGET_SECONDS:
            raise ValueError("campaign budget cannot exceed the hard 15-hour maximum")
        return cls(now, now + budget_seconds, budget_seconds)

    @classmethod
    def from_state(cls, state: Mapping[str, Any]) -> "CampaignDeadline":
        if state.get("budget_scope") != BUDGET_SCOPE:
            raise ValueError("runtime state does not describe an entire-campaign budget")
        budget = int(state["campaign_budget_seconds"])
        if budget <= 0 or budget > CAMPAIGN_BUDGET_SECONDS:
            raise ValueError("persisted campaign budget is outside the allowed 15-hour maximum")
        deadline = cls(
            _parse_iso(str(state["campaign_start_time_utc"])),
            _parse_iso(str(state["hard_deadline_utc"])),
            budget,
        )
        expected = deadline.start_timestamp + budget
        if not math.isclose(expected, deadline.deadline_timestamp, abs_tol=1e-6):
            raise ValueError("persisted hard deadline does not equal campaign start plus budget")
        return deadline

    def remaining_seconds(self, now: float) -> float:
        return max(0.0, self.deadline_timestamp - now)

    def effective_job_timeout(self, *, now: float, requested_seconds: float | None = None) -> float:
        """Clamp an optional job cap to the one campaign deadline.

        With no explicit job cap, the returned limit is exactly the remaining
        campaign time.  In particular, a new job never receives a fresh
        15-hour allowance.
        """

        remaining = self.remaining_seconds(now)
        if remaining <= 0:
            return 0.0
        if requested_seconds is None:
            return remaining
        if requested_seconds <= 0:
            raise ValueError("per-job timeout must be positive when specified")
        return min(remaining, requested_seconds)

    def to_state(self) -> dict[str, Any]:
        return {
            "budget_scope": BUDGET_SCOPE,
            "campaign_budget_seconds": self.budget_seconds,
            "campaign_start_time_utc": _iso(self.start_timestamp),
            "hard_deadline_utc": _iso(self.deadline_timestamp),
            "per_run_timeout_seconds": None,
        }


def load_or_create_state(
    state_path: Path,
    *,
    now: float | None = None,
    budget_seconds: int = CAMPAIGN_BUDGET_SECONDS,
) -> tuple[CampaignDeadline, dict[str, Any]]:
    """Load the original deadline on resume, or persist it once on first use."""

    timestamp = time.time() if now is None else now
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        deadline = CampaignDeadline.from_state(state)
        if deadline.budget_seconds != budget_seconds:
            raise ValueError(
                "refusing to reinterpret an existing campaign with a different budget; "
                f"persisted={deadline.budget_seconds}, requested={budget_seconds}"
            )
        return deadline, state

    deadline = CampaignDeadline.create(now=timestamp, budget_seconds=budget_seconds)
    state: dict[str, Any] = {
        "schema_version": 1,
        **deadline.to_state(),
        "status": "RUNNING",
        "campaign_end_time_utc": None,
        "jobs": {},
        "last_heartbeat_utc": None,
        "last_scientific_checkpoint_utc": None,
        "runtime_controller_semantics": (
            "One persisted wall-clock budget is shared by all jobs and resume invocations. "
            "Job subprocess limits are clamped to the remaining campaign time."
        ),
    }
    _atomic_json(state_path, state)
    return deadline, state


def machine_resources() -> dict[str, Any]:
    memory_bytes: int | None = None
    try:
        import psutil  # type: ignore

        memory_bytes = int(psutil.virtual_memory().total)
    except (ImportError, OSError):
        pass
    return {
        "logical_cpu_count": os.cpu_count(),
        "memory_bytes": memory_bytes,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "concurrency": 1,
    }


def _terminate(process: subprocess.Popen[Any], grace_seconds: float) -> None:
    process.terminate()
    try:
        process.wait(timeout=grace_seconds)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def write_progress(
    path: Path,
    *,
    state: Mapping[str, Any],
    deadline: CampaignDeadline,
    now: float,
    current_job: str | None,
    planned_count: int,
) -> None:
    jobs = state.get("jobs", {})
    statuses = [record.get("status") for record in jobs.values()]
    completed = sum(status in {"COMPLETED", "COMPLETED_REUSED"} for status in statuses)
    failed = sum(status == "TOOL_FAILURE" for status in statuses)
    cutoff = sum(status == CUTOFF_STATUS for status in statuses)
    completed_records = [
        record for record in jobs.values()
        if record.get("status") in {"COMPLETED", "COMPLETED_REUSED"}
    ]
    latest = completed_records[-1] if completed_records else {}
    try:
        disk = shutil.disk_usage(path.parent)
        disk_line = f"- Disk usage: `{disk.used}/{disk.total} bytes used; {disk.free} bytes free`"
    except OSError:
        disk_line = "- Disk usage: `UNAVAILABLE`"
    lines = [
        "# GREEN v3.3 campaign progress",
        "",
        f"- Campaign start: `{_iso(deadline.start_timestamp)}`",
        f"- Hard deadline: `{_iso(deadline.deadline_timestamp)}`",
        f"- Budget scope: `{BUDGET_SCOPE}`",
        f"- Elapsed seconds: `{max(0.0, now - deadline.start_timestamp):.3f}`",
        f"- Remaining seconds: `{deadline.remaining_seconds(now):.3f}`",
        f"- Current experiment: `{current_job or 'NONE'}`",
        f"- Last completed experiment: `{latest.get('job_id', 'NONE')}`",
        f"- Completed/planned: `{completed}/{planned_count}`",
        f"- Tool failures: `{failed}`",
        f"- Runtime cutoffs: `{cutoff}`",
        disk_line,
        f"- Most recent artifact: `{latest.get('completion_artifact', 'NONE')}`",
        "- Stall assessment: `NO_AUTOMATIC_STALL_EVIDENCE`",
        "",
        "A job receives only the time remaining before the shared campaign deadline; the 15-hour clock is never reset per run.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_scientific_checkpoint(
    directory: Path,
    *,
    state: Mapping[str, Any],
    deadline: CampaignDeadline,
    now: float,
    current_job: str | None,
) -> Path:
    """Write the substantive hourly checkpoint without inventing stage results."""

    jobs = list(state.get("jobs", {}).values())
    completed = [row for row in jobs if row.get("status") in {"COMPLETED", "COMPLETED_REUSED"}]
    payload = {
        "schema_version": 1,
        "timestamp_utc": _iso(now),
        "campaign_start_time_utc": _iso(deadline.start_timestamp),
        "hard_deadline_utc": _iso(deadline.deadline_timestamp),
        "elapsed_seconds": max(0.0, now - deadline.start_timestamp),
        "remaining_seconds": deadline.remaining_seconds(now),
        "current_experiment": current_job,
        "completed_experiments": [row.get("job_id") for row in completed],
        "completed_architecture_clock_seed": [
            {
                "architecture_id": row.get("architecture_id"),
                "clock_period_ns": row.get("clock_period_ns"),
                "seed": row.get("seed"),
            }
            for row in completed
            if row.get("architecture_id") is not None
        ],
        "stage_counts": {
            "synthesis": sum(bool(row.get("synthesis_complete")) for row in completed),
            "placement": sum(bool(row.get("placement_complete")) for row in completed),
            "routing": sum(bool(row.get("routing_complete")) for row in completed),
            "gds": sum(bool(row.get("gds_complete")) for row in completed),
            "timing_closed": sum(bool(row.get("timing_closed")) for row in completed),
            "activity": sum(bool(row.get("activity_complete")) for row in completed),
            "power": sum(bool(row.get("power_complete")) for row in completed),
            "e5_qualified": sum(bool(row.get("e5_qualified")) for row in completed),
        },
        "status_counts": {
            status: sum(row.get("status") == status for row in jobs)
            for status in sorted({str(row.get("status")) for row in jobs})
        },
        "new_failure": next(
            (row.get("job_id") for row in reversed(jobs) if row.get("status") == "TOOL_FAILURE"), None
        ),
        "current_blocker": None,
        "scientifically_on_track": not any(row.get("status") == "TOOL_FAILURE" for row in jobs),
        "estimated_remaining_queue_count": max(0, int(state.get("planned_job_count", 0)) - len(completed)),
        "completion_promise": None,
    }
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    output = directory / f"progress_{stamp}.json"
    _atomic_json(output, payload)
    return output


class CampaignController:
    """Sequential priority controller with one deadline for the full queue."""

    def __init__(
        self,
        *,
        state_path: Path,
        progress_path: Path,
        budget_seconds: int = CAMPAIGN_BUDGET_SECONDS,
        launch_guard_seconds: float = 300.0,
        heartbeat_seconds: float = 1800.0,
        checkpoint_seconds: float = 3600.0,
        poll_seconds: float = 5.0,
        terminate_grace_seconds: float = 30.0,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if launch_guard_seconds < 0:
            raise ValueError("launch guard cannot be negative")
        self.state_path = state_path
        self.progress_path = progress_path
        self.budget_seconds = budget_seconds
        self.launch_guard_seconds = launch_guard_seconds
        self.heartbeat_seconds = heartbeat_seconds
        self.checkpoint_seconds = checkpoint_seconds
        self.poll_seconds = poll_seconds
        self.terminate_grace_seconds = terminate_grace_seconds
        self.clock = clock

    def _save(self, state: dict[str, Any]) -> None:
        _atomic_json(self.state_path, state)

    def _cutoff_remaining(self, jobs: Iterable[Mapping[str, Any]], state: dict[str, Any], now: float) -> None:
        records = state.setdefault("jobs", {})
        for job in jobs:
            job_id = str(job["job_id"])
            if job_id not in records:
                records[job_id] = {
                    "job_id": job_id,
                    "status": CUTOFF_STATUS,
                    "classification": "UNLAUNCHED_AT_GLOBAL_DEADLINE_OR_LAUNCH_GUARD",
                    "end_time_utc": _iso(now),
                }

    def run(self, jobs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        deadline, state = load_or_create_state(
            self.state_path, now=self.clock(), budget_seconds=self.budget_seconds
        )
        state.setdefault("machine_resources", machine_resources())
        state["planned_job_count"] = len(jobs)
        last_heartbeat = self.clock()
        last_checkpoint = self.clock()

        for index, job in enumerate(jobs):
            job_id = str(job["job_id"])
            existing = state.setdefault("jobs", {}).get(job_id)
            if existing and existing.get("status") in {"COMPLETED", "COMPLETED_REUSED"}:
                continue
            completion = Path(str(job["completion_artifact"])) if job.get("completion_artifact") else None
            if completion and completion.is_file():
                state["jobs"][job_id] = {
                    "job_id": job_id,
                    "status": "COMPLETED_REUSED",
                    "completion_artifact": str(completion),
                    "completion_artifact_sha256": sha256(completion),
                    "end_time_utc": _iso(self.clock()),
                }
                self._save(state)
                continue

            now = self.clock()
            if deadline.remaining_seconds(now) <= self.launch_guard_seconds:
                self._cutoff_remaining(jobs[index:], state, now)
                state["status"] = CUTOFF_STATUS
                state["campaign_end_time_utc"] = _iso(now)
                self._save(state)
                write_progress(
                    self.progress_path, state=state, deadline=deadline, now=now,
                    current_job=None, planned_count=len(jobs),
                )
                return state

            requested_timeout = job.get("timeout_seconds")
            timeout = deadline.effective_job_timeout(
                now=now,
                requested_seconds=float(requested_timeout) if requested_timeout is not None else None,
            )
            command = [str(part) for part in job["command"]]
            log_path = Path(str(job.get("log_path", self.state_path.parent / "logs" / f"{job_id}.log")))
            log_path.parent.mkdir(parents=True, exist_ok=True)
            record: dict[str, Any] = {
                "job_id": job_id,
                "status": "RUNNING",
                "priority": job.get("priority"),
                "command": command,
                "start_time_utc": _iso(now),
                "campaign_remaining_at_launch_seconds": timeout if requested_timeout is None else deadline.remaining_seconds(now),
                "effective_subprocess_timeout_seconds": timeout,
                "requested_per_job_timeout_seconds": requested_timeout,
                "hard_deadline_utc": _iso(deadline.deadline_timestamp),
                "log_path": str(log_path),
            }
            for metadata_key in (
                "architecture_id", "clock_period_ns", "seed", "operation_class",
                "synthesis_complete", "placement_complete", "routing_complete", "gds_complete",
                "timing_closed", "activity_complete", "power_complete", "e5_qualified",
            ):
                if metadata_key in job:
                    record[metadata_key] = job[metadata_key]
            state["jobs"][job_id] = record
            self._save(state)

            cutoff = False
            per_job_timeout = False
            with log_path.open("a", encoding="utf-8", newline="\n") as log:
                try:
                    process = subprocess.Popen(
                        command,
                        cwd=str(job["cwd"]) if job.get("cwd") else None,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        text=True,
                    )
                except OSError as exc:
                    end = self.clock()
                    log.write(f"CONTROLLER_LAUNCH_ERROR: {type(exc).__name__}: {exc}\n")
                    record.update(
                        {
                            "status": "TOOL_FAILURE",
                            "classification": "PROCESS_LAUNCH_FAILURE",
                            "end_time_utc": _iso(end),
                            "elapsed_seconds": max(0.0, end - now),
                            "exit_code": None,
                        }
                    )
                    self._save(state)
                    continue
                while process.poll() is None:
                    now = self.clock()
                    if now >= deadline.deadline_timestamp:
                        cutoff = True
                        _terminate(process, self.terminate_grace_seconds)
                        break
                    if requested_timeout is not None and now >= _parse_iso(record["start_time_utc"]) + timeout:
                        per_job_timeout = True
                        _terminate(process, self.terminate_grace_seconds)
                        break
                    if now - last_heartbeat >= self.heartbeat_seconds:
                        state["last_heartbeat_utc"] = _iso(now)
                        write_progress(
                            self.progress_path, state=state, deadline=deadline, now=now,
                            current_job=job_id, planned_count=len(jobs),
                        )
                        self._save(state)
                        last_heartbeat = now
                    if now - last_checkpoint >= self.checkpoint_seconds:
                        state["last_scientific_checkpoint_utc"] = _iso(now)
                        write_scientific_checkpoint(
                            self.progress_path.parent / "progress",
                            state=state,
                            deadline=deadline,
                            now=now,
                            current_job=job_id,
                        )
                        self._save(state)
                        last_checkpoint = now
                    time.sleep(min(self.poll_seconds, max(0.01, deadline.remaining_seconds(now))))

            end = self.clock()
            record["end_time_utc"] = _iso(end)
            record["elapsed_seconds"] = max(0.0, end - _parse_iso(record["start_time_utc"]))
            record["exit_code"] = process.returncode
            if cutoff:
                record["status"] = CUTOFF_STATUS
                record["classification"] = "ACTIVE_JOB_TERMINATED_AT_GLOBAL_DEADLINE"
            elif per_job_timeout:
                record["status"] = "JOB_TIMEOUT"
                record["classification"] = "EXPLICIT_SHORTER_JOB_LIMIT_NOT_CAMPAIGN_BUDGET"
            elif process.returncode != 0:
                record["status"] = "TOOL_FAILURE"
            elif completion and not completion.is_file():
                record["status"] = "TOOL_FAILURE"
                record["classification"] = "MISSING_DECLARED_COMPLETION_ARTIFACT"
            else:
                record["status"] = "COMPLETED"
                if completion:
                    record["completion_artifact"] = str(completion)
                    record["completion_artifact_sha256"] = sha256(completion)
            self._save(state)

            if cutoff:
                self._cutoff_remaining(jobs[index + 1 :], state, end)
                state["status"] = CUTOFF_STATUS
                state["campaign_end_time_utc"] = _iso(end)
                self._save(state)
                write_progress(
                    self.progress_path, state=state, deadline=deadline, now=end,
                    current_job=None, planned_count=len(jobs),
                )
                return state

        end = self.clock()
        statuses = [item.get("status") for item in state["jobs"].values()]
        if any(status == CUTOFF_STATUS for status in statuses):
            state["status"] = CUTOFF_STATUS
        elif any(status in {"TOOL_FAILURE", "JOB_TIMEOUT"} for status in statuses):
            state["status"] = "COMPLETED_WITH_PARTIAL_FAILURES"
        else:
            state["status"] = "COMPLETED"
        state["campaign_end_time_utc"] = _iso(end)
        self._save(state)
        write_progress(
            self.progress_path, state=state, deadline=deadline, now=end,
            current_job=None, planned_count=len(jobs),
        )
        return state
