"""2024 CUMCM C: whole-plot MILP under sales and uncertainty scenarios."""

from __future__ import annotations

import json
import gc
import time
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix

YEARS = list(range(2024, 2031))


@dataclass(frozen=True)
class CropScenario:
    name: str
    surplus_discount: float
    robust: bool = False


SCENARIOS = [
    CropScenario("waste", surplus_discount=0.0),
    CropScenario("half_price", surplus_discount=0.5),
    CropScenario("robust_worst_case", surplus_discount=0.0, robust=True),
]


def locate_attachments(raw_root: Path) -> dict[str, Path]:
    base = raw_root / "extracted" / "2024C"
    mapping = {path.name: path for path in base.rglob("*.xlsx")}
    missing = [name for name in ("附件1.xlsx", "附件2.xlsx") if name not in mapping]
    if missing:
        raise FileNotFoundError(f"2024C official attachment(s) missing: {missing}")
    return mapping


def parse_price(value: Any) -> tuple[float, float, float]:
    parts = str(value).replace("—", "-").split("-")
    if len(parts) != 2:
        number = float(parts[0])
        return number, number, number
    low, high = map(float, parts)
    return low, high, (low + high) / 2


def load_official_data(
    attachment1: Path, attachment2: Path
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    land = pd.read_excel(attachment1, sheet_name="乡村的现有耕地").iloc[:, :3]
    land.columns = ["plot", "land_type", "area_mu"]
    land = land.dropna(subset=["plot", "land_type", "area_mu"]).copy()
    land["plot"] = land["plot"].astype(str).str.strip()
    land["land_type"] = land["land_type"].astype(str).str.strip()
    land["area_mu"] = pd.to_numeric(land["area_mu"], errors="raise")

    crops = pd.read_excel(attachment1, sheet_name="乡村种植的农作物").iloc[:, :3]
    crops.columns = ["crop_id", "crop_name", "crop_type"]
    crops["crop_id"] = pd.to_numeric(crops["crop_id"], errors="coerce")
    crops = crops.dropna(subset=["crop_id", "crop_name", "crop_type"]).copy()
    crops["crop_id"] = crops["crop_id"].astype(int)
    crops["crop_name"] = crops["crop_name"].astype(str).str.strip()
    crops["crop_type"] = crops["crop_type"].astype(str).str.strip()

    planted = pd.read_excel(attachment2, sheet_name="2023年的农作物种植情况").iloc[:, :6]
    planted.columns = ["plot", "crop_id", "crop_name", "crop_type", "area_mu", "season"]
    # The official sheet uses merged cells: blank plot cells inherit the previous plot.
    planted["plot"] = planted["plot"].ffill()
    planted = planted.dropna(subset=["plot", "crop_id", "area_mu"]).copy()
    planted["plot"] = planted["plot"].astype(str).str.strip()
    planted["crop_id"] = pd.to_numeric(planted["crop_id"], errors="raise").astype(int)
    planted["area_mu"] = pd.to_numeric(planted["area_mu"], errors="raise")
    planted["season"] = planted["season"].astype(str).str.strip()

    stats = pd.read_excel(attachment2, sheet_name="2023年统计的相关数据").iloc[:, 1:8]
    stats.columns = [
        "crop_id",
        "crop_name",
        "land_type",
        "season",
        "yield_jin_mu",
        "cost_yuan_mu",
        "price_range",
    ]
    stats = stats.dropna(subset=["crop_id", "land_type", "season"]).copy()
    stats["crop_id"] = pd.to_numeric(stats["crop_id"], errors="raise").astype(int)
    stats["land_type"] = stats["land_type"].astype(str).str.strip()
    stats["season"] = stats["season"].astype(str).str.strip()
    stats["yield_jin_mu"] = pd.to_numeric(stats["yield_jin_mu"], errors="raise")
    stats["cost_yuan_mu"] = pd.to_numeric(stats["cost_yuan_mu"], errors="raise")
    price = stats["price_range"].map(parse_price)
    stats["price_low"] = price.map(lambda value: value[0])
    stats["price_high"] = price.map(lambda value: value[1])
    stats["price_mid"] = price.map(lambda value: value[2])

    plot_type = land.set_index("plot")["land_type"]
    yield_lookup = stats.set_index(["crop_id", "land_type", "season"])["yield_jin_mu"]
    demand_records = []
    for crop_id, group in planted.groupby("crop_id"):
        production = 0.0
        unmatched = 0
        for row in group.itertuples():
            stat_land, stat_season = official_stat_key(
                row.crop_id, plot_type[row.plot], row.season
            )
            key = (row.crop_id, stat_land, stat_season)
            if key in yield_lookup:
                production += row.area_mu * yield_lookup[key]
            else:
                unmatched += 1
        demand_records.append(
            {"crop_id": crop_id, "demand_2023_jin": production, "unmatched_rows": unmatched}
        )
    demand = pd.DataFrame(demand_records)
    quality = {
        "land_rows": len(land),
        "crop_rows": len(crops),
        "planting_rows_2023": len(planted),
        "statistics_rows": len(stats),
        "total_land_mu": float(land["area_mu"].sum()),
        "demand_unmatched_planting_rows": int(demand["unmatched_rows"].sum()),
    }
    return land, crops, planted, stats, demand, quality


def slots_for_plot(land_type: str) -> list[str]:
    if land_type in {"平旱地", "梯田", "山坡地"}:
        return ["单季"]
    return ["第一季", "第二季"]


def allowed_crops(land_type: str, season: str) -> list[int]:
    if land_type in {"平旱地", "梯田", "山坡地"}:
        return list(range(1, 16))
    if land_type == "水浇地":
        return [16, *range(17, 35)] if season == "第一季" else list(range(35, 38))
    if land_type == "普通大棚":
        return list(range(17, 35)) if season == "第一季" else list(range(38, 42))
    if land_type == "智慧大棚":
        return list(range(17, 35))
    raise ValueError(f"Unsupported land type {land_type}")


def official_stat_key(
    crop_id: int, land_type: str, planning_season: str
) -> tuple[str, str]:
    if land_type == "水浇地" and crop_id == 16:
        return land_type, "单季"
    if land_type == "智慧大棚" and planning_season == "第一季":
        # Explicit note in official attachment 2: first-season smart-greenhouse
        # yield/cost/price are identical to the ordinary-greenhouse first season.
        return "普通大棚", "第一季"
    return land_type, planning_season


def official_stat_season(crop_id: int, land_type: str, planning_season: str) -> str:
    return official_stat_key(crop_id, land_type, planning_season)[1]


def previous_2023_crop(planted: pd.DataFrame, plot: str, season: str) -> set[int]:
    rows = planted[planted["plot"].eq(plot)]
    if season == "第一季":
        rows = rows[rows["season"].isin(["第一季", "单季"])]
    elif season == "第二季":
        rows = rows[rows["season"].eq("第二季")]
    return set(rows["crop_id"].astype(int))


class LinearRows:
    def __init__(self) -> None:
        self.row: list[int] = []
        self.col: list[int] = []
        self.data: list[float] = []
        self.lower: list[float] = []
        self.upper: list[float] = []

    def add(self, coefficients: dict[int, float], lower: float, upper: float) -> None:
        index = len(self.lower)
        for column, value in coefficients.items():
            if value:
                self.row.append(index)
                self.col.append(column)
                self.data.append(float(value))
        self.lower.append(lower)
        self.upper.append(upper)

    def constraint(self, n_variables: int) -> LinearConstraint:
        matrix = coo_matrix(
            (self.data, (self.row, self.col)), shape=(len(self.lower), n_variables)
        ).tocsr()
        return LinearConstraint(matrix, np.array(self.lower), np.array(self.upper))


def coefficient_row(
    stats_lookup: pd.DataFrame,
    crop_id: int,
    land_type: str,
    season: str,
    year: int,
    scenario: CropScenario,
) -> dict[str, float]:
    stat_land, stat_season = official_stat_key(crop_id, land_type, season)
    row = stats_lookup.loc[(crop_id, stat_land, stat_season)]
    offset = year - 2023
    yield_factor = 0.9 if scenario.robust else 1.0
    cost_factor = 1.05**offset if scenario.robust else 1.0
    if scenario.robust:
        if "食用菌" in str(row["crop_type"]):
            price_factor = 0.95**offset
        else:
            price_factor = 1.0
        price = float(row["price_low"]) * price_factor
    else:
        price = float(row["price_mid"])
    return {
        "yield": float(row["yield_jin_mu"]) * yield_factor,
        "cost": float(row["cost_yuan_mu"]) * cost_factor,
        "price": price,
    }


def demand_cap(
    crop_id: int, year: int, base_demand: dict[int, float], scenario: CropScenario
) -> float:
    base = base_demand.get(crop_id, 0.0)
    offset = year - 2023
    if not scenario.robust:
        return base
    if crop_id in {6, 7}:  # wheat and maize: official range is +5% to +10% annually
        return base * 1.05**offset
    return base * 0.95  # conservative endpoint of the ±5% range


def solve_scenario(
    land: pd.DataFrame,
    crops: pd.DataFrame,
    planted: pd.DataFrame,
    stats: pd.DataFrame,
    demand: pd.DataFrame,
    scenario: CropScenario,
    *,
    time_limit: float = 10.0,
    enforce_legume: bool = True,
    enforce_rotation: bool = True,
    candidate_limit: int = 6,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    crop_types = crops.set_index("crop_id")["crop_type"]
    enriched = stats.merge(
        crops[["crop_id", "crop_type"]], on="crop_id", how="left", validate="many_to_one"
    )
    stats_lookup = enriched.set_index(["crop_id", "land_type", "season"])
    base_demand = demand.set_index("crop_id")["demand_2023_jin"].to_dict()
    bean_ids = set(crops[crops["crop_type"].str.contains("豆类")]["crop_id"])

    candidate_map: dict[tuple[str, str], list[int]] = {}
    for land_type in land["land_type"].unique():
        for season in slots_for_plot(land_type):
            scored = []
            for crop_id in allowed_crops(land_type, season):
                stat_land, stat_season = official_stat_key(crop_id, land_type, season)
                key = (crop_id, stat_land, stat_season)
                if key in stats_lookup.index:
                    row = stats_lookup.loc[key]
                    score = float(row["yield_jin_mu"] * row["price_mid"] - row["cost_yuan_mu"])
                    scored.append((crop_id, score))
            top = {
                crop_id
                for crop_id, _ in sorted(scored, key=lambda item: item[1], reverse=True)[
                    :candidate_limit
                ]
            }
            # Preserve every eligible legume so that the official three-year rule remains feasible.
            top |= {crop_id for crop_id, _ in scored if crop_id in bean_ids}
            if land_type == "水浇地" and season == "第一季":
                top.add(16)
            candidate_map[(land_type, season)] = sorted(top)

    x_keys: list[tuple[str, str, int, int, float, str]] = []
    for plot_row in land.itertuples():
        for year in YEARS:
            for season in slots_for_plot(plot_row.land_type):
                for crop_id in candidate_map[(plot_row.land_type, season)]:
                    stat_land, stat_season = official_stat_key(
                        crop_id, plot_row.land_type, season
                    )
                    key = (crop_id, stat_land, stat_season)
                    if key in stats_lookup.index:
                        x_keys.append(
                            (
                                plot_row.plot,
                                plot_row.land_type,
                                year,
                                crop_id,
                                float(plot_row.area_mu),
                                season,
                            )
                        )
    x_index = {key: index for index, key in enumerate(x_keys)}
    sold_keys = [(crop_id, year) for crop_id in crops["crop_id"] for year in YEARS]
    sold_index = {
        key: len(x_keys) + index for index, key in enumerate(sold_keys)
    }
    n_variables = len(x_keys) + len(sold_keys)
    objective = np.zeros(n_variables)
    upper_bounds = np.ones(n_variables)
    integrality = np.zeros(n_variables)
    integrality[: len(x_keys)] = 1
    upper_bounds[len(x_keys) :] = np.inf

    production_coeff: dict[tuple[int, int], dict[int, float]] = {
        key: {} for key in sold_keys
    }
    for key, index in x_index.items():
        plot, land_type, year, crop_id, area, season = key
        coefficient = coefficient_row(
            stats_lookup, crop_id, land_type, season, year, scenario
        )
        production = area * coefficient["yield"]
        production_coeff[(crop_id, year)][index] = production
        objective[index] = area * coefficient["cost"] - (
            scenario.surplus_discount * coefficient["price"] * production
        )
    for key, index in sold_index.items():
        crop_id, year = key
        # Sales are aggregated across land types; official price is crop/land/season-specific.
        # Use production-weighted revenue through the x term would be nonlinear, so use the
        # crop-year median price and expose this approximation.
        subset = stats_lookup.reset_index()
        subset = subset[subset["crop_id"].eq(crop_id)]
        if subset.empty:
            price = 0.0
        elif scenario.robust:
            price = float(subset["price_low"].median())
            if "食用菌" in str(crop_types.get(crop_id, "")):
                price *= 0.95 ** (year - 2023)
        else:
            price = float(subset["price_mid"].median())
        objective[index] = -(1 - scenario.surplus_discount) * price

    rows = LinearRows()
    # One whole-plot crop per active slot. Irrigated second season is inactive when rice is used.
    for plot_row in land.itertuples():
        for year in YEARS:
            season1 = {
                index: 1.0
                for key, index in x_index.items()
                if key[0] == plot_row.plot and key[2] == year and key[5] in {"单季", "第一季"}
            }
            rows.add(season1, 1.0, 1.0)
            if plot_row.land_type == "水浇地":
                second = {
                    index: 1.0
                    for key, index in x_index.items()
                    if key[0] == plot_row.plot and key[2] == year and key[5] == "第二季"
                }
                rice_key = (
                    plot_row.plot,
                    plot_row.land_type,
                    year,
                    16,
                    float(plot_row.area_mu),
                    "第一季",
                )
                second[x_index[rice_key]] = 1.0
                rows.add(second, 1.0, 1.0)
            elif plot_row.land_type in {"普通大棚", "智慧大棚"}:
                second = {
                    index: 1.0
                    for key, index in x_index.items()
                    if key[0] == plot_row.plot and key[2] == year and key[5] == "第二季"
                }
                rows.add(second, 1.0, 1.0)

    # No identical crop in adjacent *active* seasons.
    if enforce_rotation:
        for plot_row in land.itertuples():
            plot_keys = [key for key in x_keys if key[0] == plot_row.plot]
            chronological_slots = [
                (year, season)
                for year in YEARS
                for season in slots_for_plot(plot_row.land_type)
            ]
            slot_members = {
                slot: [key for key in plot_keys if key[2] == slot[0] and key[5] == slot[1]]
                for slot in chronological_slots
            }
            # Official 2023 rows can contain several crops in one merged plot/season.
            history = planted[planted["plot"].eq(plot_row.plot)]
            if history["season"].eq("第二季").any():
                last_2023 = set(
                    history.loc[history["season"].eq("第二季"), "crop_id"].astype(int)
                )
            else:
                last_2023 = set(history["crop_id"].astype(int))
            for key in slot_members[chronological_slots[0]]:
                if key[3] in last_2023:
                    rows.add({x_index[key]: 1.0}, -np.inf, 0.0)
            for current_slot, next_slot in zip(
                chronological_slots, chronological_slots[1:]
            ):
                current_by_crop = {key[3]: key for key in slot_members[current_slot]}
                next_by_crop = {key[3]: key for key in slot_members[next_slot]}
                for crop_id in current_by_crop.keys() & next_by_crop.keys():
                    rows.add(
                        {
                            x_index[current_by_crop[crop_id]]: 1.0,
                            x_index[next_by_crop[crop_id]]: 1.0,
                        },
                        -np.inf,
                        1.0,
                    )
            # When rice is planted, the irrigated second season is inactive, so
            # rice in consecutive years would still be consecutive planting.
            if plot_row.land_type == "水浇地":
                for year in YEARS[:-1]:
                    rice_now = next(
                        key
                        for key in plot_keys
                        if key[2] == year and key[3] == 16
                    )
                    rice_next = next(
                        key
                        for key in plot_keys
                        if key[2] == year + 1 and key[3] == 16
                    )
                    rows.add(
                        {x_index[rice_now]: 1.0, x_index[rice_next]: 1.0},
                        -np.inf,
                        1.0,
                    )

    # Every plot has a legume crop at least once in every rolling three-year window.
    for plot_row in land.itertuples():
        for start_year in range(2024, 2029):
            coefficients = {
                index: 1.0
                for key, index in x_index.items()
                if key[0] == plot_row.plot
                and start_year <= key[2] <= start_year + 2
                and key[3] in bean_ids
            }
            rows.add(coefficients, 1.0 if enforce_legume else 0.0, np.inf)

    # sold <= production and sold <= scenario demand
    for key in sold_keys:
        sale_index = sold_index[key]
        coefficients = {sale_index: 1.0}
        coefficients.update(
            {index: -value for index, value in production_coeff[key].items()}
        )
        rows.add(coefficients, -np.inf, 0.0)
        rows.add(
            {sale_index: 1.0},
            -np.inf,
            demand_cap(key[0], key[1], base_demand, scenario),
        )

    start = time.perf_counter()
    solution = milp(
        c=objective,
        integrality=integrality,
        bounds=Bounds(np.zeros(n_variables), upper_bounds),
        constraints=rows.constraint(n_variables),
        options={"time_limit": time_limit, "mip_rel_gap": 0.015, "presolve": True},
    )
    runtime = time.perf_counter() - start
    if solution.x is None:
        raise RuntimeError(f"MILP {scenario.name} failed: {solution.message}")
    records = []
    for key, index in x_index.items():
        if solution.x[index] > 0.5:
            plot, land_type, year, crop_id, area, season = key
            values = coefficient_row(
                stats_lookup, crop_id, land_type, season, year, scenario
            )
            records.append(
                {
                    "plot": plot,
                    "land_type": land_type,
                    "year": year,
                    "season": season,
                    "stat_land_type": official_stat_key(
                        crop_id, land_type, season
                    )[0],
                    "stat_season": official_stat_season(crop_id, land_type, season),
                    "crop_id": crop_id,
                    "crop_name": crops.set_index("crop_id").loc[crop_id, "crop_name"],
                    "crop_type": crop_types[crop_id],
                    "area_mu": area,
                    "yield_jin_mu": values["yield"],
                    "production_jin": area * values["yield"],
                    "cost_yuan": area * values["cost"],
                }
            )
    schedule = pd.DataFrame(records).sort_values(["year", "plot", "season"])
    audit = audit_schedule(schedule, land, planted)
    metadata = {
        "scenario": scenario.name,
        "success": bool(solution.success),
        "solver_status": int(solution.status),
        "solver_message": solution.message,
        "objective_profit_yuan": float(-solution.fun),
        "mip_gap": float(getattr(solution, "mip_gap", np.nan)),
        "runtime_seconds": runtime,
        "binary_variables": len(x_keys),
        "continuous_variables": len(sold_keys),
        "constraints": len(rows.lower),
        "candidate_limit_per_land_season_plus_all_legumes": candidate_limit,
        "audits": audit,
        "assumption": (
            "为使轮作约束可被严格审计，每个地块每季只选一种作物；"
            "这是官方允许方案的保守子集，不声称是允许分区混种时的全局最优。"
        ),
    }
    del solution
    gc.collect()
    return schedule, metadata


def audit_schedule(
    schedule: pd.DataFrame, land: pd.DataFrame, planted: pd.DataFrame
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    capacity_violations = 0
    land_area = land.set_index("plot")["area_mu"]
    for (plot, year, season), group in schedule.groupby(["plot", "year", "season"]):
        capacity_violations += int(group["area_mu"].sum() > land_area[plot] + 1e-8)
    findings.append(
        {
            "name": "plot_capacity",
            "passed": capacity_violations == 0,
            "severity": "error",
            "observed": capacity_violations,
            "expected": "0 violations",
        }
    )
    rotation_violations = 0
    season_order = {"单季": 1, "第一季": 1, "第二季": 2}
    for plot in land["plot"]:
        history = planted[planted["plot"].eq(plot)].copy()
        history["year"] = 2023
        future = schedule[schedule["plot"].eq(plot)].copy()
        combined = pd.concat(
            [
                history[["year", "season", "crop_id"]],
                future[["year", "season", "crop_id"]],
            ],
            ignore_index=True,
        )
        combined["season_order"] = combined["season"].map(season_order)
        periods = []
        for (year, order), group in combined.groupby(["year", "season_order"], sort=True):
            periods.append((int(year), int(order), set(group["crop_id"].astype(int))))
        periods.sort(key=lambda item: (item[0], item[1]))
        for current, following in zip(periods, periods[1:]):
            rotation_violations += len(current[2] & following[2])
    findings.append(
        {
            "name": "consecutive_crop",
            "passed": bool(rotation_violations == 0),
            "severity": "error",
            "observed": int(rotation_violations),
            "expected": "0 violations against 2023 and adjacent years",
        }
    )
    bean_violations = 0
    for plot in land["plot"]:
        group = schedule[schedule["plot"].eq(plot)]
        for start in range(2024, 2029):
            window = group[group["year"].between(start, start + 2)]
            bean_violations += int(~window["crop_type"].str.contains("豆类").any())
    findings.append(
        {
            "name": "legume_in_every_three_year_window",
            "passed": bean_violations == 0,
            "severity": "error",
            "observed": bean_violations,
            "expected": "0 plot-window violations",
        }
    )
    eligibility_violations = sum(
        row.crop_id not in allowed_crops(row.land_type, row.season)
        for row in schedule.itertuples()
    )
    findings.append(
        {
            "name": "land_crop_eligibility",
            "passed": eligibility_violations == 0,
            "severity": "error",
            "observed": int(eligibility_violations),
            "expected": "0 violations",
        }
    )
    return findings


def repeated_2023_baseline(
    land: pd.DataFrame, planted: pd.DataFrame
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    records = []
    land_type = land.set_index("plot")["land_type"]
    for year in YEARS:
        for row in planted.itertuples():
            records.append(
                {
                    "plot": row.plot,
                    "land_type": land_type[row.plot],
                    "year": year,
                    "season": row.season,
                    "crop_id": row.crop_id,
                    "crop_name": row.crop_name,
                    "crop_type": row.crop_type,
                    "area_mu": row.area_mu,
                }
            )
    baseline = pd.DataFrame(records)
    return baseline, audit_schedule(baseline, land, planted)


def sensitivity_from_schedules(
    schedules: dict[str, pd.DataFrame], stats: pd.DataFrame, demand: pd.DataFrame
) -> pd.DataFrame:
    records = []
    for name, schedule in schedules.items():
        merged = schedule.merge(
            stats[
                [
                    "crop_id",
                    "land_type",
                    "season",
                    "yield_jin_mu",
                    "cost_yuan_mu",
                    "price_mid",
                ]
            ],
            left_on=["crop_id", "stat_land_type", "stat_season"],
            right_on=["crop_id", "land_type", "season"],
            how="left",
        )
        for price_factor in (0.9, 1.0, 1.1):
            for yield_factor in (0.9, 1.0, 1.1):
                revenue = (
                    merged["area_mu"]
                    * merged["yield_jin_mu_y"].fillna(merged["yield_jin_mu_x"])
                    * yield_factor
                    * merged["price_mid"]
                    * price_factor
                ).sum()
                cost = (merged["area_mu"] * merged["cost_yuan_mu"]).sum()
                records.append(
                    {
                        "model": name,
                        "price_factor": price_factor,
                        "yield_factor": yield_factor,
                        "uncapped_profit_yuan": float(revenue - cost),
                    }
                )
    return pd.DataFrame(records)


def run_case(raw_root: Path, output_dir: Path) -> dict[str, Any]:
    attachments = locate_attachments(raw_root)
    land, crops, planted, stats, demand, quality = load_official_data(
        attachments["附件1.xlsx"], attachments["附件2.xlsx"]
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    baseline, baseline_audit = repeated_2023_baseline(land, planted)
    baseline.to_csv(output_dir / "baseline_repeat_2023.csv", index=False)
    schedules: dict[str, pd.DataFrame] = {}
    model_results = []
    for scenario in SCENARIOS:
        # HiGHS can retain native memory between large MILPs. Isolating each model
        # also makes a failed scenario unable to corrupt the other experiment records.
        environment = os.environ.copy()
        subprocess.run(
            [
                sys.executable,
                "-m",
                "cumcm_lens.cases.crop_worker",
                "--raw-root",
                str(raw_root),
                "--output-dir",
                str(output_dir),
                "--scenario",
                scenario.name,
            ],
            check=True,
            env=environment,
        )
        schedule = pd.read_csv(output_dir / f"schedule_{scenario.name}.csv")
        metadata = json.loads(
            (output_dir / f"metadata_{scenario.name}.json").read_text(encoding="utf-8")
        )
        schedules[scenario.name] = schedule
        model_results.append(metadata)
    sensitivity = sensitivity_from_schedules(schedules, stats, demand)
    sensitivity.to_csv(output_dir / "sensitivity.csv", index=False)
    demand.drop(columns=["unmatched_rows"]).to_csv(output_dir / "demand_2023.csv", index=False)
    summary = {
        "case": "2024C",
        "source": "official attachments 1 and 2",
        "quality": quality,
        "baseline": {
            "name": "repeat_2023",
            "purpose": "deliberately simple diagnostic baseline, not a feasible recommendation",
            "audits": baseline_audit,
        },
        "models": model_results,
        "assumptions_and_boundaries": [
            "每地块每季只种一种作物，以便严格表达逐地块轮作；因此最优值是原题可行域的保守下界。",
            "常规两种情景采用2023年销量上限不变；鲁棒情景采用题面区间的保守端点。",
            "销量变量按作物—年份聚合，销售价格采用该作物适用地类/季次价格的中位数。",
            "结果不冒充竞赛标准答案；应通过附件3模板另行导出并人工复核。",
        ],
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    return summary
