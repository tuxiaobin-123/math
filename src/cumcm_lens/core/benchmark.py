"""Unified multi-model benchmark laboratory for regression and classification."""

from __future__ import annotations

import json
import os
import random
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Literal

os.environ.setdefault("MPLCONFIGDIR", "/tmp/cumcm-lens-matplotlib")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from cumcm_lens.core.audit import chronological_split_audit, feature_target_overlap_audit
from cumcm_lens.core.metrics import classification_metrics, regression_metrics

Task = Literal["regression", "classification"]
ConstraintChecker = Callable[[np.ndarray], list[dict[str, Any]]]


class BenchmarkLab:
    """Run comparable estimators with stable seeds, metrics and artifacts."""

    def __init__(self, output_dir: str | Path, seed: int = 42):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.seed = seed

    def run(
        self,
        *,
        case: str,
        task: Task,
        models: Mapping[str, Any],
        x_train: pd.DataFrame,
        y_train: np.ndarray | pd.Series,
        x_test: pd.DataFrame,
        y_test: np.ndarray | pd.Series,
        target_name: str,
        train_time: pd.Series | None = None,
        test_time: pd.Series | None = None,
        constraint_checker: ConstraintChecker | None = None,
    ) -> pd.DataFrame:
        random.seed(self.seed)
        np.random.seed(self.seed)
        result_rows = []
        common_audits = [feature_target_overlap_audit(x_train.columns, target_name).to_dict()]
        if train_time is not None and test_time is not None:
            common_audits.append(
                chronological_split_audit(train_time, test_time).to_dict()
            )
        for name, estimator in models.items():
            started = time.perf_counter()
            estimator.fit(x_train, y_train)
            prediction = np.asarray(estimator.predict(x_test))
            runtime = time.perf_counter() - started
            if task == "regression":
                metrics = regression_metrics(np.asarray(y_test), prediction)
                score = None
            else:
                score = self._classification_score(estimator, x_test)
                metrics = classification_metrics(np.asarray(y_test), prediction, score)
            audits = [*common_audits]
            if constraint_checker:
                audits.extend(constraint_checker(prediction))
            parameters = self._safe_parameters(estimator)
            detail = {
                "case": case,
                "task": task,
                "model": name,
                "seed": self.seed,
                "runtime_seconds": runtime,
                "metrics": metrics,
                "parameters": parameters,
                "audits": audits,
            }
            (self.output_dir / f"{case}__{name}.json").write_text(
                json.dumps(detail, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
            prediction_frame = pd.DataFrame(
                {"actual": np.asarray(y_test), "prediction": prediction}
            )
            if score is not None:
                prediction_frame["score"] = score
            prediction_frame.to_csv(
                self.output_dir / f"{case}__{name}__predictions.csv", index=False
            )
            if task == "regression":
                self._residual_figure(case, name, prediction_frame)
            result_rows.append(
                {
                    "case": case,
                    "task": task,
                    "model": name,
                    **metrics,
                    "runtime_seconds": runtime,
                    "audit_passed": all(bool(item["passed"]) for item in audits),
                }
            )
        results = pd.DataFrame(result_rows)
        results.to_csv(self.output_dir / f"{case}__leaderboard.csv", index=False)
        return results

    @staticmethod
    def _classification_score(estimator: Any, x_test: pd.DataFrame) -> np.ndarray | None:
        if hasattr(estimator, "predict_proba"):
            probability = np.asarray(estimator.predict_proba(x_test))
            return probability[:, 1] if probability.ndim == 2 and probability.shape[1] == 2 else None
        if hasattr(estimator, "decision_function"):
            score = np.asarray(estimator.decision_function(x_test))
            return score if score.ndim == 1 else None
        return None

    @staticmethod
    def _safe_parameters(estimator: Any) -> dict[str, Any]:
        if not hasattr(estimator, "get_params"):
            return {}
        result = {}
        for key, value in estimator.get_params(deep=True).items():
            if isinstance(value, (str, int, float, bool, type(None))):
                result[key] = value
            else:
                result[key] = repr(value)
        return result

    def _residual_figure(self, case: str, name: str, frame: pd.DataFrame) -> None:
        residual = frame["actual"] - frame["prediction"]
        fig, axes = plt.subplots(1, 2, figsize=(9, 3.5))
        axes[0].scatter(frame["prediction"], frame["actual"], s=10, alpha=0.6)
        low = min(frame["actual"].min(), frame["prediction"].min())
        high = max(frame["actual"].max(), frame["prediction"].max())
        axes[0].plot([low, high], [low, high], "--", color="#d55e00")
        axes[0].set(xlabel="Prediction", ylabel="Actual")
        axes[1].scatter(frame["prediction"], residual, s=10, alpha=0.6)
        axes[1].axhline(0, ls="--", color="#d55e00")
        axes[1].set(xlabel="Prediction", ylabel="Residual")
        fig.tight_layout()
        fig.savefig(
            self.output_dir / f"{case}__{name}__residuals.png",
            dpi=160,
            bbox_inches="tight",
        )
        plt.close(fig)
