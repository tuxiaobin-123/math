# CUMCM Lens V5

全国大学生数学建模赛题知识图谱、真实题复现、可审计训练与开放 Benchmark 平台。

> 核心原则：官方事实、仓库可复算结果、结构化建议必须分开。模型更复杂不等于结论更可信。

## 直接使用

- [V5 交互训练平台](https://tuxiaobin-123.github.io/math/)
- [76 页严谨训练手册](docs/downloads/CUMCM_Lens_V5_严谨训练手册.pdf)
- [38 页训练作业册](docs/downloads/CUMCM_Lens_V5_训练作业册.pdf)
- 三道完整论文：[2023E](docs/downloads/2023E_yellow_river.pdf) · [2016A](docs/downloads/2016A_mooring.pdf) · [2024C](docs/downloads/2024C_crop_planning.pdf)

GitHub Pages 需要将 `main /docs` 设为发布源；在 V5 PR 合并前，上述线上入口不会更新。

## V5 包含什么

| 能力 | 已实现 |
|---|---|
| V2 训练系统 | 36 项任务、产出、评分、12 周路线、48 小时作战、76 页手册与 38 页作业册 |
| V3 交互平台 | 五维诊断、进度持久化、知识图谱、模型实验室、团队看板、作品集导出 |
| V4 AI 教练 | 本地确定性规则：时序泄漏、缺失基线、未经证明的最优、因果越界、缺少来源 |
| V5 开放生态 | Benchmark 注册表、提交 Schema、SHA-256 认证、复现徽章、贡献规范、本地 API |

AI 教练的评分用于训练诊断，不代表专家、评委或官方意见。V5 没有伪造真实用户、社区贡献、专家认证或官方背书。

## 三道代表题

| 真题 | 核心能力 | 当前可复算结果 | 边界 |
|---|---|---|---|
| 2023E 黄河水沙 | 清洗、时序、通量、变点与预测 | 最佳含沙模型测试 RMSE 6.511 kg/m³、R² 0.325 | 含沙缺失率 87.13%，不包装成高精度预测 |
| 2016A 系泊系统 | 静力、悬链线、数值求解与设计 | I 型 36 m、5000 kg 候选，四类约束通过 | 不含波浪、疲劳和锚土耦合，非工程认证 |
| 2024C 种植规划 | MILP、情景与鲁棒优化 | 三情景均 0 项硬约束违反 | MIP gap 9.18% / 3.01% / 2.44%，不称全局最优 |

## V2 真实性修复

V1 审查发现的三个问题已修复并加入回归测试：

1. `pd.date_range` 现在显式使用月初频率，结果覆盖 2022-01 至 2023-12 共 24 个唯一月份，不再把 24 天误写为 24 个月。
2. 阻尼趋势从拟合趋势终点出发，不再把最后观测的季节残差重复带入未来。
3. 截面积分使用 `np.trapz`，与声明支持的 NumPy 1.26 兼容。

## 快速开始

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,notebook,report]"
npm install

# 数据：下载官方压缩包、校验并提取
python scripts/download_official_data.py
python scripts/prepare_official_data.py

# 三题实验与图表
cumcm-lens run-all

# 测试（当前仓库提供无额外依赖的 runner）
make test

# 重建论文、手册与 Pages 下载文件
make reports

# 交互网页
python -m http.server 8000 -d docs
```

打开 <http://127.0.0.1:8000>。

## 本地 API

不需要 API 也能使用静态网页。需要和自动化工具连接时：

```bash
cumcm-lens-api --port 8765
```

接口：

- `GET /api/v1/health`
- `GET /api/v1/problems`
- `POST /api/v1/diagnose`
- `POST /api/v1/recommend-models`
- `POST /api/v1/coach`

规范见 [OpenAPI](docs/openapi.json)。API 默认只监听 `127.0.0.1`，不包含账号、云数据库或多人权限系统。

## 复现认证

```bash
cumcm-lens certify benchmark/example_submission.json \
  --output artifacts/certificate.json
```

认证检查必填字段、仓库内文件、SHA-256 和时序切分。它是仓库级审计，不代表 CUMCM 官方认证。

## 验证结果

- Python：21 项测试全部通过。
- Web：11 个模块、诊断、训练持久化、AI 教练、知识图谱、Benchmark、团队看板、作品集、PDF 下载和 OpenAPI 均通过真实 DOM 执行测试。
- PDF：76 页手册、38 页作业册和 3 篇 17 页论文；Noto Sans SC 已嵌入并完成全页渲染检查。
- JavaScript：`node --check docs/data.js docs/app.js` 通过，无资源或运行错误。

## 证据分级

- **A：官方事实**——CUMCM 官方题面、附件或官方页面。
- **R：仓库可复算结果**——代码从 A 层资料生成，保留配置、种子、环境、耗时和校验值。
- **C：结构化建议**——模型选择、解释与改进方向，必须注明假设。

原始官方压缩包不入库；固定下载地址、SHA-256 与提取流程位于 [data/raw/README.md](data/raw/README.md)。

## 结构

```text
src/cumcm_lens/       三题实现、基准实验室、诊断、AI 教练、本地 API
benchmark/            Benchmark 注册表、提交 Schema 与示例
data/                 数据字典、来源规则和可公开派生结果
notebooks/            三道真题可复现 Notebook
reports/              三篇论文源文件与图表
output/pdf/           论文、训练手册和作业册
docs/                 GitHub Pages 单页应用与可下载成品
content/              12 周路线、团队训练、内容资产与版本记录
scripts/              数据、实验、PDF、网站验证和发布辅助脚本
tests/                指标、泄漏、方程、约束、PDF 与 V5 功能测试
```

## 官方来源

- [CUMCM 历年赛题](https://www.mcm.edu.cn/html_cn/block/8579f5fce999cdc896f78bca5d4f8237.html)
- [2016 年赛题](https://www.mcm.edu.cn/html_cn/node/6d026d84bd785435f92e3079b4a87a2b.html)
- [2023 年赛题](https://www.mcm.edu.cn/html_cn/node/c74d72127066f510a5723a94b5323a26.html)
- [2024 年赛题](https://www.mcm.edu.cn/html_cn/node/a0c1fb5c31d43551f08cd8ad16870444.html)
- [中国大学生在线赛题讲评](https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmstjp/)

贡献前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。项目采用 MIT License；字体许可见 [OFL.txt](assets/fonts/OFL.txt)。
