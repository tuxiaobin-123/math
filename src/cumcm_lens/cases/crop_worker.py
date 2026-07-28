"""Isolated worker for one 2024C MILP scenario."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cumcm_lens.cases.crop_planning import (
    SCENARIOS,
    load_official_data,
    locate_attachments,
    solve_scenario,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--scenario", required=True)
    args = parser.parse_args()
    scenario_map = {scenario.name: scenario for scenario in SCENARIOS}
    if args.scenario not in scenario_map:
        raise ValueError(f"Unknown scenario: {args.scenario}")
    attachments = locate_attachments(args.raw_root)
    values = load_official_data(attachments["附件1.xlsx"], attachments["附件2.xlsx"])
    schedule, metadata = solve_scenario(*values[:5], scenario_map[args.scenario])
    args.output_dir.mkdir(parents=True, exist_ok=True)
    schedule.to_csv(args.output_dir / f"schedule_{args.scenario}.csv", index=False)
    (args.output_dir / f"metadata_{args.scenario}.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
