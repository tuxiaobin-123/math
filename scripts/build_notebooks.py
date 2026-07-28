#!/usr/bin/env python3
"""Build the three source-controlled notebooks without requiring nbformat."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / "notebooks"


def markdown(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.splitlines(keepends=True),
    }


def notebook(cells: list[dict]) -> dict:
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.10"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


COMMON = """\
from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path.cwd().resolve()
while not (ROOT / "pyproject.toml").exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
assert (ROOT / "pyproject.toml").exists(), "请从仓库内运行 Notebook"
"""


YELLOW = notebook(
    [
        markdown(
            "# 2023E 黄河水沙监测：可复现实验\n\n"
            "证据等级：题面/附件字段为 A；代码复算结果为 B；解释和建议为 C。"
        ),
        code(COMMON),
        markdown("## 1. 原始附件校验与数据字典\n\n运行下载/提取脚本后读取官方附件，不创建模拟数据。"),
        code(
            """\
from cumcm_lens.cases.yellow_river import locate_attachments, load_monitoring
files = locate_attachments(ROOT / "data/raw")
monitoring, quality = load_monitoring(files["附件1.xlsx"])
quality
"""
        ),
        markdown("## 2. 缺失审计\n\n含沙量缺失不会被前向填充；只在时间外推测试后由最终模型补齐。"),
        code(
            """\
monitoring[["water_level_m", "discharge_m3s", "sediment_kgm3"]].isna().mean()
"""
        ),
        markdown("## 3. 三模型比较与泄漏检查"),
        code(
            """\
from cumcm_lens.cases.yellow_river import train_sediment_models
modeled, detail, config = train_sediment_models(monitoring, seed=42)
pd.DataFrame(detail["metrics"])
"""
        ),
        code("pd.DataFrame(detail['audits'])"),
        markdown("## 4. 年度水沙通量\n\n使用不规则时距梯形积分，超过48小时的长缺口不被直接跨越。"),
        code(
            """\
from cumcm_lens.cases.yellow_river import integrate_annual_flux
annual = integrate_annual_flux(modeled)
annual
"""
        ),
        markdown("## 5. 月尺度规律、回测与两年预测"),
        code(
            """\
from cumcm_lens.cases.yellow_river import monthly_series, forecast_24_months
monthly = monthly_series(modeled)
forecast, comparison = forecast_24_months(monthly)
pd.DataFrame(comparison)
"""
        ),
        code(
            """\
fig, axes = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
axes[0].plot(monthly["timestamp"], monthly["discharge_m3s"])
axes[1].plot(monthly["timestamp"], monthly["sediment_kgm3"])
plt.show()
"""
        ),
        markdown("## 6. 断面变化与采样计划"),
        code(
            """\
from cumcm_lens.cases.yellow_river import cross_section_summary, sampling_plan
display(cross_section_summary(files["附件2.xlsx"]))
display(sampling_plan(forecast))
"""
        ),
        markdown(
            "## 7. 结论边界\n\n测试期 R² 较低说明跨年份泛化有限。年度输沙量和未来预测必须连同误差、缺失率与模型假设一起引用。"
        ),
    ]
)

MOORING = notebook(
    [
        markdown("# 2016A 系泊系统：解析—数值双重复现"),
        code(COMMON),
        markdown("## 1. 官方参数\n\n本题无独立数据附件；参数逐项来自官方题面。"),
        code(
            """\
from cumcm_lens.cases.mooring import CHAIN_TYPES, MooringConfig
pd.DataFrame(CHAIN_TYPES).T
"""
        ),
        markdown("## 2. 基线场景"),
        code(
            """\
from cumcm_lens.cases.mooring import solve_state
states = [solve_state(MooringConfig(wind_ms=v)) for v in (12, 24, 36)]
pd.DataFrame([{k:v for k,v in state.items() if not isinstance(v,(list,dict))} for state in states])
"""
        ),
        markdown("## 3. 解析悬链线与数值积分复核"),
        code(
            """\
