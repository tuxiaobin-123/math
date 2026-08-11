import numpy as np
import pandas as pd

from cumcm_lens.cases.yellow_river import forecast_24_months


def _monthly_frame() -> pd.DataFrame:
    dates = pd.date_range("2016-01-01", periods=72, freq="MS")
    trend = np.arange(72, dtype=float) * 0.25
    seasonal = np.tile(np.arange(12, dtype=float), 6)
    return pd.DataFrame(
        {
            "timestamp": dates,
            "discharge_m3s": 100 + trend + seasonal,
            "sediment_kgm3": 5 + trend * 0.02 + seasonal * 0.1,
        }
    )


def test_forecast_covers_twenty_four_distinct_months() -> None:
    forecast, _ = forecast_24_months(_monthly_frame())
    assert len(forecast) == 24
    assert forecast["timestamp"].dt.to_period("M").nunique() == 24
    assert forecast["timestamp"].iloc[-1] - forecast["timestamp"].iloc[0] > pd.Timedelta(days=650)


def test_damped_forecast_does_not_carry_last_month_residual() -> None:
    frame = _monthly_frame()
    frame.loc[frame.index[-1], "discharge_m3s"] += 1000
    forecast, _ = forecast_24_months(frame)
    assert forecast["discharge_m3s"].max() < frame["discharge_m3s"].iloc[-1]
