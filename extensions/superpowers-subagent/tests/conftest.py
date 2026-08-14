"""Load the hyphenated extension directory as a Python package for unit tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

LOADER_PACKAGE = "tau_test_extension"
IMPLEMENTATION_PACKAGE = f"{LOADER_PACKAGE}.superpowers_subagent"
PACKAGE_ROOT = Path(__file__).resolve().parents[1]

if "superpowers_subagent" not in sys.modules:
    spec = importlib.util.spec_from_file_location(
        LOADER_PACKAGE,
        PACKAGE_ROOT / "extension.py",
        submodule_search_locations=[str(PACKAGE_ROOT)],
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[LOADER_PACKAGE] = module
    spec.loader.exec_module(module)
    for name, loaded in tuple(sys.modules.items()):
        if name == IMPLEMENTATION_PACKAGE or name.startswith(f"{IMPLEMENTATION_PACKAGE}."):
            alias = name.removeprefix(f"{LOADER_PACKAGE}.")
            sys.modules[alias] = loaded
