import numpy as np
import pandas as pd

from cumcm_lens.core.audit import (
    chronological_split_audit,
    feature_target_overlap_audit,
    numeric_constraint,
)
from cumcm_lens.core.metrics import classification_metrics, regression_metrics


def test_regression_metrics_are_exact() -> None:
    result = regression_metrics(np.array([0, 1, 2]), np.array([0, 2, 1]))
    assert result["mae"] == 2 / 3
    assert np.isclose(result["rmse"], np.sqrt(2 / 3))


def test_classification_metrics_include_auc() -> None:
    result = classification_metrics(
        np.array([0, 0, 1, 1]),
        np.array([0, 0, 1, 1]),
        np.array([0.1, 0.2, 0.8, 0.9]),
    )
    assert result["f1"] == 1
    assert result["auc"] == 1


def test_leakage_audits() -> None:
    finding = chronological_split_audit(
        pd.date_range("2020-01-01", periods=3),
        pd.date_range("2020-02-01", periods=2),
    )
    assert finding.passed
    assert feature_target_overlap_audit(["x1", "x2"], "target").passed
    assert not feature_target_overlap_audit(["x1", "target"], "target").passed


def test_numeric_constraint_has_tolerance() -> None:
    assert numeric_constraint("angle", 5.0 + 1e-10, upper=5.0).passed
    assert not numeric_constraint("angle", 5.1, upper=5.0).passed
