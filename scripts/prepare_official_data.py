#!/usr/bin/env python3
"""Extract only the official files required by the three case studies."""

from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

from download_official_data import ARCHIVES, RAW_DIR, sha256

ROOT = Path(__file__).resolve().parents[1]
EXTRACTED = RAW_DIR / "extracted"


def require_verified(year: str) -> Path:
    spec = ARCHIVES[year]
    path = RAW_DIR / spec["filename"]
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; run download_official_data.py first")
    actual = sha256(path)
    if actual != spec["sha256"]:
        raise RuntimeError(f"{path.name}: expected {spec['sha256']}, got {actual}")
    return path


def extract_rar(archive: Path, output: Path, fragment: str | None = None) -> None:
    command = ["node", str(ROOT / "scripts" / "extract_rar.cjs"), str(archive), str(output)]
    if fragment:
        command.append(fragment)
    subprocess.run(command, check=True)


def prepare_2016() -> None:
    archive = require_verified("2016")
    output = EXTRACTED / "2016A"
    extract_rar(archive, output, "problem-A-Chinese")


def prepare_2023() -> None:
    archive = require_verified("2023")
    staging = EXTRACTED / "_2023"
    output = EXTRACTED / "2023E"
    extract_rar(archive, staging, "E题.rar")
    nested = next(staging.rglob("E题.rar"))
    extract_rar(nested, output)
    shutil.rmtree(staging)


def prepare_2024() -> None:
    archive = require_verified("2024")
    output = EXTRACTED / "2024C"
    output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as package:
        selected = [name for name in package.namelist() if "/C题/" in name or name.startswith("C题/")]
        if not selected:
            raise RuntimeError("Official 2024 archive does not contain the C problem folder")
        for name in selected:
            if name.endswith("/"):
                continue
            destination = output / Path(name).name
            with package.open(name) as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target)


def main() -> None:
    for prepare in (prepare_2016, prepare_2023, prepare_2024):
        prepare()
    print(f"Prepared official files under {EXTRACTED.relative_to(ROOT)}")
    print("Next: cumcm-lens run-all")


if __name__ == "__main__":
    main()
