"""2023 CUMCM E: auditable water-sediment monitoring workflow."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.signal import find_peaks
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from cumcm_lens.core.audit import (
    chronological_split_audit,
    feature_target_overlap_audit,
    finite_values_audit,
)
from cumcm_lens.core.metrics import regression_metrics

FEATURES = [
    "water_level_m",
    "discharge_m3s",
    "trend_days",
    "doy_sin",
    "doy_cos",
    "hour_sin",
    "hour_cos",
]


def locate_attachments(raw_root: Path) -> dict[str, Path]:
    base = raw_root / "extracted" / "2023E"
    files = list(base.rglob("*.xlsx"))
    mapping = {path.name: path for path in files}
    required = ["附件1.xlsx", "附件2.xlsx", "附件3.xlsx"]
    missing = [name for name in required if name not in mapping]
    if missing:
        raise FileNotFoundError(f"2023E official attachment(s) missing: {missing}")
    return {name: mapping[name] for name in required}


def load_monitoring(path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Parse all six sheets and preserve measurement missingness."""
    pieces = []
    raw_rows = 0
    for sheet in pd.ExcelFile(path).sheet_names:
        source = pd.read_excel(path, sheet_name=sheet)
        source.columns = [str(column).strip() for column in source.columns]
        raw_rows += len(source)
        source = source.iloc[:, :7].copy()
        source.columns = [
            "year",
            "month",
            "day",
            "time",
            "water_level_m",
            "discharge_m3s",
            "sediment_kgm3",
        ]
        source[["year", "month", "day"]] = source[["year", "month", "day"]].ffill()
        date = pd.to_datetime(
            {
                "year": pd.to_numeric(source["year"], errors="coerce"),
                "month": pd.to_numeric(source["month"], errors="coerce"),
                "day": pd.to_numeric(source["day"], errors="coerce"),
            },
            errors="coerce",
        )
        time_text = source["time"].astype(str).str.extract(r"(\d{1,2}):(\d{2})")
        hour = pd.to_numeric(time_text[0], errors="coerce").fillna(0)
        minute = pd.to_numeric(time_text[1], errors="coerce").fillna(0)
        source["timestamp"] = date + pd.to_timedelta(hour, unit="h") + pd.to_timedelta(
            minute, unit="m"
        )
        for name in ("water_level_m", "discharge_m3s", "sediment_kgm3"):
            source[name] = pd.to_numeric(source[name], errors="coerce")
        pieces.append(
            source[["timestamp", "water_level_m", "discharge_m3s", "sediment_kgm3"]]
        )
    frame = pd.concat(pieces, ignore_index=True)
    invalid_time = int(frame["timestamp"].isna().sum())
    frame = frame.dropna(subset=["timestamp", "water_level_m", "discharge_m3s"])
    duplicate_rows = int(frame.duplicated("timestamp").sum())
    frame = (
        frame.groupby("timestamp", as_index=False)
        .agg(
            water_level_m=("water_level_m", "mean"),
            discharge_m3s=("discharge_m3s", "mean"),
            sediment_kgm3=("sediment_kgm3", "mean"),
        )
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    quality = {
        "raw_rows": raw_rows,
        "clean_rows": len(frame),
        "invalid_timestamp_rows_removed": invalid_time,
        "duplicate_timestamps_collapsed": duplicate_rows,
        "sediment_observed_rows": int(frame["sediment_kgm3"].notna().sum()),
        "sediment_missing_rate": float(frame["sediment_kgm3"].isna().mean()),
        "start": frame["timestamp"].min().isoformat(),
        "end": frame["timestamp"].max().isoformat(),
    }
    return frame, quality


def add_features(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    timestamp = result["timestamp"]
    result["trend_days"] = (timestamp - timestamp.min()).dt.total_seconds() / 86400
    day = timestamp.dt.dayofyear
    hour = timestamp.dt.hour + timestamp.dt.minute / 60
    result["doy_sin"] = np.sin(2 * np.pi * day / 365.25)
    result["doy_cos"] = np.cos(2 * np.pi * day / 365.25)
    result["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    result["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    return result


def train_sediment_models(
    frame: pd.DataFrame, seed: int = 42
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any]]:
    featured = add_features(frame)
    measured = featured.dropna(subset=["sediment_kgm3"]).copy()
    split = int(len(measured) * 0.8)
    train, test = measured.iloc[:split], measured.iloc[split:]
    models = {
        "ridge_log": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
        "random_forest_log": RandomForestRegressor(
            n_estimators=240,
            min_samples_leaf=4,
            max_features=0.8,
            random_state=seed,
            n_jobs=-1,
        ),
        "hist_gradient_boosting_log": HistGradientBoostingRegressor(
            max_iter=180, learning_rate=0.06, max_leaf_nodes=20, random_state=seed
        ),
    }
    comparison = []
    predictions: dict[str, np.ndarray] = {}
    runtimes = {}
    for name, model in models.items():
        started = time.perf_counter()
        model.fit(train[FEATURES], np.log1p(train["sediment_kgm3"]))
        prediction = np.maximum(np.expm1(model.predict(test[FEATURES])), 0)
        runtimes[name] = time.perf_counter() - started
        metrics = regression_metrics(test["sediment_kgm3"].to_numpy(), prediction)
        comparison.append({"model": name, **metrics, "runtime_seconds": runtimes[name]})
        predictions[name] = prediction
    comparison_frame = pd.DataFrame(comparison).sort_values("rmse")
    best_name = comparison_frame.iloc[0]["model"]
    best_model = models[str(best_name)]
    # Refit on all observed measurements for gap filling after honest holdout evaluation.
    best_model.fit(measured[FEATURES], np.log1p(measured["sediment_kgm3"]))
    all_prediction = np.maximum(np.expm1(best_model.predict(featured[FEATURES])), 0)
    featured["sediment_model_kgm3"] = all_prediction
    featured["sediment_filled_kgm3"] = featured["sediment_kgm3"].fillna(
        featured["sediment_model_kgm3"]
    )
    featured["prediction_source"] = np.where(
        featured["sediment_kgm3"].notna(), "observed", str(best_name)
    )
    audits = [
        chronological_split_audit(train["timestamp"], test["timestamp"]).to_dict(),
        feature_target_overlap_audit(FEATURES, "sediment_kgm3").to_dict(),
        finite_values_audit(all_prediction, "finite_predictions").to_dict(),
    ]
    detail = {
        "best_model": best_name,
        "train_rows": len(train),
        "test_rows": len(test),
        "split_time": test["timestamp"].min().isoformat(),
        "metrics": comparison_frame.to_dict(orient="records"),
        "audits": audits,
        "test_predictions": {
            "timestamp": [value.isoformat() for value in test["timestamp"]],
            "actual": test["sediment_kgm3"].tolist(),
            **{name: value.tolist() for name, value in predictions.items()},
        },
    }
    return featured, detail, {"seed": seed, "features": FEATURES}


def integrate_annual_flux(frame: pd.DataFrame) -> pd.DataFrame:
    """Trapezoidal integration on the irregular observation grid."""
    data = frame.sort_values("timestamp").copy()
    dt = data["timestamp"].diff().dt.total_seconds().shift(-1)
    # Gaps above 48 h are not silently bridged; cap and expose the affected count.
    data["interval_seconds"] = dt.clip(lower=0, upper=48 * 3600)
    q_next = data["discharge_m3s"].shift(-1)
    c_next = data["sediment_filled_kgm3"].shift(-1)
    q_avg = (data["discharge_m3s"] + q_next) / 2
    load_avg = (
        data["discharge_m3s"] * data["sediment_filled_kgm3"] + q_next * c_next
    ) / 2
    data["water_m3"] = q_avg * data["interval_seconds"]
    data["sediment_kg"] = load_avg * data["interval_seconds"]
    data["year"] = data["timestamp"].dt.year
    annual = (
        data.groupby("year", as_index=False)
        .agg(
            water_1e8_m3=("water_m3", lambda values: values.sum() / 1e8),
            sediment_1e8_t=("sediment_kg", lambda values: values.sum() / 1e11),
            observations=("timestamp", "size"),
            measured_sediment=("sediment_kgm3", "count"),
            intervals_capped_48h=("interval_seconds", lambda values: int((values == 172800).sum())),
        )
        .round(6)
    )
    return annual


def monthly_series(frame: pd.DataFrame) -> pd.DataFrame:
    monthly = (
        frame.set_index("timestamp")
        .resample("MS")
        .agg(
            water_level_m=("water_level_m", "mean"),
            discharge_m3s=("discharge_m3s", "mean"),
            sediment_kgm3=("sediment_filled_kgm3", "mean"),
            observed_sediment=("sediment_kgm3", "count"),
        )
        .reset_index()
    )
    return monthly


def seasonal_naive_backtest(
    monthly: pd.DataFrame, column: str
) -> tuple[dict[str, float], np.ndarray]:
    values = monthly[column].to_numpy(dtype=float)
    if len(values) < 24:
        raise ValueError("At least 24 monthly observations are required")
    actual = values[-12:]
    prediction = values[-24:-12]
    return regression_metrics(actual, prediction), prediction


def damped_trend_seasonal_backtest(
    monthly: pd.DataFrame, column: str, damping: float = 0.9
) -> tuple[dict[str, float], np.ndarray]:
    """Transparent trend + monthly seasonal index; no hidden future covariates."""
    train = monthly.iloc[:-12]
    actual = monthly[column].iloc[-12:].to_numpy(dtype=float)
    y = train[column].to_numpy(dtype=float)
    t = np.arange(len(y), dtype=float)
    slope, intercept = np.polyfit(t, y, 1)
    trend = intercept + slope * t
    detrended = y - trend
    months = train["timestamp"].dt.month.to_numpy()
    seasonal = {
        month: float(np.nanmean(detrended[months == month])) for month in range(1, 13)
    }
    horizon = np.arange(1, 13)
    damped_increase = slope * np.cumsum(damping**horizon)
    prediction = (intercept + slope * (len(y) - 1)) + damped_increase
    prediction += np.array([seasonal[month] for month in monthly.iloc[-12:]["timestamp"].dt.month])
    prediction = np.maximum(prediction, 0)
    return regression_metrics(actual, prediction), prediction


def forecast_24_months(monthly: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    future_dates = pd.date_range(monthly["timestamp"].max() + pd.offsets.MonthBegin(), periods=24)
    output = pd.DataFrame({"timestamp": future_dates})
    comparisons: list[dict[str, Any]] = []
    for column in ("discharge_m3s", "sediment_kgm3"):
        seasonal_metrics, _ = seasonal_naive_backtest(monthly, column)
        trend_metrics, _ = damped_trend_seasonal_backtest(monthly, column)
        comparisons.extend(
            [
                {"target": column, "model": "seasonal_naive", **seasonal_metrics},
                {"target": column, "model": "damped_trend_seasonal", **trend_metrics},
            ]
        )
        best = min(
            [("seasonal_naive", seasonal_metrics), ("damped_trend_seasonal", trend_metrics)],
            key=lambda item: item[1]["rmse"],
        )[0]
        if best == "seasonal_naive":
            prediction = np.resize(monthly[column].iloc[-12:].to_numpy(), 24)
        else:
            y = monthly[column].to_numpy(dtype=float)
            t = np.arange(len(y), dtype=float)
            slope, intercept = np.polyfit(t, y, 1)
            residual = y - (intercept + slope * t)
            month_values = monthly["timestamp"].dt.month.to_numpy()
            seasonal = {
                month: float(np.mean(residual[month_values == month])) for month in range(1, 13)
            }
            horizon = np.arange(1, 25)
            trend = y[-1] + slope * np.cumsum(0.9**horizon)
            prediction = trend + np.array([seasonal[d.month] for d in future_dates])
        output[column] = np.maximum(prediction, 0)
        output[f"{column}_model"] = best
    return output, comparisons


def change_and_periodicity(monthly: pd.DataFrame) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for column in ("discharge_m3s", "sediment_kgm3"):
        values = monthly[column].interpolate().to_numpy(dtype=float)
        standardized = (values - values.mean()) / (values.std() or 1)
        cusum = np.cumsum(standardized)
        candidates = np.argsort(np.abs(np.diff(cusum)))[-5:]
        spectrum = np.abs(np.fft.rfft(standardized - standardized.mean()))
        frequencies = np.fft.rfftfreq(len(standardized), d=1)
        peaks, _ = find_peaks(spectrum[1:])
        ranked = sorted(
            peaks + 1, key=lambda index: spectrum[index], reverse=True
        )[:3]
        result[column] = {
            "candidate_change_months": [
                monthly.iloc[int(index) + 1]["timestamp"].strftime("%Y-%m")
                for index in sorted(candidates)
            ],
            "dominant_period_months": [
                round(float(1 / frequencies[index]), 2)
                for index in ranked
                if frequencies[index] > 0
            ],
            "seasonal_month_means": (
                monthly.assign(month=monthly["timestamp"].dt.month)
                .groupby("month")[column]
                .mean()
                .round(6)
                .to_dict()
            ),
        }
    result["note"] = (
        "候选突变点由标准化月序列的 CUSUM 局部变化排序得到，属于筛查结果，"
        "不得直接解释为因果事件。"
    )
    return result


def sampling_plan(forecast: pd.DataFrame) -> pd.DataFrame:
    """Select one high-information day in every future month."""
    scored = forecast.copy()
    discharge_change = scored["discharge_m3s"].pct_change().abs().fillna(0)
    sediment_change = scored["sediment_kgm3"].pct_change().abs().fillna(0)
    score = discharge_change + sediment_change
    score = (score - score.min()) / ((score.max() - score.min()) or 1)
    scored["information_score"] = score
    scored["recommended_date"] = scored["timestamp"] + pd.to_timedelta(
        np.where(score >= score.quantile(0.75), 9, 14), unit="D"
    )
    scored["frequency"] = np.where(score >= score.quantile(0.75), "每周一次", "每月一次")
    scored["reason"] = np.where(
        score >= score.quantile(0.75), "预测变化较快，加密采样", "变化平稳，保留月度哨点"
    )
    return scored[["recommended_date", "frequency", "information_score", "reason"]]


def cross_section_summary(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path, header=None)
    records = []
    for index in range(0, raw.shape[1], 2):
        date = pd.to_datetime(raw.iloc[0, index], errors="coerce")
        distance = pd.to_numeric(raw.iloc[2:, index], errors="coerce")
        elevation = pd.to_numeric(raw.iloc[2:, index + 1], errors="coerce")
        valid = distance.notna() & elevation.notna()
        if not valid.any() or pd.isna(date):
            continue
        x, z = distance[valid].to_numpy(), elevation[valid].to_numpy()
        order = np.argsort(x)
        x, z = x[order], z[order]
        width = float(x.max() - x.min())
        reference = float(z.max())
        area = float(np.trapezoid(reference - z, x))
        records.append(
            {
                "date": date,
                "points": len(x),
                "width_m": width,
                "mean_bed_elevation_m": float(np.trapezoid(z, x) / width),
                "section_area_below_local_max_m2": area,
            }
        )
    result = pd.DataFrame(records).sort_values("date")
    result["mean_bed_change_m"] = result["mean_bed_elevation_m"].diff()
    return result


def run_case(raw_root: Path, output_dir: Path, seed: int = 42) -> dict[str, Any]:
    attachments = locate_attachments(raw_root)
    monitoring, quality = load_monitoring(attachments["附件1.xlsx"])
    modeled, model_detail, config = train_sediment_models(monitoring, seed=seed)
    annual = integrate_annual_flux(modeled)
    monthly = monthly_series(modeled)
    forecast, forecast_comparison = forecast_24_months(monthly)
    cross_section = cross_section_summary(attachments["附件2.xlsx"])
    plan = sampling_plan(forecast)
    output_dir.mkdir(parents=True, exist_ok=True)
    annual.to_csv(output_dir / "annual_flux.csv", index=False)
    monthly.to_csv(output_dir / "monthly_series.csv", index=False)
    forecast.to_csv(output_dir / "forecast_24_months.csv", index=False)
    cross_section.to_csv(output_dir / "cross_section_summary.csv", index=False)
    plan.to_csv(output_dir / "sampling_plan.csv", index=False)
    summary = {
        "case": "2023E",
        "source": "official",
        "quality": quality,
        "model": model_detail,
        "forecast_comparison": forecast_comparison,
        "patterns": change_and_periodicity(monthly),
        "configuration": config,
        "limitations": [
            "缺测含沙量由模型填补，年度输沙量因此包含模型不确定性。",
            "不规则时距采用梯形积分；超过48小时的间隔被截断，不跨长缺口外推。",
            "采样方案是信息增益启发式结果，不替代现场成本和安全约束。",
        ],
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    return summary
