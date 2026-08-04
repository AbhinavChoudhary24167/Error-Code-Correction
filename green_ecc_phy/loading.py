"""Safe local loading for manifest-declared plugin callables."""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
from typing import Callable


def load_callable(reference: str, *, base_dir: Path | None = None) -> Callable[..., object]:
    if "::" in reference:
        raw_path, attribute = reference.split("::", 1)
        path = Path(raw_path)
        if not path.is_absolute():
            if base_dir is None:
                raise ValueError(f"relative plugin path requires a base directory: {reference}")
            path = (base_dir / path).resolve()
        if not path.is_file():
            raise ValueError(f"plugin file does not exist: {path}")
        module_name = "green_ecc_external_" + path.stem + "_" + str(abs(hash(path)))
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ValueError(f"cannot load plugin module: {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    else:
        if ":" not in reference:
            raise ValueError(f"callable must use module:attribute or file.py::attribute: {reference}")
        module_name, attribute = reference.split(":", 1)
        module = importlib.import_module(module_name)
    value = getattr(module, attribute, None)
    if not callable(value):
        raise ValueError(f"plugin attribute is not callable: {reference}")
    return value

