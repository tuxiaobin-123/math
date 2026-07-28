#!/usr/bin/env python3
"""Build three 15–20 page Chinese PDF papers from persisted experiment results."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
PDF_OUTPUT = ROOT / "output" / "pdf"
PROCESSED = ROOT / "data" / "processed"
FIGURES = REPORTS / "figures"
FONT_PATH = ROOT / "assets" / "fonts" / "NotoSansSC-Regular.ttf"
FONT_NAME = "NotoSansSC"


@dataclass
class Page:
    title: str
    paragraphs: list[str]
    bullets: list[str] | None = None
    table: list[list[str]] | None = None
    image: str | None = None


def fmt(value: float, digits: int = 3) -> str:
    return f"{value:,.{digits}f}"


def yellow_pages() -> list[Page]:
    summary = json.loads((PROCESSED / "2023E" / "summary.json").read_text(encoding="utf-8"))
    annual = pd.read_csv(PROCESSED / "2023E" / "annual_flux.csv")
    metrics = summary["model"]["metrics"]
    best = summary["model"]["best_model"]
    metric_rows = [
        [item["model"], fmt(item["mae"]), fmt(item["rmse"]), fmt(item["r2"])]
        for item in metrics
    ]
    annual_rows = [
        [
            str(int(row.year)),
            fmt(row.water_1e8_m3),
            fmt(row.sediment_1e8_t, 5),
            str(int(row.measured_sediment)),
        ]
        for row in annual.itertuples()
    ]
    return [
        Page(
            "2023E 黄河水沙监测数据分析",
            [
                "基于官方附件的缺失审计、时间外推检验、通量积分、突变周期筛查、两年预测与采样设计",
                "CUMCM Lens 真题深度复现报告 · 证据版本 v1.0",
                "本文所有事实字段来自官方题面/附件；数值结果由仓库代码复算；解释性结论均标注假设和限制。",
            ],
        ),
        Page(
            "摘要",
            [
                f"本文处理2016—2021年黄河某水文站{summary['quality']['clean_rows']:,}个唯一时点。含沙量仅有{summary['quality']['sediment_observed_rows']:,}个实测值，缺失率为{summary['quality']['sediment_missing_rate']:.2%}，因此研究重点首先是缺失机制与时间外推误差，而不是追求训练集拟合。",
                f"按时间前80%训练、后20%测试，比较对数岭回归、随机森林与直方图梯度提升。测试RMSE最低的模型为{best}。随后以实测优先、模型仅补缺的口径进行不规则时距梯形积分，并对月序列进行季节朴素与阻尼趋势季节模型回测。",
                "结果表明跨年份泛化有限，未来两年预测只适合作为方案比较基线。本文进一步给出断面概览、候选突变月份、主周期筛查和按变化强度加密的采样建议，并对所有非因果、非现场约束作出明确声明。",
            ],
            bullets=["关键词：水沙关系", "缺失数据", "时间外推", "通量积分", "采样优化"],
        ),
        Page(
            "1 问题重述与研究目标",
            [
                "题目要求从历年水位、流量、含沙量和断面测量中分析水沙关系，估计年度水沙总量，识别突变、季节和周期，预测未来两年，并讨论采样频次及调水调沙对河床的作用。",
                "这些任务在统计口径上并不等价：相关关系需要控制季节和时间趋势；年度总量需要对不规则观测时距积分；未来预测必须使用严格的时间切分；河床变化需要处理不同日期横坐标网格不一致。",
                "本文将问题分为数据层、预测层、积分层、模式筛查层和决策层。每一层单独保存输入、参数、结果与审计项，避免一处插值假设被无声传播到全部结论。",
            ],
        ),
        Page(
            "2 数据来源、字段与质量",
            [
                "附件1包含2016—2021六个工作表，字段为年月日、时间、水位、流量和含沙量；附件2按日期成对给出起点距离与河底高程；附件3给出垂线测点的水深、流速和含沙量。",
                "合并单元格造成的年月日空值只用于恢复日期，含沙量空值不做前向填充。5个重复时间戳按同一时点均值折叠。水位或流量无效的记录不进入模型，但清洗前后行数均写入质量摘要。",
                "附件3的2023年测量不进入2016—2021时间外推实验，从源头防止未来信息泄漏。断面横坐标不一致时，本版只报告各次断面自身的积分概览，不直接计算未经共同网格插值的点差。",
            ],
            table=[
                ["指标", "核验值"],
                ["原始记录", f"{summary['quality']['raw_rows']:,}"],
                ["唯一时点", f"{summary['quality']['clean_rows']:,}"],
                ["含沙量实测", f"{summary['quality']['sediment_observed_rows']:,}"],
                ["含沙缺失率", f"{summary['quality']['sediment_missing_rate']:.2%}"],
            ],
        ),
        Page(
            "3 模型假设与符号",
            [
                "假设监测记录的水位、流量在各自时点代表瞬时状态；相邻有效时点之间的通量采用线性变化近似。超过48小时的长间隔被截断，不跨越长缺口直接外推。",
                "设Q(t)为流量，C(t)为含沙量，瞬时输沙率为Q(t)C(t)。年度水量为Q对时间的积分，年度沙量为QC对时间的积分。含沙缺失时使用经时间外推检验后、在全部实测值上重训的最佳模型预测。",
                "预测特征仅含当前水位、流量、距起点天数、年内日和时刻的正余弦项，不含目标的未来值、滚动未来统计或随机切分编码。",
            ],
            table=[
                ["符号", "含义", "单位"],
                ["Q(t)", "流量", "m³/s"],
                ["C(t)", "含沙量", "kg/m³"],
                ["Δt", "相邻记录时距", "s"],
                ["W", "年度水量", "m³"],
                ["M", "年度输沙质量", "kg"],
            ],
        ),
        Page(
            "4 数据清洗与特征工程",
            [
                "清洗流水线逐表读取，统一列名、向下填充日期组成字段，将时刻字符串解析为小时分钟，再组合为完整时间戳。数值列使用显式数值转换，不能转换的值标记为缺失。",
                "周期特征使用年内日和小时的正余弦编码，避免把12月31日与1月1日误当作相距很远。趋势天数仅由时间戳计算，不使用含沙量本身。",
                "模型只在含沙量非空的行上训练。清洗结果先按时间排序，再以80%位置切分，训练集最大时间严格早于测试集最小时间；该条件由自动审计代码验证。",
            ],
        ),
        Page(
            "5 简单基线：对数岭回归",
            [
                "基线将含沙量做log(1+C)变换，连续特征标准化后采用L2正则线性回归。对数变换保证反变换后通过截断获得非负预测，并降低极端高含沙值对平方损失的支配。",
                "该模型参数少、运行快、方向可解释，适合作为最低比较线。它不能充分表示流量与含沙量的阈值关系、滞后效应和跨年份机制变化。",
                f"真实测试集上基线MAE={fmt(next(x for x in metrics if x['model']=='ridge_log')['mae'])} kg/m³，RMSE={fmt(next(x for x in metrics if x['model']=='ridge_log')['rmse'])} kg/m³。负R²意味着它在测试期甚至弱于测试均值基准，应据实保留。",
            ],
        ),
        Page(
            "6 非线性模型",
            [
                "比较模型一为随机森林，对变量尺度不敏感，可表示非线性交互；设置固定随机种子、240棵树和最小叶节点样本数4。比较模型二为直方图梯度提升，以较浅叶节点和较低学习率控制过拟合。",
                "三种模型使用完全相同的训练/测试时点和特征。模型选择只依据测试RMSE的相对比较；此测试集兼具最终报告功能，因此数值仍可能存在选择偏差，下一版应增加滚动嵌套验证。",
                f"本次最佳模型为{best}。模型被选定后才在全部实测含沙样本上重训，用于补齐通量积分所需时点；测试误差仍保留原外推结果，不以重训结果覆盖。",
            ],
        ),
        Page(
            "7 模型对比与残差审计",
            [
                "表中MAE反映典型绝对偏差，RMSE对高含沙误差更敏感，R²衡量相对于测试均值的解释能力。三个指标必须结合，不能只选择数值看起来最好的一项。",
                "残差图显示误差随预测水平扩张，高含沙事件更难刻画；这与87%以上含沙缺失、跨年分布变化相一致。模型用于补缺时应在通量结果外再给出不确定性区间。",
                "自动审计同时检查时间切分、目标字段未进入特征及全体预测为有限值。三个审计均通过，但它们不能排除未观测混杂或采样机制偏差。",
            ],
            table=[["模型", "MAE", "RMSE", "R²"], *metric_rows],
            image="2023E_residual_audit.png",
        ),
        Page(
            "8 年度水量与输沙量估计",
            [
                "对相邻时点采用梯形积分：水量增量为(Qi+Qi+1)Δt/2；沙量增量为(QiCi+Qi+1Ci+1)Δt/2。结果分别换算为亿立方米和亿吨。",
                "含沙量有实测时绝不覆盖，只有缺失时才使用模型值。年度表同时报告实测含沙记录数和被截断的长间隔数，使读者能够判断某一年估计依赖模型的程度。",
                "这些数值是给定监测序列与补缺模型下的复算量，不应解释为水文部门发布的法定年鉴值；若用于决策，应通过站点质量控制和独立资料复核。",
            ],
            table=[["年份", "水量/亿m³", "沙量/亿t", "实测含沙数"], *annual_rows],
        ),
        Page(
            "9 月尺度季节、周期与突变筛查",
            [
                "小时级数据聚合为月均水位、流量和含沙量。季节性以历年同月均值描述；周期性对标准化月序列做离散傅里叶变换并报告能量最高的候选周期。",
                "突变候选由标准化序列的CUSUM局部变化排序得到。该方法只负责定位值得复查的月份，不提供因果证据，也不把候选点自动关联到调水调沙或极端天气。",
                "主周期会受仅六年样本长度、缺失补值和趋势泄漏影响。报告将其写作“候选周期”而非稳定自然周期；正式分析应增加变点显著性、频谱置信区间和外部事件对照。",
            ],
            image="2023E_monthly_series.png",
        ),
        Page(
            "10 未来两年预测与回测",
            [
                "建立季节朴素法与阻尼趋势—季节指数法。以前60个月训练、最后12个月回测；分别对月均流量和补缺后的月均含沙量计算MAE、RMSE与R²，再按RMSE选择未来24个月模型。",
                "两类模型的测试R²并不理想，表明仅凭六年历史的简单季节结构难以稳定外推。未来24个月结果应看作情景基线，不应给出虚假的高精度小数或无条件置信承诺。",
                "改进方向包括加入降雨、调度事件、上游来水、温度等外生变量，采用滚动起点评估，并对洪峰月份使用分位数或极值模型。",
            ],
            table=[
                ["目标", "模型", "MAE", "RMSE"],
                *[
                    [x["target"], x["model"], fmt(x["mae"]), fmt(x["rmse"])]
                    for x in summary["forecast_comparison"]
                ],
            ],
        ),
        Page(
            "11 断面与调水调沙讨论",
            [
                "附件2的各次断面测点网格不一致。本文对每次断面单独计算宽度、平均河底高程和相对局部最高点以下的截面积，并保留相邻测次均值变化。",
                "题目关注六月至七月的调水调沙效果，但附件断面日期不是每年严格成对的处理前后观测。仅凭这些断面不能排除季节、来水过程和测量网格变化的影响。",
                "因此本版只报告描述性变化，不将河床变化全部归因于调水调沙。若要做因果评价，需要明确处理窗口、对照断面、同期流量过程和差分中的差分或机理泥沙模型。",
            ],
        ),
        Page(
            "12 采样方案与决策规则",
            [
                "未来每个月保留一个哨点日期；当预测流量和含沙量的环比变化综合得分处于上四分位时，将该月标记为每周一次，其余月份保持每月一次。",
                "这个规则体现“变化快时加密、平稳时保底”，便于复算和讨论。它没有引入船期、安全、实验室容量、洪峰可达性等现场成本，因此不是最终优化排班。",
                "更完整的方案可把模型预测方差、断面覆盖、采样费用和漏检损失写成多目标整数规划，并通过历史重放评估在固定预算下的事件捕获率。",
            ],
        ),
        Page(
            "13 敏感性、不确定性与误差传播",
            [
                "含沙缺失率是年度输沙量不确定性的首要来源。模型残差在高值区放大，意味着简单使用点预测会低估极端事件对总沙量的贡献。",
                "应通过时间块自助法或分位数模型产生含沙预测分布，并把每个时点的分布通过积分传播到年度总量。对48小时截断阈值也应在24、48、72小时下重复计算。",
                "月预测可对趋势阻尼系数、训练窗口和季节长度做网格敏感性；采样计划可对加密阈值做预算曲线。v1保存了全部中间表，为这些扩展提供可追踪起点。",
            ],
        ),
        Page(
            "14 模型评价、局限与改进",
            [
                "优点是数据源真实、时间切分严格、实测优先、通量公式透明，并把突变筛查与因果判断分开。局限是缺少外生驱动变量、未建立完整不确定性区间、断面因果识别不足。",
                "测试R²偏低不是应被隐藏的问题，而是模型边界的核心证据。竞赛写作应解释为什么误差产生、哪些结论仍稳健、哪些只可作为趋势提示。",
                "下一版优先增加滚动回测、预测区间、附件3的断面垂线积分、跨日期共同网格，以及采样成本约束。所有改进仍须通过相同审计接口。",
            ],
        ),
        Page(
            "15 结论与复现说明",
            [
                "本文完成了官方附件清洗、三模型含沙预测、年度水沙通量、月尺度规律、两模型预测、断面概览和采样建议。最重要的结论是：数据缺失和跨年漂移显著限制预测精度。",
                "复现命令依次为官方数据下载、校验、提取和cumcm-lens run-2023e；Notebook逐单元复现，summary.json保存模型参数、切分时间、指标与审计结果。",
                "引用任何数值时应同时注明仓库版本、官方压缩包SHA-256和模型边界。本文不提供或暗示官方标准答案。",
            ],
            bullets=[
                "官方附件校验值见 data/raw/README.md",
                "字段口径见 data/dictionaries/2023E.md",
                "可复现 Notebook：notebooks/2023E_yellow_river.ipynb",
                "派生表：data/processed/2023E/",
            ],
        ),
    ]


def mooring_pages() -> list[Page]:
    summary = json.loads((PROCESSED / "2016A" / "summary.json").read_text(encoding="utf-8"))
    states = summary["problem_states"]
    robust = summary["robust_design"]
    rows = [
        [
            fmt(state["wind_ms"], 0),
            state["regime"],
            fmt(state["draft_m"]),
            fmt(state["barrel_angle_deg"]),
            fmt(state["anchor_angle_deg"]),
            fmt(state["excursion_radius_m"]),
        ]
        for state in states
    ]
    return [
        Page(
            "2016A 系泊系统的设计",
            [
                "静力平衡、解析悬链线、数值积分复核与鲁棒离散设计",
                "CUMCM Lens 真题深度复现报告 · 证据版本 v1.0",
                "题面参数与模型假设分层记录；所有角度约束均由程序逐项审计。",
            ],
        ),
        Page(
            "摘要",
            [
                "本文把浮标—钢管—钢桶—重物球—锚链系统分解为浮力平衡、水平环境载荷、竖向张力递推和悬链线几何四部分，分别求解锚链接地与全悬浮状态。",
                "悬链线同时使用闭式公式和数值积分计算水平跨度与垂直升高，以绝对误差复核解析实现。对题1给定II型22.05 m锚链、1200 kg重物球和12/24/36 m/s风速计算状态。",
                f"面向水深16—20 m、风速36 m/s和流速1.5 m/s的离散场景搜索，得到当前目标函数下的候选：{robust['chain_type']}型、{robust['chain_length_m']:.1f} m、重物球{robust['ballast_mass_kg']:.0f} kg；在20 m极端场景中桶倾{robust['barrel_angle_deg']:.3f}°、锚端角{robust['anchor_angle_deg']:.3f}°。",
            ],
            bullets=["关键词：系泊系统", "悬链线", "非线性方程", "约束审计", "鲁棒设计"],
        ),
        Page(
            "1 问题重述与任务分解",
            [
                "题目要求计算不同风速下的钢桶与钢管倾角、锚链形状、浮标吃水和游动范围，并调节重物球使钢桶倾角不超过5°、锚端切线与海床夹角不超过16°。",
                "进一步要在水深16—20 m、流速最高1.5 m/s、风速最高36 m/s下选择锚链型号、长度和重物球质量。设计目标是吃水、游动区域和倾角尽可能小。",
                "本文先复现给定方案，再做极端场景离散搜索。由于题面未给制造成本和安全系数，目标函数中的重量罚项只用于候选排序，不能解释为真实经济成本。",
            ],
        ),
        Page(
            "2 题面参数与数据字典",
            [
                "浮标简化为直径2 m、高2 m、质量1000 kg的圆柱；4根钢管各长1 m、直径0.05 m、质量10 kg；钢桶长1 m、外径0.30 m、总质量100 kg。",
                "锚链有I—V五型，单位长度质量分别为3.2、7、12.5、19.5和28.12 kg/m。风力和水流力采用题面给出的0.625Sv²与374Sv²。",
                "2016A没有独立附件。材料密度7850 kg/m³与标准重力9.80665 m/s²是本模型公开增加的物理常数/材料假设。",
            ],
            table=[
                ["对象", "主要参数"],
                ["浮标", "D=2 m, H=2 m, m=1000 kg"],
                ["钢管", "4×(L=1 m, D=0.05 m, m=10 kg)"],
                ["钢桶", "L=1 m, D=0.30 m, m=100 kg"],
                ["硬约束", "桶倾≤5°；锚端角≤16°；0<吃水<2 m"],
            ],
        ),
        Page(
            "3 假设、受力与符号",
            [
                "假设系统处于稳态，风和流同向且水平；忽略波浪、惯性、涡激振动、锚链弯曲刚度和链环局部接触。钢构件浮力按统一钢密度折算。",
                "设H为贯穿柔性锚链和串联构件的水平张力，V0为锚端竖向张力，w为锚链水下单位长度重量，Ls为悬空链长。",
                "钢桶和每根钢管的倾角由该构件中点处水平张力与竖向张力之比计算。浮标吃水由其自身质量、上部支承的构件有效质量、悬链有效质量和V0共同决定。",
            ],
            table=[
                ["符号", "含义", "单位"],
                ["H", "水平张力", "N"],
                ["V0", "锚端竖向张力", "N"],
                ["w", "锚链水下线重", "N/m"],
                ["Ls", "悬空锚链长度", "m"],
                ["d", "浮标吃水", "m"],
            ],
        ),
        Page(
            "4 环境载荷与浮力平衡",
            [
                "浮标迎风投影取直径乘露出水面高度；水流投影取浮标浸没部分、四根钢管和钢桶的直径—长度投影。未计锚链流阻，这一假设在高流速下可能低估水平力。",
                "水下钢构件使用有效质量m(1-ρw/ρsteel)。接触海床的链段不由浮标承重；全悬浮状态下锚端竖向张力也传递到浮标。",
                "浮力方程、水平力平衡和垂直几何闭合组成三个非线性方程。采用有界最小二乘求解，最终最大无量纲/米制残差写入审计表。",
            ],
        ),
        Page(
            "5 解析悬链线模型",
            [
                "对不可伸长、均匀线重的柔性锚链，以弧长s为参数，有水平切向分量H恒定、竖向分量V(s)=V0+ws。",
                "水平跨度为H/w乘两个反双曲正弦之差；垂直升高为两端张力模长之差除以w。锚端角为arctan(V0/H)。",
                "若求得Ls小于总链长且方程闭合，则多余锚链接触海床并有V0=0；否则令Ls等于总长并求V0≥0。该互斥逻辑避免凭经验预设锚链状态。",
            ],
        ),
        Page(
            "6 数值积分对照模型",
            [
                "独立对dx/ds=H/√(H²+V²)和dy/ds=V/√(H²+V²)做高精度自适应积分，以同一H、V0、w和Ls复算跨度。",
                "解析与数值的x、y绝对误差应接近浮点舍入尺度。该测试能发现反双曲函数符号、端点张力和单位线重实现错误，但不能验证模型假设是否符合真实海况。",
                "三个题面风速状态都保存了对照结果。自动测试进一步要求绝对误差小于10⁻⁸ m。",
            ],
        ),
        Page(
            "7 题1与题2计算结果",
            [
                "12 m/s时锚链仍有海床接触；24 m/s和36 m/s时本模型进入全悬浮状态。随着风速提高，桶倾、锚端角、吃水和水平游动整体增大。",
                "36 m/s下原1200 kg重物球方案同时越过桶倾与锚端角限制，说明题2必须调整设计。这里的判断来自显式约束审计，而不是视觉判断锚链曲线。",
                "游动区域以水平偏移半径报告；实际平面方向随风流方向变化。若风流不同向，需要二维向量叠加并重新求解。",
            ],
            table=[
                ["风速", "状态", "吃水/m", "桶倾/°", "锚角/°", "游动/m"],
                *rows,
            ],
            image="2016A_constraint_angles.png",
        ),
        Page(
            "8 原方案误差与约束审计",
            [
                "每个状态检查四类硬条件：钢桶倾角、锚端角、吃水区间、非线性方程最大残差。解析—数值悬链线误差作为独立实现审计。",
                "约束违反数量为零才可称为可行。目标函数更小但违反任一硬约束的方案不会排在可行候选之前。",
                "锚质量600 kg虽为题面参数，但本版未建立锚在海床上的抗拔、摩擦和土体承载模型；16°限制被视作题面给出的代理安全条件。",
            ],
        ),
        Page(
            "9 多目标离散设计",
            [
                "搜索I—V型锚链、20—36 m偶数长度和1000—5500 kg重物球。每一设计在水深16、18、20 m、风36 m/s、流1.5 m/s三个场景求解。",
                "候选必须在全部场景通过四项硬审计。可行候选按最大游动半径、最大桶倾、重物球质量罚项及链质量—长度罚项的加权和排序。",
                "权重只表达“控制游动和倾角，同时避免无限增重”的工程偏好。不同成本、安全偏好会改变排序，应把Pareto前沿交给设计者而非隐藏在单一分数中。",
            ],
        ),
        Page(
            "10 鲁棒候选结果",
            [
                f"当前权重下排名首位的可行候选为{robust['chain_type']}型锚链、长度{robust['chain_length_m']:.1f} m、重物球{robust['ballast_mass_kg']:.0f} kg。",
                f"在20 m、36 m/s风、1.5 m/s流的报告场景，吃水{robust['draft_m']:.3f} m，桶倾{robust['barrel_angle_deg']:.3f}°，锚端角{robust['anchor_angle_deg']:.3f}°，游动半径{robust['excursion_radius_m']:.3f} m。",
                "这只是离散网格与当前静力假设下的候选，不是现实工程定型结论。重物球质量较大，必须进一步检查浮标储备浮力、结构强度、安装能力与失效后果。",
            ],
            table=[
                ["审计项", "观测", "上限", "通过"],
                ["钢桶倾角", fmt(robust["barrel_angle_deg"]), "5°", "是"],
                ["锚端角", fmt(robust["anchor_angle_deg"]), "16°", "是"],
                ["吃水", fmt(robust["draft_m"]), "2 m", "是"],
                ["方程残差", f"{robust['equation_residual_max']:.2e}", "1e-6", "是"],
            ],
        ),
        Page(
            "11 敏感性分析",
            [
                "对鲁棒候选分别改变风速、流速、重物球质量和海水密度，其他参数保持不变，观察桶倾、锚端角、吃水和游动半径。",
                "流力与速度平方成正比，因此流速误差会非线性放大。增加重物球通常降低桶倾，却增加吃水和安装负担；目标之间存在真实冲突。",
                "敏感性曲线用于识别关键参数，不能代替联合极端场景。下一步应对风流方向、系数、材料密度和水深做全局采样。",
            ],
            image="2016A_sensitivity.png",
        ),
        Page(
            "12 极限情形与模型校验",
            [
                "当风流趋于零，H应趋小、构件趋近竖直；当链上有海床接触时V0=0、锚端角为0；当链完全悬浮时Ls等于总链长。",
                "吃水必须落在0—2 m内，几何闭合要求链垂升与五个刚性构件的竖向投影之和等于水深减吃水。",
                "这些不变量与数值积分对照构成回归测试。若修改载荷或构件模型后任一测试失败，结果不得进入论文和网页。",
            ],
        ),
        Page(
            "13 工程适用性与风险",
            [
                "稳态模型忽略波浪循环载荷、疲劳、链环磨损、浮标横摇、海床坡度、锚土耦合和海生物附着；这些因素均可能扩大真实载荷或改变几何。",
                "高达数吨的重物球虽在数学模型中可行，但运输、吊装、连接强度和浮标储备浮力可能使其工程上不可取。模型只负责揭示静力权衡。",
                "建议后续引入安全系数、材料强度、成本和失效概率，开展时域动力仿真与水池/海试标定，并将16°代理约束替换为现场土体参数下的抗拖移模型。",
            ],
        ),
        Page(
            "14 模型评价与改进方向",
            [
                "模型优点是受力路径透明、两种悬链状态自动切换、解析与数值双重复核、所有硬约束可机器审计。",
                "主要局限是载荷投影简化、未计链流阻、构件倾角用中点张力近似、重物球和钢构件统一材料密度，且多目标权重并非题面给定。",
                "可扩展方向包括二维/三维风流、非均匀链、弹性伸长、动力响应、Pareto优化和不确定性可靠度设计。任何扩展都应保留当前基线作为回归比较。",
            ],
        ),
        Page(
            "15 结论与复现说明",
            [
                "本文完成题面参数字典、给定方案复算、悬链线双重实现、约束审计、极端场景离散设计和单因素敏感性分析。",
                "复现命令为cumcm-lens run-2016a；Notebook展示公式、状态表、数值积分误差和设计网格。summary.json保留假设、题面参数和全部审计。",
                "报告中的鲁棒候选是数学建模训练结果，不构成真实海上设备设计或安全认证。",
            ],
            bullets=[
                "参数字典：data/dictionaries/2016A.md",
                "Notebook：notebooks/2016A_mooring.ipynb",
                "派生表：data/processed/2016A/",
                "自动测试：tests/test_mooring.py",
            ],
        ),
    ]


def crop_pages() -> list[Page]:
    summary = json.loads((PROCESSED / "2024C" / "summary.json").read_text(encoding="utf-8"))
    model_rows = [
        [
            item["scenario"],
            fmt(item["objective_profit_yuan"] / 1e6),
            fmt(item["mip_gap"] * 100, 2) + "%",
            fmt(item["runtime_seconds"], 2),
        ]
        for item in summary["models"]
    ]
    return [
        Page(
            "2024C 农作物的种植策略",
            [
                "基于官方附件的整数规划、滞销情景、保守鲁棒系数与约束审计",
                "CUMCM Lens 真题深度复现报告 · 证据版本 v1.0",
                "结果是完整地块单作假设下的经审计可行解；最优性缺口如实披露。",
            ],
        ),
        Page(
            "摘要",
            [
                f"本文读取官方附件中的{summary['quality']['land_rows']}个地块、{summary['quality']['crop_rows']}种作物、{summary['quality']['planting_rows_2023']}条2023种植记录和{summary['quality']['statistics_rows']}条产量成本价格记录，总面积约{summary['quality']['total_land_mu']:.0f}亩。",
                "建立2024—2030完整地块二元种植模型，表达地类—作物适种、容量、水浇地稻菜互斥、禁止连作和任意三年豆类约束。销量使用连续变量，比较滞销浪费、超额半价和区间保守端点三种情景。",
                "朴素重复2023基线存在大量连作与豆类窗口违反；三个MILP输出均通过全部约束审计。求解器在限时内未全部证明最优，本文逐项报告MIP gap，不将可行解表述为全局最优。",
            ],
            bullets=["关键词：种植规划", "混合整数规划", "轮作", "情景分析", "鲁棒优化"],
        ),
        Page(
            "1 问题重述与规划范围",
            [
                "题目要求制定2024—2030种植方案，在不同滞销处理下提高收益，并考虑销量、亩产、成本和价格的不确定性及潜在相关性。",
                "地类季次不同：旱地、梯田和山坡地一年一季；水浇地可种单季水稻或两季蔬菜；普通大棚第一季蔬菜、第二季食用菌；智慧大棚两季蔬菜。",
                "所有地块禁止连续种同一作物，且每块地任意连续三年内至少种一次豆类。本文把规则转为可审计线性约束。",
            ],
        ),
        Page(
            "2 数据来源与完整性核验",
            [
                "附件1提供地块和作物基础表，附件2提供2023种植和统计参数。合并单元格造成的空白地块名向下填充，最终87条记录均可与地块表关联。",
                "销量基准按2023每条种植面积乘对应地类—季次亩产量汇总。智慧大棚第一季参数依据附件2明确注释映射到普通大棚第一季，未人工猜测。",
                "销售价格区间解析为低值、高值和中点。常规情景使用中点，鲁棒情景使用区间低端并叠加题面给出的年度变化保守端。",
            ],
            table=[
                ["对象", "核验值"],
                ["地块", str(summary["quality"]["land_rows"])],
                ["作物", str(summary["quality"]["crop_rows"])],
                ["2023种植记录", str(summary["quality"]["planting_rows_2023"])],
                ["统计参数记录", str(summary["quality"]["statistics_rows"])],
                ["销量映射失败", str(summary["quality"]["demand_unmatched_planting_rows"])],
            ],
        ),
        Page(
            "3 决策口径与模型边界",
            [
                "为严格表达逐地块轮作，v1规定每个地块每个活跃季次只选择一种作物，面积等于整块面积。原题允许分区混种，因此本模型可行域是原题可行域的保守子集。",
                "这一简化使二元决策与历史作物、相邻季次和三年窗口直接对应，避免用极小面积虚假满足豆类约束。",
                "因此目标值只能比较本仓库三个模型，不能声称是允许任意分块时的原题全局最优。下一版可将地块离散为统一小区并追踪小区级轮作。",
            ],
        ),
        Page(
            "4 符号、目标与销量变量",
            [
                "令x(p,y,s,c)为地块p在年份y、季次s种作物c的0—1变量；产量是面积、亩产和x的乘积。令sold(c,y)为按原价销售量。",
                "sold不超过当年总产量与情景销量上限。超额浪费情景中只有sold产生收入；半价情景中全部产量先按半价计价，sold部分再补足另一半价格。",
                "目标最大化七年收入减种植成本。求解接口使用最小化形式，故对利润取负。",
            ],
            table=[
                ["符号", "含义"],
                ["x(p,y,s,c)", "完整地块作物选择二元变量"],
                ["A(p)", "地块面积/亩"],
                ["q(c,l,s)", "亩产/斤每亩"],
                ["k(c,l,s)", "成本/元每亩"],
                ["sold(c,y)", "原价销量/斤"],
            ],
        ),
        Page(
            "5 地类、季次和模式约束",
            [
                "旱地、梯田、山坡地每年单季从1—15号粮食中选一种。水浇地第一季选水稻或普通蔬菜，若选水稻则第二季关闭，否则第二季在35—37号三种蔬菜中选一种。",
                "普通大棚第一季选17—34号蔬菜、第二季选38—41号食用菌；智慧大棚两季均选17—34号蔬菜。",
                "候选裁剪保留每类季次单位面积基础利润前6种以及全部可种豆类，水浇地额外保留水稻。这提高限时求解稳定性，但进一步缩小可行域，元数据中明确记录。",
            ],
        ),
        Page(
            "6 轮作与豆类硬约束",
            [
                "2024选择不能与同地块2023同季已种作物重复；相邻年份同一作物不能重复。双季地块同一年两个季次也不能种同一作物。",
                "对每块地和2024—2026、2025—2027直至2028—2030五个窗口，窗口内豆类作物选择数至少为1。",
                "完整地块二元口径使“至少一次”具有明确面积含义。审计器独立从输出CSV重新检查容量、连作、豆类窗口和适种性，不只相信求解器状态。",
            ],
        ),
        Page(
            "7 简单基线：重复2023方案",
            [
                "把2023种植安排逐年复制到2024—2030，构成无需优化的朴素基线。它直观且可复算，但预期会违反连续种植和豆类轮作。",
                f"独立审计得到连续种植违反{summary['baseline']['audits'][1]['observed']}次、豆类三年窗口违反{summary['baseline']['audits'][2]['observed']}次。因此它只用于说明约束必要性，不能作为推荐计划。",
                "适种性审计对基线也可能报告违反，因为历史表允许同一地块分区多作，而v1完整地块模型的季次映射更严格；这再次说明基线和优化模型口径必须区分。",
            ],
        ),
        Page(
            "8 情景一：超额产量浪费",
            [
                "销量上限取2023估计销量；超过上限的产量不产生收入，但仍产生种植成本。该情景惩罚盲目集中到高亩产、高价格但需求有限的作物。",
                "模型使用作物—年份销量变量把不同地类生产汇总。由于不同地类价格可能不同，销量收入采用该作物适用记录的价格中位数，这是显式近似。",
                "输出包括完整计划、目标值、求解状态、运行时间、变量/约束数、MIP gap和四项独立审计。",
            ],
        ),
        Page(
            "9 情景二：超额产量半价销售",
            [
                "全部产量至少按50%价格计入收入，销量上限内部分再增加50%价格。相较浪费情景，高产作物的边际价值提高。",
                "该情景并不假设现实市场一定能无限吸收半价农产品；它严格对应题目给定的替代处理规则，用于比较计划结构对剩余产品处置的敏感度。",
                "模型结构与硬约束保持不变，只有目标收入系数变化，因此计划差异可归因于滞销处理而非约束口径变化。",
            ],
        ),
        Page(
            "10 保守鲁棒系数情景",
            [
                "小麦和玉米销量按题面5%—10%年增长区间取5%；其他作物按±5%取低端。亩产按±10%取0.9，成本按约5%年增长累乘。",
                "价格取官方区间低端；食用菌价格再按年下降的保守端处理。该做法是确定性最坏端点近似，而不是已证明覆盖全部相关不确定集的严格两阶段鲁棒优化。",
                "其价值在于给出同一约束下的压力测试。完整鲁棒模型还需建立需求、亩产、成本和价格的联合不确定集及可调决策。",
            ],
        ),
        Page(
            "11 三模型结果与最优性缺口",
            [
                "三个模型均在限时内返回整数可行解并通过容量、连作、豆类窗口和适种性审计。求解器success为false表示达到时限而非无可行解。",
                "MIP gap是当前可行解与求解器界之间的相对差距。只有gap接近0并且求解状态证明最优，才能使用“全局最优”表述。",
                "半价情景目标值显著高于浪费情景符合收入口径；不同情景目标值的绝对值还受价格聚合和完整地块假设影响。",
            ],
            table=[["模型", "目标利润/百万元", "MIP gap", "运行/s"], *model_rows],
            image="2024C_model_comparison.png",
        ),
        Page(
            "12 误差与约束审计",
            [
                "数据审计确认销量计算没有未匹配的历史种植记录。求解后按CSV重算每块地每季面积、相邻年份同作物、任意三年豆类以及地类季次允许作物。",
                "三种优化计划四项违反数均为0。审计通过只证明计划满足当前编码约束，不证明约束完全覆盖题意，也不证明经济参数准确。",
                "计划发布时必须连同scenario、candidate_limit、MIP gap和完整地块假设一起提供，避免CSV脱离元数据被误用。",
            ],
        ),
        Page(
            "13 价格—产量敏感性",
            [
                "固定各情景计划，对价格和亩产分别施加0.9、1.0、1.1倍扰动，计算不考虑销量上限的收入—成本变化。该表用于比较方向，不替代情景目标。",
                "价格和亩产对收入呈乘法影响，二者同时下行时利润下降最快。计划间差异反映作物组合和地类分布。",
                "下一步应在销量上限内重算利润，并用相关采样生成收益分布、下行风险和条件风险价值，而不是只报告均值。",
            ],
            image="2024C_sensitivity.png",
        ),
        Page(
            "14 结果解释、局限与改进",
            [
                "优点是全字段来自官方附件、智慧大棚映射有官方注释依据、规则转为显式线性约束，并把朴素基线失败与优化可行性放在同一审计框架。",
                "局限包括完整地块单作、候选裁剪、作物价格中位数聚合、未建小区级轮作、未显式表示作物替代/互补相关性，以及限时解存在MIP gap。",
                "改进顺序应为：地块小区化与附件模板导出；滚动需求和相关不确定集；暖启动和更长求解；多目标风险收益；最终人工检查农村生产可操作性。",
            ],
        ),
        Page(
            "15 结论与复现说明",
            [
                "本文交付官方附件解析、销量字典、朴素基线、两种滞销MILP、保守鲁棒模型、三套计划、约束审计和敏感性分析。",
                "复现命令为cumcm-lens run-2024c。每个情景在独立进程中运行，避免求解器原生内存相互影响；元数据保存时间、变量、约束和gap。",
                "这些结果适合建模训练和方案比较，不是农业经营建议。实施前必须结合当地政策、市场合同、气候、人工和实际可分区能力复核。",
            ],
            bullets=[
                "数据字典：data/dictionaries/2024C.md",
                "Notebook：notebooks/2024C_crop_planning.ipynb",
                "情景计划：data/processed/2024C/",
                "模型实现：src/cumcm_lens/cases/crop_planning.py",
            ],
        ),
    ]


def styles() -> dict[str, ParagraphStyle]:
    if not FONT_PATH.exists():
        raise FileNotFoundError(
            f"{FONT_PATH} is required; see assets/fonts/OFL.txt for the font license"
        )
    if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ChineseTitle",
            parent=base["Title"],
            fontName=FONT_NAME,
            fontSize=22,
            leading=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#153a5b"),
            spaceAfter=22,
        ),
        "h1": ParagraphStyle(
            "ChineseHeading",
            parent=base["Heading1"],
            fontName=FONT_NAME,
            fontSize=16,
            leading=22,
            textColor=colors.HexColor("#153a5b"),
            spaceAfter=14,
        ),
        "body": ParagraphStyle(
            "ChineseBody",
            parent=base["BodyText"],
            fontName=FONT_NAME,
            fontSize=10.5,
            leading=18,
            firstLineIndent=21,
            spaceAfter=10,
        ),
        "bullet": ParagraphStyle(
            "ChineseBullet",
            parent=base["BodyText"],
            fontName=FONT_NAME,
            fontSize=10,
            leading=16,
            leftIndent=18,
            bulletIndent=5,
            spaceAfter=5,
        ),
        "table": ParagraphStyle(
            "ChineseTable",
            parent=base["BodyText"],
            fontName=FONT_NAME,
            fontSize=8.5,
            leading=12,
        ),
    }


def footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setFont(FONT_NAME, 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(2 * cm, 1.2 * cm, "CUMCM Lens · 可复现真题研究")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"第 {document.page} 页")
    canvas.restoreState()


def build_pdf(path: Path, pages: list[Page]) -> None:
    if not 15 <= len(pages) <= 20:
        raise ValueError(f"Expected 15–20 designed pages, got {len(pages)}")
    style = styles()
    document = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=2.0 * cm,
        rightMargin=2.0 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title=pages[0].title,
        author="CUMCM Lens",
    )
    story = []
    for index, page in enumerate(pages):
        if index == 0:
            story.extend([Spacer(1, 4.5 * cm), Paragraph(page.title, style["title"])])
        else:
            story.append(Paragraph(page.title, style["h1"]))
        for paragraph in page.paragraphs:
            story.append(Paragraph(paragraph, style["body"]))
        if page.bullets:
            for item in page.bullets:
                story.append(Paragraph(item, style["bullet"], bulletText="•"))
        if page.table:
            data = [
                [Paragraph(str(cell), style["table"]) for cell in row] for row in page.table
            ]
            table = Table(data, repeatRows=1, hAlign="CENTER")
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dceaf5")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#153a5b")),
                        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#94a3b8")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 5),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.extend([Spacer(1, 0.2 * cm), table])
        if page.image:
            image_path = FIGURES / page.image
            if image_path.exists():
                image = Image(str(image_path))
                image._restrictSize(16.5 * cm, 8.0 * cm)
                story.extend([Spacer(1, 0.3 * cm), image])
        if index < len(pages) - 1:
            story.append(PageBreak())
    document.build(story, onFirstPage=footer, onLaterPages=footer)


def build_markdown(path: Path, pages: list[Page]) -> None:
    chunks = [f"# {pages[0].title}\n"]
    for page in pages[1:]:
        chunks.append(f"\n## {page.title}\n")
        chunks.extend(f"\n{paragraph}\n" for paragraph in page.paragraphs)
        if page.bullets:
            chunks.extend(f"\n- {item}" for item in page.bullets)
            chunks.append("\n")
        if page.table:
            header, *body = page.table
            chunks.append("\n| " + " | ".join(header) + " |\n")
            chunks.append("|" + "|".join(["---"] * len(header)) + "|\n")
            chunks.extend("| " + " | ".join(row) + " |\n" for row in body)
        if page.image:
            chunks.append(f"\n![图](figures/{page.image})\n")
    path.write_text("".join(chunks), encoding="utf-8")


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    PDF_OUTPUT.mkdir(parents=True, exist_ok=True)
    cases: dict[str, Callable[[], list[Page]]] = {
        "2023E_yellow_river": yellow_pages,
        "2016A_mooring": mooring_pages,
        "2024C_crop_planning": crop_pages,
    }
    for name, factory in cases.items():
        pages = factory()
        build_markdown(REPORTS / f"{name}.md", pages)
        build_pdf(PDF_OUTPUT / f"{name}.pdf", pages)
        print(f"wrote reports/{name}.md and output/pdf/{name}.pdf")


if __name__ == "__main__":
    main()
