#!/usr/bin/env python3
"""Rebuild forecast artifacts from the committed monthly series after forecast fixes."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from cumcm_lens.cases.yellow_river import forecast_24_months, sampling_plan

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "data" / "processed" / "2023E"


def main() -> None:
    monthly = pd.read_csv(CASE / "monthly_series.csv", parse_dates=["timestamp"])
    forecast, comparison = forecast_24_months(monthly)
    plan = sampling_plan(forecast)
    if len(forecast) != 24 or forecast["timestamp"].dt.to_period("M").nunique() != 24:
        raise RuntimeError("forecast must contain 24 distinct months")
    forecast.to_csv(CASE / "forecast_24_months.csv", index=False)
    plan.to_csv(CASE / "sampling_plan.csv", index=False)
    summary_path = CASE / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["forecast_comparison"] = comparison
    summary.setdefault("artifact_repairs", []).append(
        {
            "version": "5.0.0",
            "fixes": [
                "future dates use monthly-start frequency",
                "damped forecast starts from fitted trend endpoint",
            ],
        }
    )
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"rebuilt {len(forecast)} monthly forecasts: {forecast.timestamp.min().date()} to {forecast.timestamp.max().date()}")


if __name__ == "__main__":
    main()
