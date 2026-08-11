#!/usr/bin/env python3
"""Remove only disposable experiment runs and temporary report products."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

for relative in ("artifacts/runs", "reports/generated", "tmp"):
    path = ROOT / relative
    if path.exists():
        shutil.rmtree(path)
        print(f"removed {relative}")
