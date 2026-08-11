"""One-command publication figures from persisted, reviewed results."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/cumcm-lens-matplotlib")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def yellow_river_figures(processed: Path, figures: Path) -> list[Path]:
    summary = json.loads((processed / "summary.json").read_text(encoding="utf-8"))
    predictions = summary["model"]["test_predictions"]
    actual = np.asarray(predictions["actual"])
    best = summary["model"]["best_model"]
    predicted = np.asarray(predictions[best])
    residual = actual - predicted
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].scatter(predicted, actual, s=12, alpha=0.55)
    bound = max(actual.max(), predicted.max())
    axes[0].plot([0, bound], [0, bound], "--", color="#d55e00")
    axes[0].set(xlabel="Predicted sediment (kg/m³)", ylabel="Observed sediment (kg/m³)")
    axes[1].scatter(predicted, residual, s=12, alpha=0.55)
    axes[1].axhline(0, ls="--", color="#d55e00")
    axes[1].set(xlabel="Predicted", ylabel="Residual")
    path1 = figures / "2023E_residual_audit.png"
    _save(fig, path1)

    monthly = pd.read_csv(processed / "monthly_series.csv", parse_dates=["timestamp"])
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    axes[0].plot(monthly["timestamp"], monthly["discharge_m3s"], color="#0072b2")
    axes[0].set_ylabel("Discharge (m³/s)")
    axes[1].plot(monthly["timestamp"], monthly["sediment_kgm3"], color="#d55e00")
    axes[1].set_ylabel("Sediment (kg/m³)")
    path2 = figures / "2023E_monthly_series.png"
    _save(fig, path2)
    return [path1, path2]


def mooring_figures(processed: Path, figures: Path) -> list[Path]:
    state = pd.read_csv(processed / "question_1_2_states.csv")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(state["wind_ms"], state["barrel_angle_deg"], "o-", label="Barrel tilt")
    ax.plot(state["wind_ms"], state["anchor_angle_deg"], "s-", label="Anchor angle")
    ax.axhline(5, color="#d55e00", ls="--", label="Barrel limit")
    ax.axhline(16, color="#cc79a7", ls=":", label="Anchor limit")
    ax.set(xlabel="Wind speed (m/s)", ylabel="Angle (degree)")
    ax.legend()
    path1 = figures / "2016A_constraint_angles.png"
    _save(fig, path1)

    sensitivity = pd.read_csv(processed / "sensitivity.csv")
    fig, ax = plt.subplots(figsize=(9, 4))
    for name, group in sensitivity.groupby("parameter"):
        ax.plot(group["factor"], group["barrel_angle_deg"], marker="o", label=name)
    ax.axhline(5, color="#d55e00", ls="--")
    ax.set(xlabel="Parameter multiplier", ylabel="Barrel tilt (degree)")
    ax.legend(ncol=2)
    path2 = figures / "2016A_sensitivity.png"
    _save(fig, path2)
    return [path1, path2]


def crop_figures(processed: Path, figures: Path) -> list[Path]:
    summary = json.loads((processed / "summary.json").read_text(encoding="utf-8"))
    names = [item["scenario"] for item in summary["models"]]
    profits = [item["objective_profit_yuan"] / 1e6 for item in summary["models"]]
    gaps = [item["mip_gap"] * 100 for item in summary["models"]]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].bar(names, profits, color=["#0072b2", "#009e73", "#e69f00"])
    axes[0].set_ylabel("Model objective (million CNY)")
    axes[0].tick_params(axis="x", rotation=15)
    axes[1].bar(names, gaps, color=["#0072b2", "#009e73", "#e69f00"])
    axes[1].set_ylabel("Reported MIP gap (%)")
    axes[1].tick_params(axis="x", rotation=15)
    path1 = figures / "2024C_model_comparison.png"
    _save(fig, path1)

    sensitivity = pd.read_csv(processed / "sensitivity.csv")
    pivot = sensitivity.pivot_table(
        index="yield_factor",
        columns="price_factor",
        values="uncapped_profit_yuan",
        aggfunc="mean",
    )
    fig, ax = plt.subplots(figsize=(6, 5))
    image = ax.imshow(pivot.to_numpy() / 1e6, cmap="YlGnBu")
    ax.set_xticks(range(len(pivot.columns)), [f"{value:.1f}" for value in pivot.columns])
    ax.set_yticks(range(len(pivot.index)), [f"{value:.1f}" for value in pivot.index])
    ax.set(xlabel="Price multiplier", ylabel="Yield multiplier")
    fig.colorbar(image, ax=ax, label="Uncapped profit (million CNY)")
    path2 = figures / "2024C_sensitivity.png"
    _save(fig, path2)
    return [path1, path2]


def build_all_figures(processed_root: Path, figures_root: Path) -> list[Path]:
    return [
        *yellow_river_figures(processed_root / "2023E", figures_root),
        *mooring_figures(processed_root / "2016A", figures_root),
        *crop_figures(processed_root / "2024C", figures_root),
    ]
