"""Additive CLI surface for the multi-ECC framework."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .backends import CharacterizationStore, characterize_implementation
from .comparison import select_physical
from .hashing import canonical_hash, file_sha256
from .registry import EccRegistry
from .verification import verify_implementation


def add_parsers(subparsers) -> dict[str, argparse.ArgumentParser]:
    parsers: dict[str, argparse.ArgumentParser] = {}
    ecc = subparsers.add_parser("ecc", help="Inspect and verify versioned ECC plugins")
    ecc_sub = ecc.add_subparsers(dest="ecc_command")

    parsers["ecc-list"] = ecc_sub.add_parser("list", help="List registered mathematical codes")
    _registry_argument(parsers["ecc-list"])

    parsers["ecc-inspect"] = ecc_sub.add_parser("inspect", help="Inspect one mathematical code")
    parsers["ecc-inspect"].add_argument("--code", required=True)
    _registry_argument(parsers["ecc-inspect"])

    parsers["ecc-implementations"] = ecc_sub.add_parser(
        "implementations", help="List hardware implementations for a code"
    )
    parsers["ecc-implementations"].add_argument("--code", required=True)
    _registry_argument(parsers["ecc-implementations"])

    parsers["ecc-verify"] = ecc_sub.add_parser("verify", help="Run the implementation evidence gate")
    parsers["ecc-verify"].add_argument("--implementation", required=True)
    parsers["ecc-verify"].add_argument("--out", type=Path, default=None)
    _registry_argument(parsers["ecc-verify"])

    parsers["characterize"] = subparsers.add_parser(
        "characterize", help="Run one implementation through a physical-backend adapter"
    )
    parsers["characterize"].add_argument("--implementation", required=True)
    parsers["characterize"].add_argument("--architecture", default=None)
    parsers["characterize"].add_argument("--backend", type=Path, required=True)
    parsers["characterize"].add_argument("--workload", type=Path, required=True)
    parsers["characterize"].add_argument("--outdir", type=Path, required=True)
    _registry_argument(parsers["characterize"])

    parsers["characterize-all"] = subparsers.add_parser(
        "characterize-all", help="Characterize every passing registered implementation"
    )
    parsers["characterize-all"].add_argument("--backend", type=Path, required=True)
    parsers["characterize-all"].add_argument("--workload", type=Path, required=True)
    parsers["characterize-all"].add_argument("--outdir", type=Path, required=True)
    _registry_argument(parsers["characterize-all"])

    parsers["select-physical"] = subparsers.add_parser(
        "select-physical", help="Select only among fair, characterized physical results"
    )
    parsers["select-physical"].add_argument("--characterization", type=Path, required=True)
    parsers["select-physical"].add_argument("--scenario", type=Path, required=True)
    parsers["select-physical"].add_argument("--outdir", type=Path, required=True)
    _registry_argument(parsers["select-physical"])
    return parsers


def _registry_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--registry", type=Path, default=None, help="Registry config; defaults to built-in catalogue")


def handle(args, *, repo_root: Path, parsers: dict[str, argparse.ArgumentParser]) -> bool:
    if args.command not in {"ecc", "characterize", "characterize-all", "select-physical"}:
        return False
    parser_key = args.command if args.command != "ecc" else f"ecc-{args.ecc_command}"
    parser = parsers.get(parser_key)
    if parser is None:
        parsers["ecc-list"].error("ecc subcommand required")
    try:
        registry = _load_registry(args.registry, repo_root)
        if args.command == "ecc":
            payload = _handle_ecc(args, registry)
        elif args.command == "characterize":
            args.outdir.mkdir(parents=True, exist_ok=True)
            output = args.outdir / f"{args.implementation}.characterization.json"
            payload = characterize_implementation(
                registry, args.implementation, args.backend, args.workload,
                architecture_id=args.architecture, output_path=output,
            )
        elif args.command == "characterize-all":
            payload = _characterize_all(registry, args.backend, args.workload, args.outdir)
        else:
            scenario_path = args.scenario if args.scenario.is_absolute() else repo_root / args.scenario
            scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
            store = CharacterizationStore.load_directory(args.characterization, registry)
            args.outdir.mkdir(parents=True, exist_ok=True)
            payload = select_physical(store, scenario, output_path=args.outdir / "physical_selection.json")
            manifest = {
                "schema_version": 1,
                "scenario_sha256": file_sha256(scenario_path),
                "selection_sha256": payload["selection_sha256"],
                "result_count": len(store.results),
            }
            manifest["manifest_sha256"] = canonical_hash(manifest)
            (args.outdir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return True


def _load_registry(path: Path | None, repo_root: Path) -> EccRegistry:
    if path is None:
        return EccRegistry.builtin(repo_root)
    return EccRegistry.load(path if path.is_absolute() else repo_root / path, repo_root=repo_root)


def _handle_ecc(args, registry: EccRegistry) -> dict[str, Any]:
    if args.ecc_command == "list":
        return {
            "schema_version": 1,
            "registry": str(registry.registry_path),
            "code_count": len(registry.codes),
            "implementation_count": len(registry.implementations),
            "codes": [
                {
                    "code_id": code_id, "family": code["family"], "name": code["name"],
                    "k": code["k"], "n": code["n"],
                    "implementation_count": sum(item["code_id"] == code_id for item in registry.implementations.values()),
                }
                for code_id, code in sorted(registry.codes.items())
            ],
        }
    if args.ecc_command == "inspect":
        return registry.public_code(args.code)
    if args.ecc_command == "implementations":
        registry.code(args.code)
        return {
            "schema_version": 1,
            "code_id": args.code,
            "implementations": [
                _public_implementation(item)
                for _, item in sorted(registry.implementations.items())
                if item["code_id"] == args.code
            ],
        }
    if args.ecc_command == "verify":
        return verify_implementation(registry, args.implementation, output_path=args.out)
    raise ValueError("ecc subcommand required")


def _public_implementation(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if not key.startswith("_")}


def _characterize_all(registry: EccRegistry, backend: Path, workload: Path, outdir: Path) -> dict[str, Any]:
    outdir.mkdir(parents=True, exist_ok=True)
    completed: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for implementation_id in sorted(registry.implementations):
        verification = verify_implementation(
            registry, implementation_id,
            output_path=outdir / "verification" / f"{implementation_id}.json",
        )
        if verification["verification_status"] != "passed":
            rejected.append({"implementation_id": implementation_id, "failures": verification["failures"]})
            continue
        implementation = registry.implementation(implementation_id)
        for architecture_id in implementation["compatible_deployment_architectures"]:
            output = outdir / "characterization" / f"{implementation_id}--{architecture_id}.json"
            result = characterize_implementation(
                registry, implementation_id, backend, workload,
                architecture_id=architecture_id, output_path=output,
            )
            completed.append(
                {
                    "implementation_id": implementation_id,
                    "architecture_id": architecture_id,
                    "result_id": result["result_id"],
                }
            )
    summary: dict[str, Any] = {
        "schema_version": 1,
        "completed": completed,
        "rejected": rejected,
        "physical_metrics_policy": "unsupported quantities remain null; structural evidence is not physical PPA",
    }
    summary["summary_sha256"] = canonical_hash(summary)
    (outdir / "characterize_all_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary
