"""Command line entry point for all reproducible experiments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cumcm_lens.cases.crop_planning import run_case as run_crop
from cumcm_lens.cases.mooring import run_case as run_mooring
from cumcm_lens.cases.yellow_river import run_case as run_yellow_river
from cumcm_lens.core.plots import build_all_figures

ROOT = Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cumcm-lens")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("run-2023e", "run-2016a", "run-2024c", "run-all", "paper-figures"):
        subparsers.add_parser(command)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    raw = ROOT / "data" / "raw"
    processed = ROOT / "data" / "processed"
    results = {}
    if args.command in {"run-2023e", "run-all"}:
        results["2023E"] = run_yellow_river(raw, processed / "2023E")
    if args.command in {"run-2016a", "run-all"}:
        results["2016A"] = run_mooring(processed / "2016A")
    if args.command in {"run-2024c", "run-all"}:
        results["2024C"] = run_crop(raw, processed / "2024C")
    if args.command in {"paper-figures", "run-all"}:
        figures = build_all_figures(processed, ROOT / "reports" / "figures")
        results["figures"] = [str(path.relative_to(ROOT)) for path in figures]
    print(json.dumps({"completed": list(results)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
