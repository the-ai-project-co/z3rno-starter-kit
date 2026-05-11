"""Smoke tests for every example in `examples/`.

Imports each module (which exercises the file syntactically and runs
all module-level code: imports, constant definitions) and asserts the
module exposes a callable `main()`. This is the import-time gate the
starter kit ships — actual interactive runs are documented in the
README and rely on a live server.

We don't *call* main() in tests because the examples talk to a live
z3rno-server. CI brings up the server elsewhere if interactive runs
are wanted; the smoke gate stays cheap and offline.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def _example_paths() -> list[Path]:
    """Every `NN_*.py` under examples/ (sorted, deterministic)."""
    return sorted(_EXAMPLES_DIR.glob("[0-9][0-9]_*.py"))


def _import_module(path: Path):
    """Import a Python file by path under a unique module name."""
    spec = importlib.util.spec_from_file_location(f"example_{path.stem}", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_examples_directory_has_five_demos() -> None:
    """The repo promise: five worked examples, ordered 01..05."""
    paths = _example_paths()
    assert len(paths) == 5, f"expected 5 examples, found {len(paths)}"
    stems = [p.stem.split("_", 1)[0] for p in paths]
    assert stems == ["01", "02", "03", "04", "05"]


@pytest.mark.parametrize("path", _example_paths(), ids=lambda p: p.stem)
def test_example_imports_cleanly(path: Path) -> None:
    """The module must import without raising."""
    _import_module(path)


@pytest.mark.parametrize("path", _example_paths(), ids=lambda p: p.stem)
def test_example_has_callable_main(path: Path) -> None:
    """Every example exposes ``main()`` so an outer driver can wire it in."""
    module = _import_module(path)
    assert hasattr(module, "main"), f"{path.name} is missing a top-level main()"
    assert callable(module.main), f"{path.name}.main is not callable"
