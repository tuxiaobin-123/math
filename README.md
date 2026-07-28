# CUMCM Lens

全国大学生数学建模赛题知识图谱、真题复现与 AI 辅助训练平台。

> 目标不是“给题目贴模型标签”，而是建立一条可审计的证据链：官方题面与附件 → 数据字典 → 基线模型 → 模型对比 → 误差/约束审计 → 敏感性分析 → Notebook → 论文 → 可视化网页。

## 已实现的三道代表题

| 真题 | 核心能力 | 当前实现 |
|---|---|---|
| 2023E 黄河水沙监测 | 数据清洗、时序、相关、突变、预测、采样优化 | 真实附件流水线、双模型比较、年度水沙通量、月度规律、预测与采样建议 |
| 2016A 系泊系统设计 | 静力学、悬链线、数值求解、多目标设计 | 解析悬链线与数值积分对照、约束审计、重物球/锚链鲁棒搜索 |
| 2024C 农作物种植策略 | 整数规划、情景分析、鲁棒优化 | 真实附件解析、重复2023基线、MILP、风险调整MILP、轮作/豆类/容量约束审计 |

## 当前可复算结果

| 真题 | 核心结果 | 严谨性说明 |
|---|---|---|
| 2023E | 最佳含沙模型测试 RMSE 6.511 kg/m³、R² 0.325 | 严格时间外推；缺失率87.13%，不把结果包装成高精度预测 |
| 2016A | 鲁棒候选：I型36 m、重物球5000 kg | 报告极端场景桶倾4.786°、锚角15.041°，四项审计通过；仅为静力模型候选 |
| 2024C | 三种情景均得到0项硬约束违反的整数可行解 | 如实报告MIP gap 9.18%、3.01%、2.44%；不宣称限时解全局最优 |

这些数字来自当前代码和已校验官方附件。重新运行可能因依赖版本或求解器路径产生细微差异，运行元数据会保留实际版本与耗时。

## 仓库结构

```text
src/cumcm_lens/        模型基准实验室与三道题实现
notebooks/             可复现 Notebook
reports/               三篇研究报告与方法说明
output/pdf/            三篇17页完整论文（已嵌入中文字体）
docs/                  静态交互网页（GitHub Pages）
data/dictionaries/     官方附件数据字典
data/processed/        可公开的聚合/派生结果
scripts/               下载、校验、运行与生成脚本
tests/                 单元测试、数据泄漏与约束测试
content/               抖音/小红书选题与团队训练材料
```

## 直接查看交付物

- 交互结果页：[CUMCM Lens Dashboard](https://tuxiaobin-123.github.io/math/)（合并后需在仓库 Settings → Pages 选择 `main /docs`）
- 论文：[2023E](output/pdf/2023E_yellow_river.pdf) · [2016A](output/pdf/2016A_mooring.pdf) · [2024C](output/pdf/2024C_crop_planning.pdf)
- Notebook：[2023E](notebooks/2023E_yellow_river.ipynb) · [2016A](notebooks/2016A_mooring.ipynb) · [2024C](notebooks/2024C_crop_planning.ipynb)
- [模型基准实验室](docs/model-lab.md) · [12周学习路线](content/learning-roadmap.md) · [团队训练系统](content/team-training-system.md) · [内容选题](content/social-series.md)
- [赛题目录](knowledge/problem_catalog.csv) · [模型—任务映射](knowledge/model_task_map.csv)

## 快速开始

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,notebook,report]"

# 下载官方赛题包并校验 SHA-256
python scripts/download_official_data.py

# 从官方包提取三道题（RAR 需要 node-unrar-js）
npm install
python scripts/prepare_official_data.py

# 运行三道题和模型基准实验室
cumcm-lens run-all

# 执行测试
pytest

# 一键重建图表、Notebook和17页论文
cumcm-lens paper-figures
python scripts/build_notebooks.py
python scripts/build_reports.py

# 本地查看网页
python -m http.server 8000 -d docs
```

打开 <http://localhost:8000>。

## 真实性分级

- **A：官方事实**——来自 CUMCM 官网题面或官方附件。
- **B：可复算结果**——由仓库代码从官方附件计算得到，并保存配置、随机种子、运行时间和校验值。
- **C：结构化建议**——模型选择、解释或改进方向，必须注明假设，不能冒充官方答案。

仓库不提交体积较大的官方原始压缩包。下载地址、校验值和提取流程均保存在 `data/raw/README.md` 与脚本中。

三篇PDF嵌入 Noto Sans SC 字体子集，许可见 `assets/fonts/OFL.txt`。重建论文前，`scripts/prepare_report_font.py` 会从固定版本的 Fontsource 包下载 WOFF 并转换为本地 TTF；TTF 本身不重复提交。

## 官方来源

- [CUMCM 历年赛题](https://www.mcm.edu.cn/html_cn/block/8579f5fce999cdc896f78bca5d4f8237.html)
- [2016 年赛题](https://www.mcm.edu.cn/html_cn/node/6d026d84bd785435f92e3079b4a87a2b.html)
- [2023 年赛题](https://www.mcm.edu.cn/html_cn/node/c74d72127066f510a5723a94b5323a26.html)
- [2024 年赛题](https://www.mcm.edu.cn/html_cn/node/a0c1fb5c31d43551f08cd8ad16870444.html)
- [中国大学生在线赛题讲评](https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmstjp/)

## 重要边界

本项目是可复现研究与训练框架，不声称存在唯一“标准模型”。报告中的数值结果只能由对应版本的官方附件和代码生成；若原始附件缺失，系统会停止并给出明确错误，不会自动生成伪数据。
