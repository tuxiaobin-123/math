#!/usr/bin/env python3
"""Fetch the pinned open-source Chinese font and convert WOFF to local TTF."""

from __future__ import annotations

import hashlib
import io
import tarfile
import urllib.request
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = ROOT / "assets" / "fonts"
WOFF = FONT_DIR / "NotoSansSC-Regular.woff"
TTF = FONT_DIR / "NotoSansSC-Regular.ttf"
URL = "https://registry.npmjs.org/@fontsource/noto-sans-sc/-/noto-sans-sc-5.2.8.tgz"
MEMBER = "package/files/noto-sans-sc-chinese-simplified-400-normal.woff"
EXPECTED_SHA256 = "1aac13a9ba6d1fd92f8a7294c3119dc4fed54c517bb6bbf021a75850b568d3ea"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    if TTF.exists():
        print(f"font ready: {TTF.relative_to(ROOT)}")
        return
    request = urllib.request.Request(URL, headers={"User-Agent": "CUMCM-Lens/0.1"})
    with urllib.request.urlopen(request, timeout=120) as response:
        archive = response.read()
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
        extracted = bundle.extractfile(MEMBER)
        if extracted is None:
            raise RuntimeError(f"font member missing from package: {MEMBER}")
        WOFF.write_bytes(extracted.read())
    actual = digest(WOFF)
    if actual != EXPECTED_SHA256:
        WOFF.unlink(missing_ok=True)
        raise RuntimeError(f"font SHA-256 mismatch: {actual}")
    font = TTFont(str(WOFF))
    font.flavor = None
    font.save(str(TTF))
    WOFF.unlink()
    print(f"font ready: {TTF.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