from cumcm_lens.cases.mooring import numerical_catenary_audit
pd.DataFrame([numerical_catenary_audit(state) for state in states])
"""
        ),
        markdown("## 4. 约束审计"),
        code("pd.DataFrame(states[-1]['audits'])"),
        markdown("## 5. 鲁棒离散设计搜索"),
        code(
            """\
from cumcm_lens.cases.mooring import design_grid
grid = design_grid()
grid.head(10)
"""
        ),
        markdown("## 6. 敏感性分析"),
        code(
            """\
from cumcm_lens.cases.mooring import sensitivity_table
best = grid[grid["feasible"]].iloc[0]
config = MooringConfig(depth_m=20, wind_ms=36, current_ms=1.5,
    chain_type=best.chain_type, chain_length_m=best.chain_length_m,
    ballast_mass_kg=best.ballast_mass_kg)
sensitivity = sensitivity_table(config)
for name, group in sensitivity.groupby("parameter"):
    plt.plot(group["factor"], group["barrel_angle_deg"], marker="o", label=name)
plt.axhline(5, linestyle="--"); plt.legend(); plt.show()
"""
        ),
        markdown(
            "## 7. 结论边界\n\n模型是稳态、同向风流的静力模型，未覆盖波浪、疲劳、锚土相互作用与制造公差；工程部署前必须进一步验证。"
        ),
    ]
)

CROP = notebook(
    [
        markdown("# 2024C 农作物种植策略：整数规划与情景审计"),
        code(COMMON),
        markdown("## 1. 官方附件读取"),
        code(
            """\
from cumcm_lens.cases.crop_planning import locate_attachments, load_official_data
files = locate_attachments(ROOT / "data/raw")
land, crops, planted, stats, demand, quality = load_official_data(
    files["附件1.xlsx"], files["附件2.xlsx"])
quality
"""
        ),
        markdown("## 2. 数据字典与销量口径"),
        code(
            """\
display(land.groupby("land_type").agg(plots=("plot","size"), area_mu=("area_mu","sum")))
display(demand.head(10))
"""
        ),
        markdown("## 3. 朴素基线及约束失败"),
        code(
            """\
from cumcm_lens.cases.crop_planning import repeated_2023_baseline
baseline, baseline_audit = repeated_2023_baseline(land, planted)
pd.DataFrame(baseline_audit)
"""
        ),
        markdown(
            "## 4. 三种整数规划\n\n为隔离 HiGHS 原生内存，每个情景由独立工作进程运行。"
        ),
        code(
            """\
from cumcm_lens.cases.crop_planning import run_case
summary = run_case(ROOT / "data/raw", ROOT / "data/processed/2024C")
pd.DataFrame([{k:v for k,v in item.items() if k not in {"audits"}}
              for item in summary["models"]])
"""
        ),
        markdown("## 5. 可行性与最优性审计"),
        code(
            """\
for item in summary["models"]:
    print(item["scenario"], "MIP gap =", item["mip_gap"])
    display(pd.DataFrame(item["audits"]))
"""
        ),
        markdown("## 6. 计划结果"),
        code(
            """\
schedule = pd.read_csv(ROOT / "data/processed/2024C/schedule_robust_worst_case.csv")
display(schedule.head(20))
display(schedule.groupby(["year", "crop_name"])["area_mu"].sum().reset_index().head(30))
"""
        ),
        markdown("## 7. 价格—产量敏感性"),
        code(
            """\
sensitivity = pd.read_csv(ROOT / "data/processed/2024C/sensitivity.csv")
sensitivity.groupby(["price_factor","yield_factor"])["uncapped_profit_yuan"].mean().unstack()
"""
        ),
        markdown(
            "## 8. 结论边界\n\n结果是完整地块单作假设下的经审计可行解；求解器达到时限时须报告 MIP gap，不得写成“已证明最优”。"
        ),
    ]
)


def main() -> None:
    NOTEBOOKS.mkdir(parents=True, exist_ok=True)
    for name, payload in {
        "2023E_yellow_river.ipynb": YELLOW,
        "2016A_mooring.ipynb": MOORING,
        "2024C_crop_planning.ipynb": CROP,
    }.items():
        (NOTEBOOKS / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        print(f"wrote notebooks/{name}")


if __name__ == "__main__":
    main()
