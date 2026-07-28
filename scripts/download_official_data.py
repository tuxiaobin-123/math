#!/usr/bin/env python3
"""Download the three official CUMCM archives and verify their hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"

ARCHIVES = {
    "2016": {
        "filename": "CUMCM2016Problems.rar",
        "url": "https://www.mcm.edu.cn/upload_cn/node/393/"
        "UxYMjfW4fd0a5cd7a21951b49232088d2af3f4e8.rar",
        "sha256": "a20eac15b174e79ac5491378dfec5138c1f990d8f55d2ba037cadb69cb685dad",
    },
    "2023": {
        "filename": "CUMCM2023Problems.rar",
        "url": "https://www.mcm.edu.cn/upload_cn/node/690/"
        "Y20WPner9fa62862794e6dc82731a5561ce1132f.rar",
        "sha256": "37b1010672adcf35831e798264cc69db616027f2287cfeae3c4ee6daf03ae4e6",
    },
    "2024": {
        "filename": "CUMCM2024Problems.zip",
        "url": "https://www.mcm.edu.cn/upload_cn/node/725/"
        "pmkWxf8H9cfe9984c1a1a5b1263e5dd3b5596ed5.zip",
        "sha256": "38d9effcede947354f9e9a9c2b4fc68947d83a77c2ff75737e9a662888158726",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "CUMCM-Lens/0.1"})
    partial = destination.with_suffix(destination.suffix + ".part")
    with urllib.request.urlopen(request, timeout=120) as response, partial.open("wb") as output:
        while block := response.read(1024 * 1024):
            output.write(block)
    partial.replace(destination)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", choices=[*ARCHIVES, "all"], default="all")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    selected = ARCHIVES if args.year == "all" else {args.year: ARCHIVES[args.year]}
    manifest: dict[str, dict[str, str | int]] = {}
    for year, spec in selected.items():
        path = RAW_DIR / spec["filename"]
        if not path.exists():
            if args.verify_only:
                raise FileNotFoundError(path)
            print(f"[download] {year}: {spec['url']}")
            download(spec["url"], path)
        actual = sha256(path)
        if actual != spec["sha256"]:
            raise RuntimeError(f"{path.name}: SHA-256 mismatch: {actual}")
        print(f"[verified] {path.name}")
        manifest[year] = {
            **spec,
            "bytes": path.stat().st_size,
            "verified_sha256": actual,
        }
    (RAW_DIR / "verified_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
