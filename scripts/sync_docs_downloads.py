#!/usr/bin/env python3
"""Copy stable PDF deliverables into the GitHub Pages document root."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "output" / "pdf"
TARGET = ROOT / "docs" / "downloads"
FILES = [
    "CUMCM_Lens_V5_严谨训练手册.pdf",
    "CUMCM_Lens_V5_训练作业册.pdf",
    "2023E_yellow_river.pdf",
    "2016A_mooring.pdf",
    "2024C_crop_planning.pdf",
]


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        source = SOURCE / name
        if not source.is_file():
            raise FileNotFoundError(source)
        shutil.copy2(source, TARGET / name)
        print(f"synced docs/downloads/{name}")


if __name__ == "__main__":
    main()
