"""Process-local configuration for plotting in restricted environments."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile


def configure_matplotlib_cache() -> Path:
    """Use a writable per-process cache unless the caller selected one."""

    configured = os.environ.get("MPLCONFIGDIR")
    if configured:
        return Path(configured)
    cache = Path(tempfile.gettempdir()) / f"green-ecc-matplotlib-{os.getpid()}"
    os.environ["MPLCONFIGDIR"] = str(cache)
    return cache

