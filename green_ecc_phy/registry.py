"""Versioned manifest registry with cross-reference and hash enforcement."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator

from codeforge.gf2 import is_zero_matrix, matmul, rank, transpose, validate_matrix

from .hashing import (
    RAW_BYTES_SHA256_V1,
    canonical_hash,
    manifest_sha256,
    scientific_hash_matches,
)
from .loading import load_callable


SUPPORTED_SCHEMA_VERSION = 1


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON document must be an object: {path}")
    return value


class EccRegistry:
    """Loaded catalogue. Core behavior is ID-driven, never family-dispatched."""

    def __init__(self, *, repo_root: Path, registry_path: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.registry_path = registry_path.resolve()
        self.codes: dict[str, dict[str, Any]] = {}
        self.implementations: dict[str, dict[str, Any]] = {}
        self.architectures: dict[str, dict[str, Any]] = {}
        self.backends: dict[str, dict[str, Any]] = {}
        self._paths: dict[tuple[str, str], Path] = {}
        self.source_hash_scheme = RAW_BYTES_SHA256_V1
        self.source_hash_migrations: dict[str, dict[str, str]] = {}

    @classmethod
    def load(cls, registry_path: Path, *, repo_root: Path | None = None) -> "EccRegistry":
        source = registry_path.resolve()
        root = (repo_root or _find_repo_root(source)).resolve()
        registry = cls(repo_root=root, registry_path=source)
        registry._load()
        return registry

    @classmethod
    def builtin(cls, repo_root: Path) -> "EccRegistry":
        return cls.load(
            repo_root / "green_ecc_physical_simulation" / "registry" / "registry.json",
            repo_root=repo_root,
        )

    def _load(self) -> None:
        config = _read_json(self.registry_path)
        if config.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
            raise ValueError(f"incompatible registry schema_version: {config.get('schema_version')!r}")
        self.source_hash_scheme = str(config.get("scientific_source_hash_scheme", RAW_BYTES_SHA256_V1))
        self._load_source_hash_migrations(
            config.get("scientific_hash_migration"),
            config.get("scientific_hash_migration_sha256"),
        )
        self._load_group(config.get("codes", []), "code", "code_id", "ecc-code-manifest.schema.json", self.codes)
        self._load_group(
            config.get("implementations", []), "implementation", "implementation_id",
            "ecc-implementation-manifest.schema.json", self.implementations,
        )
        self._load_group(
            config.get("architectures", []), "architecture", "architecture_id",
            "deployment-architecture.schema.json", self.architectures,
        )
        self._load_backends(config.get("backends", []))
        self._validate_cross_references()

    def _load_source_hash_migrations(self, raw: object, expected_hash: object) -> None:
        if raw is None:
            return
        path = self._resolve_registry_path(str(raw))
        payload = _read_json(path)
        if not isinstance(expected_hash, str) or canonical_hash(payload) != expected_hash:
            raise ValueError(f"{path}: broken scientific hash migration identity")
        if payload.get("schema_version") != 1 or payload.get("scheme") != self.source_hash_scheme:
            raise ValueError(f"{path}: incompatible scientific hash migration")
        bindings = payload.get("bindings")
        if not isinstance(bindings, dict):
            raise ValueError(f"{path}: scientific hash migration bindings must be an object")
        for raw_path, value in bindings.items():
            if not isinstance(value, dict):
                raise ValueError(f"{path}: invalid scientific hash migration for {raw_path}")
            legacy = str(value.get("legacy_sha256", ""))
            canonical = str(value.get("canonical_sha256", ""))
            if len(legacy) != 64 or len(canonical) != 64:
                raise ValueError(f"{path}: invalid scientific hash migration digest for {raw_path}")
            source = (self.repo_root / str(raw_path)).resolve()
            if not source.is_relative_to(self.repo_root):
                raise ValueError(f"{path}: scientific hash migration escapes repository: {raw_path}")
            if not source.is_file() or not scientific_hash_matches(
                source, canonical, scheme=self.source_hash_scheme
            ):
                raise ValueError(f"{path}: canonical scientific hash migration mismatch for {raw_path}")
            self.source_hash_migrations[str(raw_path)] = {
                "legacy_sha256": legacy,
                "canonical_sha256": canonical,
            }

    def source_hash_matches(self, raw: str, path: Path, expected: str) -> bool:
        migration = self.source_hash_migrations.get(raw)
        migrated = None
        if migration is not None and migration["legacy_sha256"] == expected:
            migrated = migration["canonical_sha256"]
        return scientific_hash_matches(
            path,
            expected,
            scheme=self.source_hash_scheme,
            legacy_canonical_sha256=migrated,
        )

    def _load_group(
        self,
        paths: Iterable[object],
        kind: str,
        id_field: str,
        schema_name: str,
        destination: dict[str, dict[str, Any]],
    ) -> None:
        if isinstance(paths, (str, bytes)):
            raise ValueError(f"registry {kind}s must be an array of paths")
        schema = _read_json(self.repo_root / "schemas" / schema_name)
        validator = Draft202012Validator(schema)
        for raw in paths:
            path = self._resolve_registry_path(str(raw))
            payload = _read_json(path)
            errors = sorted(validator.iter_errors(payload), key=lambda item: list(item.absolute_path))
            if errors:
                first = errors[0]
                location = "/".join(map(str, first.absolute_path)) or "<root>"
                raise ValueError(f"{path}: schema error at {location}: {first.message}")
            identifier = str(payload[id_field])
            if identifier in destination:
                raise ValueError(f"duplicate {id_field}: {identifier}")
            self._validate_manifest_hash(payload, path, kind)
            if kind == "code":
                resolved = self._resolve_matrix(payload, path)
                self._validate_code(payload, resolved, path)
                payload = copy.deepcopy(payload)
                payload["_resolved_matrix"] = resolved
            self._validate_sources(payload, path, kind)
            payload["_manifest_path"] = path
            destination[identifier] = payload
            self._paths[(kind, identifier)] = path

    def _load_backends(self, paths: Iterable[object]) -> None:
        if isinstance(paths, (str, bytes)):
            raise ValueError("registry backends must be an array of paths")
        for raw in paths:
            path = self._resolve_registry_path(str(raw))
            payload = _read_json(path)
            if payload.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
                raise ValueError(f"{path}: incompatible backend schema_version")
            backend_id = str(payload.get("backend_id", ""))
            if not backend_id:
                raise ValueError(f"{path}: backend_id is required")
            if backend_id in self.backends:
                raise ValueError(f"duplicate backend_id: {backend_id}")
            supplied = payload.get("manifest_sha256")
            if supplied != manifest_sha256(payload):
                raise ValueError(f"{path}: broken manifest_sha256")
            payload["_manifest_path"] = path
            self.backends[backend_id] = payload

    def _resolve_registry_path(self, raw: str) -> Path:
        path = Path(raw)
        if not path.is_absolute():
            path = self.registry_path.parent / path
        path = path.resolve()
        if not path.is_file():
            raise ValueError(f"missing registry reference: {path}")
        return path

    def _validate_manifest_hash(self, payload: Mapping[str, Any], path: Path, kind: str) -> None:
        if kind == "code":
            supplied = payload["content_hashes"]["manifest_sha256"]
        else:
            supplied = payload["manifest_sha256"]
        if supplied != manifest_sha256(payload):
            raise ValueError(f"{path}: broken manifest_sha256")

    def _resolve_matrix(self, payload: Mapping[str, Any], path: Path) -> dict[str, Any]:
        definition = payload["matrix_definition"]
        if definition.get("generator_matrix") is not None and definition.get("parity_check_matrix") is not None:
            return {"G": definition["generator_matrix"], "H": definition["parity_check_matrix"]}
        generator = definition["deterministic_generator"]
        factory = load_callable(str(generator["callable"]), base_dir=path.parent)
        resolved = factory(**dict(generator["parameters"]))
        if not isinstance(resolved, Mapping) or "G" not in resolved or "H" not in resolved:
            raise ValueError(f"{path}: matrix generator must return G and H")
        return dict(resolved)

    def _validate_code(self, payload: Mapping[str, Any], matrix: Mapping[str, Any], path: Path) -> None:
        k, n, redundancy = int(payload["k"]), int(payload["n"]), int(payload["redundancy"])
        if n != k + redundancy:
            raise ValueError(f"{path}: n must equal k+redundancy")
        h = matrix["H"]
        g = matrix["G"]
        h_shape = validate_matrix(h, name="H")
        g_shape = validate_matrix(g, name="G")
        if h_shape != (redundancy, n):
            raise ValueError(f"{path}: H shape {h_shape} does not match {redundancy}x{n}")
        if g_shape != (k, n):
            raise ValueError(f"{path}: G shape {g_shape} does not match {k}x{n}")
        if rank(h) != redundancy or rank(g) != k:
            raise ValueError(f"{path}: matrix rank check failed")
        if not is_zero_matrix(matmul(g, transpose(h))):
            raise ValueError(f"{path}: G H^T != 0")
        positions = list(payload["systematic"]["data_positions"])
        if len(positions) != k or len(set(positions)) != k or any(pos >= n for pos in positions):
            raise ValueError(f"{path}: invalid systematic data_positions")
        expected_matrix_hash = canonical_hash({"G": g, "H": h})
        if payload["content_hashes"]["matrix_sha256"] != expected_matrix_hash:
            raise ValueError(f"{path}: broken matrix_sha256")

    def _validate_sources(self, payload: Mapping[str, Any], path: Path, kind: str) -> None:
        hashes = payload["content_hashes"]["source_files"] if kind == "code" else payload.get("source_hashes", {})
        for raw, expected in hashes.items():
            source = Path(raw)
            if not source.is_absolute():
                source = self.repo_root / source
            source = source.resolve()
            if not source.is_file():
                raise ValueError(f"{path}: missing source reference {raw}")
            if not self.source_hash_matches(str(raw), source, str(expected)):
                raise ValueError(f"{path}: broken source hash for {raw}")
        if kind == "implementation":
            declared = set(map(str, payload["source_files"]))
            if declared != set(map(str, hashes)):
                raise ValueError(f"{path}: source_files and source_hashes keys differ")

    def _validate_cross_references(self) -> None:
        for implementation_id, implementation in self.implementations.items():
            if implementation["code_id"] not in self.codes:
                raise ValueError(f"implementation {implementation_id} references unknown code_id {implementation['code_id']}")
        for architecture_id, architecture in self.architectures.items():
            allowed = list(architecture["allowed_implementation_ids"])
            missing = sorted(set(allowed) - set(self.implementations))
            if missing:
                raise ValueError(f"architecture {architecture_id} references unknown implementations: {missing}")
            if architecture["active_implementation"] not in allowed:
                raise ValueError(f"architecture {architecture_id} active implementation is not allowed")
            fallback = architecture["fallback_implementation"]
            if fallback is not None and fallback not in allowed:
                raise ValueError(f"architecture {architecture_id} fallback implementation is not allowed")

    def adapter(self, implementation_id: str):
        implementation = self.implementation(implementation_id)
        code = self.code(str(implementation["code_id"]))
        spec = implementation["adapter"]
        factory = load_callable(str(spec["factory"]), base_dir=Path(implementation["_manifest_path"]).parent)
        return factory(code=code, implementation=implementation, **dict(spec["parameters"]))

    def code(self, code_id: str) -> dict[str, Any]:
        try:
            return self.codes[code_id]
        except KeyError as exc:
            raise KeyError(f"unknown code_id: {code_id}") from exc

    def implementation(self, implementation_id: str) -> dict[str, Any]:
        try:
            return self.implementations[implementation_id]
        except KeyError as exc:
            raise KeyError(f"unknown implementation_id: {implementation_id}") from exc

    def architecture(self, architecture_id: str) -> dict[str, Any]:
        try:
            return self.architectures[architecture_id]
        except KeyError as exc:
            raise KeyError(f"unknown architecture_id: {architecture_id}") from exc

    def public_code(self, code_id: str) -> dict[str, Any]:
        payload = copy.deepcopy(self.code(code_id))
        payload.pop("_manifest_path", None)
        payload.pop("_resolved_matrix", None)
        payload["implementation_ids"] = sorted(
            identifier for identifier, item in self.implementations.items() if item["code_id"] == code_id
        )
        payload["matrix_checks"] = {
            "matrix_sha256": self.code(code_id)["content_hashes"]["matrix_sha256"],
            "rank_h": int(payload["redundancy"]),
            "rank_g": int(payload["k"]),
            "g_h_transpose_zero": True,
        }
        return payload


def _find_repo_root(path: Path) -> Path:
    for candidate in [path.parent, *path.parents]:
        if (candidate / "schemas" / "ecc-code-manifest.schema.json").is_file():
            return candidate
    raise ValueError(f"cannot locate repository root from {path}")
