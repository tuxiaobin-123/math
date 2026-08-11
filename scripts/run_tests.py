#!/usr/bin/env python3
"""Small dependency-free runner for this repository's assert-style tests."""

from __future__ import annotations

import importlib.util
import inspect
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: Path):
    name = f"cumcm_lens_test_{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    passed = 0
    failed = 0
    for path in sorted((ROOT / "tests").glob("test_*.py")):
        module = load(path)
        for name, function in inspect.getmembers(module, inspect.isfunction):
            if not name.startswith("test_"):
                continue
            parameters = inspect.signature(function).parameters
            try:
                if not parameters:
                    function()
                elif list(parameters) == ["tmp_path"]:
                    with tempfile.TemporaryDirectory(prefix="cumcm-lens-test-") as directory:
                        function(Path(directory))
                else:
                    raise RuntimeError(f"unsupported fixture signature: {list(parameters)}")
                passed += 1
                print(f"PASS {path.name}::{name}")
            except Exception:
                failed += 1
                print(f"FAIL {path.name}::{name}")
                traceback.print_exc()
    print(f"TEST_SUMMARY passed={passed} failed={failed}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
