# 模型基准实验室

`BenchmarkLab` 负责把“跑模型”变成可重复实验，而不是散落脚本。

```python
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from cumcm_lens.core.benchmark import BenchmarkLab

lab = BenchmarkLab("artifacts/runs/demo", seed=42)
leaderboard = lab.run(
    case="demo",
    task="regression",
    models={
        "ridge": Ridge(alpha=1.0),
        "random_forest": RandomForestRegressor(random_state=42),
    },
    x_train=X_train,
    y_train=y_train,
    x_test=X_test,
    y_test=y_test,
    target_name="target",
    train_time=train_time,
    test_time=test_time,
)
```

每次实验自动保存：

- MAE、RMSE、R²，或 accuracy、F1、AUC；
- 估计器全部参数、随机种子、运行时间；
- 测试集真实值、预测值和分类分数；
- 回归残差图；
- 目标泄漏和时间切分审计；
- 业务约束检查器返回的逐项结果；
- 同一任务的模型排行榜。

三道真题还在此通用层之外增加各自审计：2023E检查长时距积分和时间泄漏，2016A检查角度/吃水/方程残差，2024C检查地块容量、轮作、豆类窗口、适种性和MIP gap。

一键论文图表：

```bash
cumcm-lens paper-figures
python scripts/build_reports.py
```
