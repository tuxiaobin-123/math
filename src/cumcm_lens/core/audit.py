"""Reusable leakage, data-quality and constraint audits."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class AuditFinding:
    name: str
    passed: bool
    severity: str
    observed: Any
    expected: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def chronological_split_audit(
    train_time: Iterable[Any], test_time: Iterable[Any]
) -> AuditFinding:
    train = pd.to_datetime(pd.Series(train_time)).dropna()
    test = pd.to_datetime(pd.Series(test_time)).dropna()
    passed = bool(len(train) and len(test) and train.max() < test.min())
    return AuditFinding(
        "chronological_split",
        passed,
        "error",
        {
            "train_max": str(train.max()) if len(train) else None,
            "test_min": str(test.min()) if len(test) else None,
        },
        "max(train_time) < min(test_time)",
    )


def feature_target_overlap_audit(features: Iterable[str], target: str) -> AuditFinding:
    feature_set = set(features)
    return AuditFinding(
        "target_not_in_features",
        target not in feature_set,
        "error",
        sorted(feature_set & {target}),
        f"{target!r} must not be a feature",
    )


def finite_values_audit(values: np.ndarray, name: str) -> AuditFinding:
    array = np.asarray(values, dtype=float)
    ratio = float(np.isfinite(array).mean()) if array.size else 0.0
    return AuditFinding(name, ratio == 1.0, "error", ratio, "all values finite")


def numeric_constraint(
    name: str,
    observed: float,
    *,
    upper: float | None = None,
    lower: float | None = None,
    tolerance: float = 1e-8,
    severity: str = "error",
) -> AuditFinding:
    passed = True
    terms = []
    if lower is not None:
        passed &= observed >= lower - tolerance
        terms.append(f">= {lower}")
    if upper is not None:
        passed &= observed <= upper + tolerance
        terms.append(f"<= {upper}")
    return AuditFinding(name, bool(passed), severity, float(observed), " and ".join(terms))
