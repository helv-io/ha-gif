"""Load GIF helper modules without importing Home Assistant."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

_GIF_DIR = Path(__file__).resolve().parents[1] / "custom_components" / "gif"
_PKG = "gif_helpers"

if _PKG not in sys.modules:
    pkg = types.ModuleType(_PKG)
    pkg.__path__ = [str(_GIF_DIR)]
    sys.modules[_PKG] = pkg


def load_gif_module(name: str):
    """Import a submodule of custom_components/gif by file path."""
    full_name = f"{_PKG}.{name}"
    if full_name in sys.modules:
        return sys.modules[full_name]
    spec = importlib.util.spec_from_file_location(
        full_name, _GIF_DIR / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module
