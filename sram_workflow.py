"""SRAM-oriented ECC workflow adapters.

This module integrates the PracticalSRAMSimulator C++ backend into the Python
CLI/reporting stack while preserving deterministic selector semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Dict, Iterable, List, Mapping

from ecc_selector import select

SUPPORTED_SRAM_KB = (64, 128, 256)
SUPPORTED_WORD_BITS = (8, 16, 32)
SUPPORTED_SCHEMES = ("sec-ded", "taec", "bch", "polar")

_SCHEME_TO_CODEC = {
    "sec-ded": "secded",
    "taec": "taec",
    "bch": "bch",
    "polar": "polar",
}

_SCHEME_TO_SELECTOR_FAMILY = {
    "sec-ded": "secded",
    "taec": "taec",
    "bch": "bch",
    "polar": "polar",
}


@dataclass(frozen=True)
class SRAMScenario:
    size_kb: int
    word_bits: int
    iterations: int
    seed: int
    fault_model: str


def _validate(size_kb: int, word_bits: int, schemes: Iterable[str]) -> List[str]:
    if size_kb not in SUPPORTED_SRAM_KB:
        raise ValueError(f"size-kb must be one of {SUPPORTED_SRAM_KB}")
    if word_bits not in SUPPORTED_WORD_BITS:
        raise ValueError(f"word-bits must be one of {SUPPORTED_WORD_BITS}")
    cleaned = []
    for scheme in schemes:
        s = scheme.strip().lower()
        if not s:
            continue
        if s not in SUPPORTED_SCHEMES:
            raise ValueError(f"Unsupported SRAM scheme '{scheme}'")
        cleaned.append(s)
    if not cleaned:
        raise ValueError("At least one SRAM scheme must be provided")
    return cleaned


def selector_code_for_sram_scheme(scheme: str, word_bits: int) -> str:
    return f"sram-{_SCHEME_TO_SELECTOR_FAMILY[scheme]}-{word_bits}"


def _scenario_hash(scenario: Mapping[str, object]) -> str:
    return hashlib.sha1(json.dumps(dict(scenario), sort_keys=True).encode()).hexdigest()


def _map_result_row(row: Mapping[str, object], *, scenario: SRAMScenario) -> Dict[str, object]:
    metrics = row.get("metrics", {})
    stats = row.get("stats", {})
    corrected = float(stats.get("corrected", 0.0))
    detected_uncorrectable = float(stats.get("detected_uncorrectable", 0.0))
    undetected = float(stats.get("undetected", 0.0))
    total_reads = max(float(stats.get("reads", 0.0)), 1.0)
    rel_success = (corrected + detected_uncorrectable) / total_reads

    return {
        "codec": row.get("codec"),
        "size_kb": int(row.get("size_kb", scenario.size_kb)),
        "word_bits": int(row.get("word_bits", scenario.word_bits)),
        "fault_model": row.get("fault_model", scenario.fault_model),
        "iterations": int(row.get("iterations", scenario.iterations)),
        "reliability_success": rel_success,
        "sdc_rate": float(metrics.get("sdc_pct", 0.0)) / 100.0,
        "effective_protection": float(metrics.get("effective_protection_score", 0.0)),
        "redundancy_overhead_pct": float(metrics.get("expansion_pct", 0.0)),
        "energy_proxy": float(metrics.get("normalized_energy", 0.0)),
        "latency_proxy": float(metrics.get("normalized_latency", 0.0)),
        "utility": float(metrics.get("effective_protection_score", 0.0))
        / (1.0 + float(metrics.get("normalized_energy", 0.0)) + float(metrics.get("normalized_latency", 0.0))),
        "raw": row,
    }


def run_sram_backend(
    *,
    repo_root: Path,
    mode: str,
    size_kb: int,
    word_bits: int,
    schemes: Iterable[str],
    iterations: int,
    seed: int,
    fault_model: str,
) -> Dict[str, object]:
    cleaned = _validate(size_kb, word_bits, schemes)
    scenario = SRAMScenario(size_kb=size_kb, word_bits=word_bits, iterations=iterations, seed=seed, fault_model=fault_model)
    exe = repo_root / "PracticalSRAMSimulator"

    scenario_meta = {
        "size_kb": size_kb,
        "word_bits": word_bits,
        "iterations": iterations,
        "seed": seed,
        "fault_model": fault_model,
        "mode": mode,
        "schemes": cleaned,
    }

    rows: List[Dict[str, object]] = []
    backend = "python-fallback"
    if exe.exists():
        backend = "cpp-practical"
        codec = "all" if len(cleaned) > 1 else _SCHEME_TO_CODEC[cleaned[0]]
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tmp:
            export_path = Path(tmp.name)
        cmd = [
            str(exe),
            "--mode",
            "compare" if mode == "compare" else "stress",
            "--codec",
            codec,
            "--size-kb",
            str(size_kb),
            "--word-bits",
            str(word_bits),
            "--iterations",
            str(iterations),
            "--seed",
            str(seed),
            "--fault-model",
            fault_model,
            "--export-json",
            str(export_path),
        ]
        subprocess.run(cmd, check=True, cwd=repo_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        payload = json.loads(export_path.read_text(encoding="utf-8"))
        export_path.unlink(missing_ok=True)

        for row in payload.get("results", []):
            codec_name = str(row.get("codec", "")).strip().lower().replace("-", "")
            expected = _SCHEME_TO_CODEC[cleaned[0]].replace("-", "")
            if len(cleaned) == 1 and codec_name != expected:
                continue
            rows.append(_map_result_row(row, scenario=scenario))
    else:
        # deterministic fallback: selector-derived proxies keep workflow usable
        capacity_gib = size_kb / (1024 * 1024)
        selector_codes = [selector_code_for_sram_scheme(s, word_bits) for s in cleaned]
        sel = select(
            selector_codes,
            node=14,
            vdd=0.8,
            temp=75.0,
            capacity_gib=capacity_gib,
            ci=0.3,
            bitcell_um2=0.08,
            lifetime_h=8760.0,
            mbu="moderate",
            scrub_s=10.0,
        )
        for rec in sel.get("candidate_records", []):
            rows.append(
                {
                    "codec": rec["code"],
                    "size_kb": size_kb,
                    "word_bits": word_bits,
                    "fault_model": fault_model,
                    "iterations": iterations,
                    "reliability_success": max(0.0, 1.0 - rec.get("fit_word_post", 0.0) * 1e-9),
                    "sdc_rate": rec.get("fit_word_post", 0.0) * 1e-12,
                    "effective_protection": rec.get("GS", 0.0),
                    "redundancy_overhead_pct": 100.0 * rec.get("area_macro_mm2", 0.0) / max(rec.get("area_logic_mm2", 1.0), 1e-9),
                    "energy_proxy": rec.get("E_scrub_kWh", 0.0),
                    "latency_proxy": rec.get("latency_ns", 0.0),
                    "utility": rec.get("NESII", 0.0),
                    "raw": rec,
                }
            )

    return {
        "backend": backend,
        "scenario": scenario_meta,
        "scenario_hash": _scenario_hash(scenario_meta),
        "records": rows,
    }


def run_sram_selection(
    *,
    schemes: Iterable[str],
    size_kb: int,
    word_bits: int,
    node: int,
    vdd: float,
    temp: float,
    ci: float,
    bitcell_um2: float,
    lifetime_h: float,
    mbu: str,
    scrub_s: float,
    flux_rel: float | None,
    alt_km: float,
    latitude_deg: float,
) -> Dict[str, object]:
    cleaned = _validate(size_kb, word_bits, schemes)
    codes = [selector_code_for_sram_scheme(s, word_bits) for s in cleaned]
    return select(
        codes,
        node=node,
        vdd=vdd,
        temp=temp,
        capacity_gib=size_kb / (1024 * 1024),
        ci=ci,
        bitcell_um2=bitcell_um2,
        lifetime_h=lifetime_h,
        mbu=mbu,
        scrub_s=scrub_s,
        flux_rel=flux_rel,
        alt_km=alt_km,
        latitude_deg=latitude_deg,
    )


def write_sram_records_csv(path: Path, rows: Iterable[Mapping[str, object]]) -> None:
    fieldnames = [
        "codec",
        "size_kb",
        "word_bits",
        "fault_model",
        "iterations",
        "reliability_success",
        "sdc_rate",
        "effective_protection",
        "redundancy_overhead_pct",
        "energy_proxy",
        "latency_proxy",
        "utility",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fieldnames})
