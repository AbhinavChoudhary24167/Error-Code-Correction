"""Physical-backend adapters and normalized characterization storage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Protocol

from jsonschema import Draft202012Validator

from .hashing import canonical_hash, file_sha256, manifest_sha256
from .loading import load_callable
from .registry import EccRegistry
from .verification import verify_implementation


PHYSICAL_FIELDS = (
    "cell_area", "routed_area", "critical_path", "setup_slack", "hold_slack",
    "maximum_frequency", "encoder_energy", "no_error_decode_energy",
    "corrected_decode_energy", "due_decode_energy", "leakage_power", "mux_area",
    "mux_energy", "controller_area", "controller_energy", "transition_energy",
    "transition_latency", "reencoding_energy", "wirelength", "congestion", "uncertainty",
)


class PhysicalBackend(Protocol):
    backend_id: str

    def characterize(
        self,
        *,
        registry: EccRegistry,
        implementation: Mapping[str, Any],
        code: Mapping[str, Any],
        architecture: Mapping[str, Any] | None,
        workload: Mapping[str, Any],
        verification: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...


class NullSafeBackend:
    """Adapter for structural-only or unavailable flows; never fabricates PPA."""

    def __init__(self, *, config: Mapping[str, Any], repo_root: Path) -> None:
        self.config = dict(config)
        self.repo_root = repo_root
        self.backend_id = str(config["backend_id"])

    def characterize(
        self,
        *,
        registry: EccRegistry,
        implementation: Mapping[str, Any],
        code: Mapping[str, Any],
        architecture: Mapping[str, Any] | None,
        workload: Mapping[str, Any],
        verification: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        kind = str(self.config["kind"])
        structural = kind == "structural_synthesis_only"
        structural_metrics = None
        if structural:
            structural_metrics = {
                "scope": "technology-independent structural evidence; not physical PPA",
                "available": bool(self.config.get("available", False)),
                "tool": self.config.get("tool"),
                "evidence_paths": list(self.config.get("evidence_paths", [])),
            }
        return {
            "technology": self.config.get("technology"),
            "pdk": self.config.get("pdk"),
            "library": self.config.get("library"),
            "corner": self.config.get("corner"),
            "voltage": self.config.get("voltage"),
            "temperature": self.config.get("temperature"),
            "timing_constraints": self.config.get("timing_constraints"),
            "evidence_level": "structural_only" if structural else "not_characterized",
            "physical_values": {field: None for field in PHYSICAL_FIELDS},
            "structural_metrics": structural_metrics,
            "backend_reason": self.config.get("reason"),
        }


def create_null_safe_backend(*, config: Mapping[str, Any], repo_root: Path) -> NullSafeBackend:
    return NullSafeBackend(config=config, repo_root=repo_root)


def load_backend(config_path: Path, *, repo_root: Path) -> tuple[dict[str, Any], PhysicalBackend]:
    path = config_path if config_path.is_absolute() else repo_root / config_path
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("incompatible backend schema_version")
    if payload.get("manifest_sha256") != manifest_sha256(payload):
        raise ValueError(f"broken backend manifest_sha256: {path}")
    adapter = payload.get("adapter", {})
    factory = load_callable(str(adapter.get("factory", "green_ecc_phy.backends:create_null_safe_backend")), base_dir=path.parent)
    backend = factory(config=payload, repo_root=repo_root)
    return payload, backend


def characterize_implementation(
    registry: EccRegistry,
    implementation_id: str,
    backend_config: Path,
    workload_config: Path,
    *,
    architecture_id: str | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    implementation = registry.implementation(implementation_id)
    code = registry.code(str(implementation["code_id"]))
    architecture = registry.architecture(architecture_id) if architecture_id is not None else None
    if architecture is not None and implementation_id not in architecture["allowed_implementation_ids"]:
        raise ValueError(f"implementation {implementation_id} is not allowed by architecture {architecture_id}")
    workload_path = workload_config if workload_config.is_absolute() else registry.repo_root / workload_config
    workload = json.loads(workload_path.read_text(encoding="utf-8"))
    if not isinstance(workload, dict) or not workload.get("workload_id"):
        raise ValueError("workload config requires workload_id")
    verification = verify_implementation(registry, implementation_id)
    if verification["verification_status"] != "passed":
        raise ValueError(f"implementation failed verification: {implementation_id}")
    backend_payload, backend = load_backend(backend_config, repo_root=registry.repo_root)
    raw = dict(
        backend.characterize(
            registry=registry,
            implementation=implementation,
            code=code,
            architecture=architecture,
            workload=workload,
            verification=verification,
        )
    )
    values = dict(raw["physical_values"])
    unsupported = sorted(
        [field for field in PHYSICAL_FIELDS if values.get(field) is None]
        + [field for field in ("technology", "pdk", "library", "corner", "voltage", "temperature", "timing_constraints") if raw.get(field) is None]
    )
    metadata_bits = None
    if architecture is not None:
        raw_bits = architecture.get("metadata", {}).get("bits_per_unit")
        metadata_bits = int(raw_bits) if raw_bits is not None else None
    basis = {
        "schema_version": 1,
        "code_id": code["code_id"],
        "implementation_id": implementation_id,
        "architecture_id": architecture_id,
        "backend_id": backend.backend_id,
        "workload_id": workload["workload_id"],
        "backend_manifest_sha256": backend_payload["manifest_sha256"],
        "workload_sha256": file_sha256(workload_path),
    }
    result: dict[str, Any] = {
        "schema_version": 1,
        "result_id": "characterization-" + canonical_hash(basis)[:24],
        "code_id": code["code_id"],
        "implementation_id": implementation_id,
        "architecture_id": architecture_id,
        "backend_id": backend.backend_id,
        "technology": raw.get("technology"),
        "pdk": raw.get("pdk"),
        "library": raw.get("library"),
        "corner": raw.get("corner"),
        "voltage": raw.get("voltage"),
        "temperature": raw.get("temperature"),
        "timing_constraints": raw.get("timing_constraints"),
        "workload_id": workload["workload_id"],
        "k": int(code["k"]),
        "n": int(code["n"]),
        "redundancy": int(code["redundancy"]),
        **{field: values.get(field) for field in PHYSICAL_FIELDS},
        "encoder_latency": int(implementation["encoder_latency"]),
        "decoder_latency": int(implementation["decoder_latency"]),
        "initiation_interval": int(implementation["initiation_interval"]),
        "metadata_bits": metadata_bits,
        "evidence_level": raw["evidence_level"],
        "provenance": {
            "code_manifest_sha256": code["content_hashes"]["manifest_sha256"],
            "matrix_sha256": code["content_hashes"]["matrix_sha256"],
            "implementation_manifest_sha256": implementation["manifest_sha256"],
            "backend_manifest_sha256": backend_payload["manifest_sha256"],
            "workload_sha256": file_sha256(workload_path),
            "verification_sha256": verification["verification_sha256"],
            "verification_status": verification["verification_status"],
            "tool_versions": verification["tool_versions"],
            "source_report_hashes": {
                path: digest
                for path, digest in implementation["source_hashes"].items()
                if Path(path).suffix.lower() in {".json", ".log"}
            },
            "backend_reason": raw.get("backend_reason"),
        },
        "unsupported_fields": unsupported,
        "structural_metrics": raw.get("structural_metrics"),
    }
    result["result_sha256"] = canonical_hash(result)
    _validate_result(result, registry.repo_root)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def _validate_result(payload: Mapping[str, Any], repo_root: Path) -> None:
    schema = json.loads((repo_root / "schemas" / "physical-characterization-result.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)
    basis = dict(payload)
    supplied = basis.pop("result_sha256")
    if supplied != canonical_hash(basis):
        raise ValueError("broken physical result hash")
    unsupported = set(map(str, payload["unsupported_fields"]))
    for field in unsupported:
        if field in payload and payload[field] is not None:
            raise ValueError(f"unsupported field must be null: {field}")


class CharacterizationStore:
    def __init__(self, registry: EccRegistry) -> None:
        self.registry = registry
        self.results: list[dict[str, Any]] = []
        self._ids: set[str] = set()

    def add(self, payload: Mapping[str, Any]) -> None:
        _validate_result(payload, self.registry.repo_root)
        result_id = str(payload["result_id"])
        if result_id in self._ids:
            raise ValueError(f"duplicate physical result_id: {result_id}")
        if payload["code_id"] not in self.registry.codes:
            raise ValueError(f"physical result references unknown code_id: {payload['code_id']}")
        if payload["implementation_id"] not in self.registry.implementations:
            raise ValueError(f"physical result references unknown implementation_id: {payload['implementation_id']}")
        architecture_id = payload["architecture_id"]
        if architecture_id is not None and architecture_id not in self.registry.architectures:
            raise ValueError(f"physical result references unknown architecture_id: {architecture_id}")
        self._ids.add(result_id)
        self.results.append(dict(payload))

    @classmethod
    def load_directory(cls, directory: Path, registry: EccRegistry) -> "CharacterizationStore":
        store = cls(registry)
        for path in sorted(directory.rglob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and payload.get("schema_version") == 1 and payload.get("result_id"):
                store.add(payload)
        return store
