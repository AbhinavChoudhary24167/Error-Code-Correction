from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path

import pytest


@dataclass
class _SimpleTmpPathFactory:
    base: Path
    counter: int = 0

    def mktemp(self, basename: str, numbered: bool = True) -> Path:
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", basename)
        if numbered:
            self.counter += 1
            safe = f"{safe}_{self.counter}"
        path = self.base / safe
        path.mkdir(parents=True, exist_ok=True)
        return path.resolve()

    def getbasetemp(self) -> Path:
        return self.base


@pytest.fixture(scope="session")
def tmp_path_factory() -> _SimpleTmpPathFactory:
    base = Path("tests") / "fixtures" / "local_tmp" / f"session_{uuid.uuid4().hex}"
    base.mkdir(parents=True, exist_ok=True)
    return _SimpleTmpPathFactory(base=base)


@pytest.fixture
def tmp_path(tmp_path_factory: _SimpleTmpPathFactory, request: pytest.FixtureRequest) -> Path:
    return tmp_path_factory.mktemp(request.node.name, numbered=True)
