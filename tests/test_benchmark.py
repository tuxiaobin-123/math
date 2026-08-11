import pandas as pd
from sklearn.datasets import make_classification, make_regression
from sklearn.linear_model import LinearRegression, LogisticRegression

from cumcm_lens.core.benchmark import BenchmarkLab


def test_regression_benchmark_writes_auditable_artifacts(tmp_path) -> None:
    x, y = make_regression(n_samples=80, n_features=3, noise=0.1, random_state=42)
    frame = pd.DataFrame(x, columns=["a", "b", "c"])
    lab = BenchmarkLab(tmp_path, seed=42)
    result = lab.run(
        case="regression",
        task="regression",
        models={"linear": LinearRegression()},
        x_train=frame.iloc[:60],
        y_train=y[:60],
        x_test=frame.iloc[60:],
        y_test=y[60:],
        target_name="target",
        train_time=pd.date_range("2020-01-01", periods=60),
        test_time=pd.date_range("2021-01-01", periods=20),
    )
    assert result.loc[0, "audit_passed"]
    assert (tmp_path / "regression__linear.json").exists()
    assert (tmp_path / "regression__linear__residuals.png").exists()


def test_classification_benchmark_computes_f1_and_auc(tmp_path) -> None:
    x, y = make_classification(n_samples=100, n_features=4, random_state=42)
    frame = pd.DataFrame(x, columns=list("abcd"))
    result = BenchmarkLab(tmp_path).run(
        case="classification",
        task="classification",
        models={"logistic": LogisticRegression(max_iter=500)},
        x_train=frame.iloc[:75],
        y_train=y[:75],
        x_test=frame.iloc[75:],
        y_test=y[75:],
        target_name="target",
    )
    assert 0 <= result.loc[0, "f1"] <= 1
    assert 0 <= result.loc[0, "auc"] <= 1
