"""Community-facing SafeForge audit, compiler, and verification pipelines."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import time
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator

from .ambiguity import build_support, support_document
from .artifacts import render_cpp_reference, render_python_reference
from .certificates import finalize_safety_certificate, verify_safety_certificate
from .equivalence import classify_code
from .experiments import make_experiment_identity
from .faults import load_fault_distribution
from .robust import compile_safe_decoder
from .safe_artifacts import policy_hardware_comparison, render_safe_rtl, render_safe_testbench


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _resolve(path: str | Path, root: Path) -> Path:
    source = Path(path)
    return source if source.is_absolute() else root / source


def _validate(payload: Mapping[str, Any], schema: Path) -> None:
    Draft202012Validator(_read(schema)).validate(payload)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_commit(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unknown"


def run_equivalence_audit(
    code_path: str | Path,
    *,
    repo_root: str | Path,
    reference_path: str | Path | None = None,
    geometry_rows: int | None = None,
    geometry_columns: int | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    code_source = _resolve(code_path, root)
    code = _read(code_source)
    _validate(code, root / "schemas" / "linear-code.schema.json")
    reference = None
    reference_source = None
    if reference_path is not None:
        reference_source = _resolve(reference_path, root)
        reference = _read(reference_source)
        _validate(reference, root / "schemas" / "linear-code.schema.json")
    geometry = None
    if geometry_rows is not None or geometry_columns is not None:
        if geometry_rows is None or geometry_columns is None:
            raise ValueError("both geometry_rows and geometry_columns are required")
        geometry = {"rows": int(geometry_rows), "columns": int(geometry_columns)}
    result = classify_code(code, reference_code=reference, geometry=geometry)
    result["audited_file"] = str(code_source)
    result["reference_file"] = str(reference_source) if reference_source else None
    result["claim_guard"] = (
        "No code-construction novelty may be claimed unless exact equivalence is false under the "
        "equivalence group relevant to the claim."
    )
    return result


def compile_safe_decoder_pipeline(
    code_path: str | Path,
    fault_model_path: str | Path,
    ambiguity_path: str | Path,
    outdir: str | Path,
    *,
    repo_root: str | Path,
    sdc_limit: float,
    residual_fit_limit: float | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    code_source = _resolve(code_path, root)
    ambiguity_source = _resolve(ambiguity_path, root)
    output = _resolve(outdir, root)
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    code = _read(code_source)
    ambiguity = _read(ambiguity_source)
    _validate(code, root / "schemas" / "linear-code.schema.json")
    _validate(ambiguity, root / "schemas" / "ambiguity-set.schema.json")
    nominal = load_fault_distribution(fault_model_path, repo_root=root)
    expansions = [
        load_fault_distribution(path, repo_root=root)
        for path in ambiguity.get("support_expansions", [])
    ]
    support = build_support(nominal, expansions)
    support_doc = support_document(support, bit_width=nominal.bit_width)
    identity = make_experiment_identity(
        k=int(code["k"]),
        r=int(code["r"]),
        distribution=nominal,
        physical_bit_order=ambiguity.get("physical_bit_order"),
        error_universe_document=support_doc,
        ambiguity=ambiguity,
    )
    policy = compile_safe_decoder(
        code,
        support,
        ambiguity,
        sdc_limit=float(sdc_limit),
        residual_fit_limit=residual_fit_limit,
        raw_fit=nominal.raw_fit,
    )
    certificate = finalize_safety_certificate(
        {
            "schema_version": 1,
            "certificate_type": "SafeForge finite-support distributionally robust SDC envelope",
            "policy_id": policy["policy_id"],
            "policy_sha256": policy["policy_sha256"],
            "source_code_id": policy["code_id"],
            "experiment_identity": identity,
            "compiled_code": policy["compiled_code"],
            "support": support_doc,
            "ambiguity": ambiguity,
            "sdc_limit": float(sdc_limit),
            "residual_fit_limit": residual_fit_limit,
            "raw_fit": nominal.raw_fit,
            "loss_vectors": {
                name: policy["certificates"][name]["loss_vector"]
                for name in ("sdc", "due")
            }
            | {
                "correct": [
                    1 - int(sdc) - int(due)
                    for sdc, due in zip(
                        policy["certificates"]["sdc"]["loss_vector"],
                        policy["certificates"]["due"]["loss_vector"],
                    )
                ]
            },
            "risk_certificates": policy["certificates"],
            "certified_safety_radius": policy["certified_safety_radius"],
            "certificate_scope": (
                "all data values crossed with every bit-exact error vector in the declared finite support; "
                "distributional uncertainty only within the declared ambiguity set"
            ),
        }
    )
    _validate(policy, root / "schemas" / "safe-decoder-policy.schema.json")
    _validate(certificate, root / "schemas" / "safety-certificate.schema.json")
    verification = verify_safety_certificate(certificate)
    if verification["verification_status"] != "passed":
        raise ValueError(f"independent certificate verification failed: {verification['failures']}")
    hardware = policy_hardware_comparison(code, policy)
    envelope = {
        "schema_version": 1,
        "mode_id": policy["compiled_code_id"],
        "supported_fault_model_family": nominal.distribution_id,
        "ambiguity_set_type": ambiguity["type"],
        "support_identifier": support_doc["support_sha256"],
        "configured_radius": ambiguity["radius"],
        "certified_radius": policy["certified_safety_radius"]["certified_radius"],
        "maximum_certified_sdc": policy["metrics"]["worst_case"]["sdc"],
        "maximum_certified_due": policy["metrics"]["worst_case"]["due"],
        "fallback_mode": ambiguity.get("fallback_mode", "detect-only-safe-fallback"),
        "certificate_identifier": certificate["safety_certificate_sha256"],
        "selection_rule": "select only when current confidence region is contained in this envelope",
    }
    _write(output / "policy.json", policy)
    _write(output / "support.json", support_doc)
    _write(output / "certificate.json", certificate)
    _write(output / "verification_report.json", verification)
    _write(output / "safe_envelope.json", envelope)
    _write(output / "hardware_comparison.json", hardware)
    _write(
        output / "adversarial_pmf.json",
        {
            "policy_id": policy["policy_id"],
            "ambiguity_type": ambiguity["type"],
            "objective": "worst_case_sdc",
            "worst_case_risk": policy["certificates"]["sdc"]["worst_case_risk"],
            "adversarial_pmf": policy["certificates"]["sdc"]["adversarial_pmf"],
            "patterns_receiving_probability": policy["certificates"]["sdc"][
                "patterns_receiving_probability"
            ],
            "certificate_sha256": policy["certificates"]["sdc"]["certificate_sha256"],
        },
    )
    reference = output / "reference"
    reference.mkdir(parents=True, exist_ok=True)
    (reference / "reference_model.py").write_text(
        render_python_reference(policy["compiled_code"]), encoding="utf-8"
    )
    cpp_reference = reference / "reference_model.cpp"
    if int(policy["compiled_code"]["n"]) <= 64:
        cpp_reference.write_text(
            render_cpp_reference(policy["compiled_code"]), encoding="utf-8"
        )
    else:
        if cpp_reference.exists():
            cpp_reference.unlink()
        _write(
            reference / "reference_model_limitations.json",
            {
                "cpp_reference_emitted": False,
                "reason": "the existing uint64_t C++ reference representation cannot hold a 72-bit codeword",
                "authoritative_reference": "reference_model.py with arbitrary-precision integers",
            },
        )
    rtl = output / "rtl"
    rtl.mkdir(parents=True, exist_ok=True)
    for name, content in render_safe_rtl(policy).items():
        (rtl / name).write_text(content, encoding="utf-8")
    testbench_name, testbench = render_safe_testbench(policy, policy["outcomes"])
    (rtl / testbench_name).write_text(testbench, encoding="utf-8")
    files = {
        path.relative_to(output).as_posix(): _sha256(path)
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "result_manifest.json"
    }
    source_paths = [
        root / "codeforge" / name
        for name in (
            "ambiguity.py",
            "certificates.py",
            "experiments.py",
            "robust.py",
            "safe_artifacts.py",
            "safe_pipeline.py",
        )
    ] + [
        root / "schemas" / name
        for name in (
            "ambiguity-set.schema.json",
            "fault-distribution.schema.json",
            "linear-code.schema.json",
            "safe-decoder-policy.schema.json",
            "safety-certificate.schema.json",
        )
    ] + [
        code_source,
        _resolve(fault_model_path, root),
        ambiguity_source,
        *[_resolve(path, root) for path in ambiguity.get("support_expansions", [])],
    ]
    unique_sources = list(dict.fromkeys(path.resolve() for path in source_paths))
    source_hashes = {
        path.relative_to(root).as_posix(): _sha256(path) for path in unique_sources
    }
    source_tree_hash = hashlib.sha256(
        "".join(f"{path}:{digest}\n" for path, digest in sorted(source_hashes.items())).encode("utf-8")
    ).hexdigest()
    manifest = {
        "manifest_version": 1,
        "repository_commit": _git_commit(root),
        "repository_dirty": True,
        "input_code": str(code_source),
        "input_code_sha256": _sha256(code_source),
        "fault_model": str(_resolve(fault_model_path, root)),
        "ambiguity_config": str(ambiguity_source),
        "ambiguity_config_sha256": _sha256(ambiguity_source),
        "source_tree_sha256": source_tree_hash,
        "source_files": source_hashes,
        "files": files,
        "observed_runtime_seconds": time.perf_counter() - started,
        "reproduction_command": (
            f"python eccsim.py compile-safe-decoder --code {code_source} "
            f"--fault-model {_resolve(fault_model_path, root)} --ambiguity {ambiguity_source} "
            f"--sdc-limit {sdc_limit} --outdir {output}"
        ),
    }
    _write(output / "result_manifest.json", manifest)
    return {
        "policy_id": policy["policy_id"],
        "verification_status": verification["verification_status"],
        "nominal": policy["metrics"]["nominal"],
        "worst_case": policy["metrics"]["worst_case"],
        "certified_radius": policy["certified_safety_radius"]["certified_radius"],
        "certificate_id": certificate["safety_certificate_sha256"],
        "output_directory": str(output),
    }


def verify_safety_certificate_file(
    certificate_path: str | Path, *, repo_root: str | Path
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    source = _resolve(certificate_path, root)
    document = _read(source)
    _validate(document, root / "schemas" / "safety-certificate.schema.json")
    return verify_safety_certificate(document)
