#!/usr/bin/env python3
"""Build the V5 training manual and workbook as deterministic one-page units."""

from __future__ import annotations

import json
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf"
FONT = ROOT / "assets" / "fonts" / "NotoSansSC-Regular.ttf"
PAGE_W, PAGE_H = A4

INK = HexColor("#17211B")
MUTED = HexColor("#627067")
ACCENT = HexColor("#176B4D")
ACCENT_DARK = HexColor("#0D4935")
SOFT = HexColor("#E8F1EB")
LINE = HexColor("#D9E2DB")
WARNING = HexColor("#9B5D13")
WHITE = HexColor("#FFFFFF")


@dataclass
class Page:
    chapter: str
    title: str
    subtitle: str
    bullets: list[str] = field(default_factory=list)
    checklist: list[str] = field(default_factory=list)
    boundary: str = ""


def wrap(text: str, font: str, size: float, width: float) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in text:
        candidate = current + char
        if current and pdfmetrics.stringWidth(candidate, font, size) > width:
            lines.append(current)
            current = char
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]


def draw_text(canvas: Canvas, text: str, x: float, y: float, width: float, *, size: float = 10.5,
              leading: float = 16, color=INK, max_lines: int | None = None) -> float:
    canvas.setFont("NotoSansSC", size)
    canvas.setFillColor(color)
    lines = wrap(text, "NotoSansSC", size, width)
    if max_lines is not None:
        lines = lines[:max_lines]
    for line in lines:
        canvas.drawString(x, y, line)
        y -= leading
    return y


def draw_cover(canvas: Canvas, manual: bool) -> None:
    canvas.setFillColor(ACCENT_DARK)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    canvas.setFillColor(HexColor("#D9EFE2"))
    for radius, alpha in ((210, .10), (145, .13), (82, .18)):
        canvas.setFillAlpha(alpha)
        canvas.circle(PAGE_W - 36, PAGE_H - 70, radius, fill=1, stroke=0)
    canvas.setFillAlpha(1)
    canvas.setFont("NotoSansSC", 12)
    canvas.setFillColor(HexColor("#B7D8C4"))
    canvas.drawString(58, PAGE_H - 68, "CUMCM LENS / VERSION 5.0")
    canvas.setFont("NotoSansSC", 29)
    canvas.setFillColor(WHITE)
    canvas.drawString(58, PAGE_H - 150, "全国大学生数学建模")
    canvas.drawString(58, PAGE_H - 194, "严谨训练手册" if manual else "训练作业册")
    canvas.setFont("NotoSansSC", 14)
    canvas.setFillColor(HexColor("#D7E6DC"))
    canvas.drawString(60, PAGE_H - 238, "真实赛题 · 可复现代码 · 可审计 AI · 开放 Benchmark")
    canvas.setFillColor(HexColor("#153F31"))
    canvas.roundRect(58, 150, PAGE_W - 116, 142, 16, fill=1, stroke=0)
    draw_text(canvas,
              "从“知道模型名称”走到“能重建结果、能说明边界、能接受复核”。本材料不提供唯一标准答案；它训练的是证据链、基线、验证、约束和表达。",
              78, 255, PAGE_W - 156, size=12, leading=20, color=WHITE)
    canvas.setFont("NotoSansSC", 10)
    canvas.setFillColor(HexColor("#B7D8C4"))
    canvas.drawString(58, 66, "tuxiaobin-123/math · 2026 · Community training edition")
    canvas.showPage()


def draw_page(canvas: Canvas, page: Page, number: int, total: int) -> None:
    canvas.setFillColor(HexColor("#F7F9F7"))
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    canvas.setFillColor(ACCENT)
    canvas.roundRect(44, PAGE_H - 58, 112, 22, 11, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("NotoSansSC", 8.5)
    canvas.drawCentredString(100, PAGE_H - 50.5, page.chapter[:22])
    canvas.setFont("NotoSansSC", 8)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(PAGE_W - 44, PAGE_H - 49, f"CUMCM LENS V5  ·  {number:02d}/{total:02d}")

    y = PAGE_H - 104
    canvas.setFillColor(INK)
    canvas.setFont("NotoSansSC", 23)
    for line in wrap(page.title, "NotoSansSC", 23, PAGE_W - 88)[:2]:
        canvas.drawString(44, y, line)
        y -= 31
    y -= 2
    y = draw_text(canvas, page.subtitle, 44, y, PAGE_W - 88, size=11, leading=17, color=MUTED, max_lines=3)
    y -= 20

    for index, bullet in enumerate(page.bullets, 1):
        canvas.setFillColor(SOFT)
        canvas.circle(58, y + 4, 12, fill=1, stroke=0)
        canvas.setFillColor(ACCENT_DARK)
        canvas.setFont("NotoSansSC", 9)
        canvas.drawCentredString(58, y + 1, str(index))
        y = draw_text(canvas, bullet, 80, y + 8, PAGE_W - 124, size=10.4, leading=16, max_lines=4)
        y -= 15

    if page.checklist:
        y = min(y, 295)
        canvas.setFillColor(WHITE)
        canvas.setStrokeColor(LINE)
        height = min(138, 38 + len(page.checklist) * 25)
        canvas.roundRect(44, y - height + 18, PAGE_W - 88, height, 12, fill=1, stroke=1)
        canvas.setFillColor(ACCENT)
        canvas.setFont("NotoSansSC", 9.5)
        canvas.drawString(60, y - 6, "本页验收")
        yy = y - 32
        for item in page.checklist[:4]:
            canvas.setStrokeColor(ACCENT)
            canvas.rect(60, yy - 2, 9, 9, fill=0, stroke=1)
            draw_text(canvas, item, 78, yy + 1, PAGE_W - 144, size=9.2, leading=14, max_lines=2)
            yy -= 25

    if page.boundary:
        canvas.setFillColor(HexColor("#F6EAD8"))
        canvas.roundRect(44, 64, PAGE_W - 88, 56, 10, fill=1, stroke=0)
        canvas.setFillColor(WARNING)
        canvas.setFont("NotoSansSC", 8.5)
        canvas.drawString(58, 101, "边界")
        draw_text(canvas, page.boundary, 58, 84, PAGE_W - 116, size=8.5, leading=13, color=HexColor("#694A1E"), max_lines=2)
    canvas.setStrokeColor(LINE)
    canvas.line(44, 42, PAGE_W - 44, 42)
    canvas.setFont("NotoSansSC", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(44, 27, "A=官方事实  R=仓库可复算结果  C=结构化建议")
    canvas.drawRightString(PAGE_W - 44, 27, "非 CUMCM 官方出版物")
    canvas.showPage()


def p(chapter: str, title: str, subtitle: str, bullets: list[str], checklist: list[str], boundary: str = "") -> Page:
    return Page(chapter, title, subtitle, bullets, checklist, boundary)


FOUNDATION = [
    p("使用说明","如何使用这套系统","不要从第一页顺读到最后一页；先诊断，再进入相应题型，最后用评分表验收。",["第一次使用先完成五维能力诊断，选择一条主线；每周只交付可检查的文件。","每项任务按 30 分钟诊断、3 小时基线、8 小时完整训练递进；未过基线不得堆复杂模型。","训练结束必须留下来源、环境、代码、结果、局限和复盘六类证据。"],["确定本周唯一主任务","建立输出文件名","约定复盘时间"],"完成页数不等于能力；能否让他人从空环境重跑才是关键。"),
    p("目录","全书结构","76 页由规则、题型、三道案例、实验室、AI 教练、12 周训练和 48 小时作战组成。",["第 4-26 页：证据、选题、数据、验证和七类题型卡。","第 27-44 页：2023E、2016A、2024C 三道完整训练链。","第 45-76 页：实验室、AI 教练、周计划、协作与终检。"],["标记自己当前章节","准备代码环境","打开 V5 网页同步记录"]),
    p("版本路线","V1 到 V5：每一代解决什么","升级不是加功能，而是建立新的能力闭环。",["V1 整理题与模型；V2 增加任务、答案和评分；V3 记录进度并形成作品集。","V4 用确定性规则审查常见错误；V5 增加 Benchmark、贡献协议、复现认证和 API。","V5 的技术完整不等于生态成熟：没有伪造用户、专家社区或官方背书。"],["能说清每版验收条件","区分产品功能与真实运营","只承诺可验证能力"]),
    p("证据规则","A、R、C 三层证据","任何数字先问“它来自哪里、能否复算、还是只是一条建议”。",["A：官方题面、附件与官方页面中的事实；保留文件名、链接、日期与哈希。","R：仓库代码从 A 层资料计算的结果；保留配置、种子、环境、运行时间和输出。","C：模型选择、解释与改进方向；明确额外假设，允许被反驳。"],["每个表格标证据层","R 层能一键重建","C 层写出假设"],"优秀论文不是把 C 层建议伪装成 A 层结论。"),
    p("来源注册","从总链接升级到逐条来源","资料入口不是引用；每个关键事实要定位到具体文件和版本。",["来源 ID 至少包含年份、题号、附件号、文件名、官方页面和访问日期。","原始压缩包保持只读；派生数据放入 processed，禁止覆盖原件。","SHA-256 用于识别同名不同版本，不证明内容一定正确。"],["来源 ID 唯一","原件与派生物分离","记录 SHA-256"]),
    p("可复现规范","从“我电脑能跑”到“别人能重跑”","复现包括输入、代码、环境、随机性、命令和结果容差。",["锁定主依赖下限与兼容测试；保存随机种子不能替代记录算法非确定性。","一个命令生成中间表、图、Notebook 和论文；论文数字不得手工复制修改。","结果快照允许合理浮点容差；优化任务还需保存求解器状态和 gap。"],["空环境安装","单命令运行","关键结果快照"],"烟雾测试只能证明没有立即崩溃，不能证明算法或结论正确。"),
    p("30 分钟选题","先判断问题结构，再判断模型","选题要看任务、数据、约束、可验证性和团队能力，而不是题面背景是否熟悉。",["前 10 分钟：分别写输入、输出、约束和不确定性；禁止讨论模型名。","中间 10 分钟：检查数据能否读取、关键字段是否存在、是否有明确验收指标。","最后 10 分钟：用统一评分表比较三题，记录放弃理由并冻结首选题。"],["三人独立评分","数据能打开","90 分钟冻结选题"]),
    p("选题评分","把主观偏好变成可讨论的分数","评分帮助暴露分歧，不是机械决定。",["建议维度：理解 20%、数据 20%、建模 20%、编程 15%、验证 15%、写作 10%。","每个分数必须附一句证据；“感觉简单”不能作为评分依据。","若最高与次高差小于 5 分，优先做 30 分钟双题基线再决定。"],["公布权重","分数有证据","保留备选题"],"权重是团队决策建议 C，不是官方选题规则。"),
    p("团队决策","解决分歧而不是追求表面一致","重大换模、换题和删约束必须留下决策记录。",["采用“提出人写证据、反对人写反例、负责人做可逆试验”的三步法。","设立模型冻结时间；冻结后只有出现致命错误或明确增益证据才允许更换。","每 4 小时进行一次 10 分钟事实核对，而不是长时间汇报。"],["负责人明确","决策可追踪","冻结条件明确"]),
    p("数据审计","模型之前先审数据","数据问题通常比调参更能改变结论。",["核对行数、列数、单位、类型、唯一键、时间范围、缺失、异常、重复和合并关系。","每项清洗都记录前后数量；无法解释的删除必须停止。","先画原始分布和时间序列，再做标准化、插值和编码。"],["清洗前后行数","单位换算测试","异常处理理由"]),
    p("缺失机制","缺失不是一个 fillna 就结束","缺失的位置可能携带采样机制和极端事件信息。",["按时间、地区、类别和目标水平分层报告缺失；不要只给总缺失率。","区分结构性空白、设备故障、低于检出限和真实零值。","插补模型必须只在训练段拟合；同时保留缺失指示与敏感性分析。"],["缺失语义清楚","训练段拟合","报告插补依赖度"],"高缺失时，模型填补结果的精度不能等同于真实观测。"),
    p("异常与重复","不要把不舒服的数据直接删除","异常可能是错误，也可能是比赛真正关心的极端事件。",["先用物理范围、单位和邻近记录判断，再用统计规则标记；两类依据分开。","重复键要判断是重复记录、同点多测还是多实体，不默认取第一条。","保留原值、标记值和处理值三列，便于回溯。"],["异常只标记不覆盖","重复规则明确","极端事件单独评估"]),
    p("泄漏审计","未来信息泄漏会制造虚假高分","泄漏常发生在切分、聚合、插补、标准化和特征选择阶段。",["所有有监督预处理只在训练集拟合；时间窗口不能包含预测时点之后的数据。","目标衍生字段、事后统计和最终标签编码必须从特征中排除。","用自动断言检查训练最大时间早于测试最小时间，并扫描目标重名。"],["预处理在切分后","无未来窗口","自动断言通过"]),
    p("时间验证","随机切分不是时序预测的默认答案","验证方式必须模拟最终使用场景。",["单次后段留出用于最终外推；滚动起点用于评估跨时期稳定性。","季节任务至少与季节朴素基线比较；避免用测试期反复选模。","预测窗口、更新频率和可用外生变量必须与实际决策时间一致。"],["时间边界明确","至少一个朴素基线","滚动稳定性"]),
    p("实验清单","每次运行都可定位、可比较","没有元数据的结果不能进入论文主表。",["清单记录 case、source_ids、seed、split、features、model、parameters、runtime 和 versions。","输出文件包含 run_id；同一 run_id 的图、表和摘要来自同一结果。","失败运行也记录错误原因，防止反复踩坑和选择性汇报。"],["run_id 唯一","依赖版本齐全","失败也记录"]),
    p("基线规则","先证明简单方法不够","基线决定复杂模型的增益是否有意义。",["回归用均值/线性，分类用多数类/Logistic，时序用持续性/季节朴素。","优化先构造可解释可行解，机理模型先做量纲与极限情形。","复杂模型没有样本外增益、约束增益或解释增益时立即停止。"],["基线可运行","同切分同指标","停止条件写清"]),
    p("指标地图","指标服务问题，不服务漂亮表格","至少同时报告平均误差、极端误差、稳定性和成本。",["回归结合 MAE、RMSE、R²；类别不平衡结合 precision、recall、F1 与 PR-AUC。","优化报告目标、可行性、gap 和耗时；机理模型报告方程残差与物理约束。","任何单一指标都可能掩盖失败子群，必须分层检查。"],["主指标唯一","辅助指标解释","分层误差可见"]),
    p("模型决策树","数据形态决定验证，验证决定模型","先识别任务，再沿“基线—候选—审计—停止”前进。",["目标连续且无时间顺序：回归；有时间顺序：预测；规则决定可行域：优化。","存在守恒、受力或传播方程时，优先机理模型或机理约束混合模型。","评价类题必须检查权重扰动后的排名稳定性，不能只给一组分数。"],["任务类型明确","验证方式匹配","失败条件明确"]),
    p("题型卡","回归","预测连续目标时，先分清解释、插值和外推。",["基线：均值、线性或岭回归；候选：树模型、核方法或神经网络。","检查异方差、极端值、分组偏差和分布漂移；不要只看总体 R²。","若目标取对数，反变换偏差和非负截断必须写清。"],["基线与候选同切分","残差分层","外推边界明确"]),
    p("题型卡","分类","阈值决定错误代价，准确率不是万能指标。",["先给多数类和 Logistic 基线；类别不平衡时使用分层切分和合适采样。","报告混淆矩阵、F1、召回和阈值曲线；概率输出检查校准。","时间或主体相关样本要按时间/主体分组，禁止同一实体跨训练测试。"],["类别比例报告","阈值有理由","主体不泄漏"]),
    p("题型卡","时间预测","预测的是未来，而不是重建过去。",["设置持续性、季节朴素和趋势基线；滚动验证覆盖多个起点。","滞后、滚动和季节特征只使用预测时点之前的信息。","报告窗口长度、更新频率、极端期误差和漂移。"],["未来频率正确","无未来特征","多起点评估"]),
    p("题型卡","优化","先保证规则翻译正确，再比较算法。",["逐条把自然语言写成变量、目标和约束，并为每条约束构造反例测试。","报告求解状态、上下界、MIP gap 和限时；可行解不等于全局最优。","用模型外审计器重新读取结果，逐条检查容量、连作和适种性。"],["变量粒度明确","状态与 gap 齐全","独立约束审计"]),
    p("题型卡","机理方程","数值收敛不代表物理正确。",["从受力、守恒或几何关系推导；每个符号有单位和正方向。","用量纲、极限情形、解析对照或独立积分验证实现。","明确忽略的物理过程，并说明模型不能用于哪些工程决策。"],["量纲闭合","独立对照","工程边界"]),
    p("题型卡","模拟","随机数不是解释，分布假设才是核心。",["固定种子、报告重复次数、置信区间和收敛曲线。","能解析求期望的部分先解析，再用模拟验证；避免用模拟替代简单推导。","对输入分布、相关性和尾部假设做敏感性。"],["种子与重复次数","置信区间","分布敏感性"]),
    p("题型卡","综合评价","权重改变时，结论是否还站得住？",["指标方向、标准化和权重来源逐项公开；避免重复指标放大同一维度。","透明加权作为基线，对比 PCA、熵权或层次方法，但不冒充客观真理。","扰动权重与样本，报告排名稳定区间和反转条件。"],["指标不重复","权重来源明确","排名稳定性"]),
]


CASE_TOPICS = {
    "2023E 黄河水沙": [
        ("任务与真实数据","六年水位、流量、含沙量，断面测量与监测点资料构成三类附件。",["逐表解析时间戳，水位和流量无效记录退出；含沙缺失保持为空。","附件 3 的 2023 测量不进入 2016-2021 外推实验。","来源和清洗行数写入 summary.json。"]),
        ("缺失与时间切分","含沙量缺失率约 87.13%，模型结论首先受采样机制限制。",["只在含沙实测行训练；按时间排序后 80/20 外推。","标准化、模型选择和重训顺序分开记录。","随机切分即使分数更高也不采用。"]),
        ("三模型比较","岭回归、随机森林和直方图梯度提升使用同一特征与测试段。",["主指标为 RMSE，同时报告 MAE、R² 和耗时。","当前最佳 RMSE 6.511 kg/m³、R² 0.325，不包装成高精度。","误差按时间和高含沙事件分层。"]),
        ("通量与长缺口","水量积分 Q，沙量积分 QC；相邻时点采用梯形近似。",["超过 48 小时间隔不静默跨越；截断次数逐年报告。","实测含沙优先，只有缺失处使用模型值。","24/48/72 小时阈值做敏感性。"]),
        ("24 个月预测修复","未来日期必须是 24 个唯一月份，阻尼趋势从拟合终点出发。",["明确 freq=MS，防止 24 天冒充 24 个月。","不把最后观测季节残差带入所有未来月份。","加入月份唯一性与跨度大于 650 天的回归测试。"]),
        ("结论与采样","变化快时加密采样是启发式建议，不是现场排班。",["预测结果视为情景基线。","断面网格不一致时不直接做未经插值的点差。","因果解释需要事件窗口、对照和外部资料。"]),
    ],
    "2016A 系泊系统": [
        ("任务与受力","浮标、钢管、钢桶、重物球和锚链形成串联系统。",["逐体隔离，统一正方向与有效重量。","风力、水流力和浮力写入平衡方程。","锚链流阻、波浪和惯性为明确忽略项。"]),
        ("悬链线推导","水平张力恒定，竖向张力随弧长线性变化。",["推导水平跨度与垂直升高闭式式。","区分接地与全悬浮状态。","锚端角由端点张力分量确定。"]),
        ("独立数值复核","对 dx/ds 和 dy/ds 做自适应积分，不能复制解析公式。",["解析与数值误差小于 1e-8 m。","多风速、多水深重复验证。","此测试验证实现，不验证物理假设。"]),
        ("非线性求解","浮力、水平载荷和几何闭合组成非线性方程组。",["使用有界求解，保存初值、边界和残差。","失败状态不自动填默认答案。","用极限情形验证符号与趋势。"]),
        ("鲁棒候选","在 16/18/20 m 水深和极端风流场景跨设计网格审计。",["当前候选 I 型 36 m、5000 kg。","桶倾、锚角、吃水和方程残差四类约束通过。","目标函数与搜索网格限制必须公开。"]),
        ("工程边界","稳态竞赛模型不能替代工程认证。",["未覆盖波浪、疲劳、涡激振动和锚土耦合。","材料、阻力系数和安全系数需现场/规范校核。","结论写作“模型候选”，不写“工程最优方案”。"]),
    ],
    "2024C 种植规划": [
        ("数据与索引","54 块地、45 种作物、2023 种植与经济参数构成优化输入。",["统一地块、地类、面积、作物、季次键。","历史种植状态连接到 2024 连作约束。","普通/智慧大棚的统计口径显式映射。"]),
        ("变量与可行域","决策变量按地块-年-季-作物索引。",["当前实现采用整地块单作和候选裁剪。","该假设是题目允许分区混种可行域的保守子集。","变量粒度改变会影响目标上限，必须披露。"]),
        ("四类硬约束","容量、适种、连作和三年豆类窗口逐条形式化。",["每类约束都有故意违规反例。","求解结果由模型外审计器再次检查。","三种情景当前均为 0 项硬约束违反。"]),
        ("销售情景","超额浪费、超额半价和保守鲁棒只改变价值/参数，不偷改规则。",["需求、价格、成本和产量口径分别记录。","情景差异通过同一输出表比较。","最坏端点是公开假设 C，不是官方设定。"]),
        ("求解状态与 gap","限时整数解必须报告状态、上下界和 MIP gap。",["三情景 gap 为 9.18%、3.01%、2.44%。","0 违规只说明可行，不说明全局最优。","记录时限与候选裁剪对最优性的影响。"]),
        ("敏感性与论文","价格和产量扰动用于判断结论何时反转。",["利润图、计划表和摘要从同一结果文件生成。","对关键作物和地块报告边际变化。","结论区分模型内收益、现实可执行性和额外风险。"]),
    ],
}


LAB_TOPICS = [
    ("实验室总流程","定义任务 → 固定数据切分 → 跑基线 → 候选模型 → 审计 → 冻结结果。"),
    ("运行元数据","每次运行保存 run_id、commit、环境、种子、参数、耗时和来源。"),
    ("公平比较","所有模型使用相同训练/测试、特征可用性和指标计算。"),
    ("残差诊断","总体指标之后检查时间、群体、预测水平和极端事件误差。"),
    ("约束回调","优化结果进入排行榜前必须通过模型外硬约束审计。"),
    ("敏感性设计","优先扰动最不确定且最可能改变决策的参数。"),
    ("不确定性传播","输入和模型误差传播到最终总量、排名或决策。"),
    ("性质测试","用单调性、守恒、上下界和极限情形测试代码。"),
    ("结果快照","主指标和关键表保留容差快照，阻止无意漂移。"),
    ("依赖兼容","最低允许依赖版本也要测试，避免声明范围内运行失败。"),
    ("Notebook 复现","Notebook 从空内核顺序运行，禁止依赖隐藏状态。"),
    ("论文图表","图、表、摘要数字由同一结构化结果自动生成。"),
]


AI_TOPICS = [
    ("AI 教练原则","AI 首先追问证据和基线，不直接泄露整题答案。"),
    ("规则审查器","检查随机时序切分、缺失基线、未经证明的最优、因果越界和缺少来源。"),
    ("评分与申诉","规则分数可重复，但不是专家评分；用户可以查看规则 ID 并人工覆盖。"),
    ("幻觉防线","AI 建议分事实、推断和假设；计算结论必须通过代码重跑。"),
    ("人机分工","AI 适合诊断、生成测试和发现遗漏；人负责题意、假设、伦理和最终责任。"),
]


WEEKS = [
    (1,"2023E","来源注册、数据字典、问题重述"),(2,"2023E","清洗、缺失机制、时间切分"),
    (3,"2023E","基线、非线性模型、残差"),(4,"2023E","通量、24 月预测、真实性声明"),
    (5,"2016A","受力图、单位、极限情形"),(6,"2016A","悬链线、数值积分、残差"),
    (7,"2016A","三风速、约束、设计搜索"),(8,"2016A","稳健场景、敏感性、工程边界"),
    (9,"2024C","表格解析、变量、规则形式化"),(10,"2024C","可行基线、MILP、约束审计"),
    (11,"2024C","销售情景、鲁棒、MIP gap"),(12,"2024C","图表、48 小时演练、复现清单"),
]


def manual_pages() -> list[Page]:
    pages = list(FOUNDATION)
    for chapter, topics in CASE_TOPICS.items():
        for title, subtitle, bullets in topics:
            pages.append(p(chapter, title, subtitle, bullets,
                           ["代码/公式可复查", "关键数字带证据等级", "限制会影响结论"],
                           "案例结果只对应仓库当前模型与官方资料版本，不是唯一标准答案。"))
    for title, subtitle in LAB_TOPICS:
        pages.append(p("模型基准实验室", title, subtitle,
                       ["先固定比较协议，再运行模型。", "通过自动审计后才进入主结果表。", "保存失败运行与停止理由。"],
                       ["协议先于结果", "元数据完整", "结果可重建"]))
    for title, subtitle in AI_TOPICS:
        pages.append(p("可审计 AI 教练", title, subtitle,
                       ["每条反馈显示严重度、规则 ID、动作和证据级别。", "AI 不能把结构化建议写成官方结论。", "最终模型与论文由参赛者负责。"],
                       ["规则可查看", "允许人工覆盖", "计算必须复跑"],
                       "AI 评分用于训练诊断，不代表竞赛评委或专家意见。"))
    for week, case, focus in WEEKS:
        pages.append(p("12 周训练路线", f"第 {week} 周 · {case}", focus,
                       [f"30 分钟诊断：在没有完整解答的情况下，指出本周最可能犯的三个错误。",
                        f"3 小时基线：提交一个可运行、可解释、带最小测试的版本。",
                        f"8 小时完整：加入模型对比、审计、敏感性和一页复盘。"],
                       ["交付源文件", "评分达到 70/100", "记录下一周淘汰事项"],
                       "若基线未通过，不进入更复杂模型；未完成任务顺延，不用阅读量抵消。"))
    pages.extend([
        p("48 小时作战","七个冻结节点","用时间节点保护模型与论文的一致性。",["H+1.5 冻结选题；H+4 冻结数据字典与基线。","H+16 冻结主模型；H+28 冻结图表；H+36 冻结论文。","H+44 终检；H+48 保存校验值、提交并立即记录复盘。"],["冻结时间写入日志","重大变更全员同意","最终文件哈希保存"]),
        p("团队协作","三人角色与共同责任","建模、编程、论文各有主责，但真实性是共同责任。",["建模负责人管理公式、假设和结构；编程负责人管理数据、实验和测试。","论文负责人管理证据、图表、引用和终检；不能手工修改结果数字。","每 4 小时交换一次“当前最可能错的地方”，而不是只汇报进度。"],["角色主责明确","关键数字双人核对","有替补与交接文件"]),
        p("最终验收","提交前 20 项终检","最后一小时只检查事实、文件和一致性。",["题号、单位、变量、图表、摘要数字、结论数字和附件文件名完全一致。","所有‘最优’‘证明’‘因果’‘显著’都有对应证据；否则降级措辞。","代码从空环境运行；PDF 字体嵌入、无乱码、无溢出；提交包校验值保存。"],["代码测试通过","PDF 逐页检查","复现清单通过"],"完成这三项只能说明提交达到仓库内部严谨标准，不代表获奖或官方认证。"),
    ])
    assert len(pages) == 75, len(pages)
    return pages


def workbook_pages() -> list[Page]:
    tasks: list[Page] = []
    for week, case, focus in WEEKS:
        for level, hours, deliverable in (
            ("诊断任务", "30 分钟", "错误清单 + 结构草图"),
            ("基线任务", "3 小时", "可运行基线 + 最小测试"),
            ("完整任务", "8 小时", "模型对比 + 审计 + 复盘"),
        ):
            tasks.append(p(f"W{week} · {case}", f"{level} · {focus}", f"建议时限：{hours}；强制产出：{deliverable}。",
                           ["任务前：写下输入、输出、约束、证据和停止条件。",
                            "任务中：每次修改记录理由；失败运行也保存。",
                            "任务后：分别给正确性、复现性、解释性和表达评分。"],
                           ["基础 60：产出完整且能运行", "良好 80：验证与边界清楚", "优秀 95：独立复现与反例测试"],
                           "自评分不得代替代码、数据和结果证据。"))
    tasks.append(p("评分表","通用 100 分量表","所有作业使用同一底层尺度，便于看见真实进步。",
                   ["正确性 30：公式、代码、单位和约束。","可复现性 25：来源、环境、种子、命令和结果。","验证 20、解释 15、表达 10；任何致命泄漏或伪造直接不通过。"],
                   ["总分记录", "致命项单列", "写下下一次改进"]))
    assert len(tasks) == 37
    return tasks


def build(path: Path, pages: list[Page], *, manual: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas = Canvas(str(path), pagesize=A4, pageCompression=1)
    canvas.setTitle("CUMCM Lens V5 严谨训练手册" if manual else "CUMCM Lens V5 训练作业册")
    canvas.setAuthor("CUMCM Lens")
    draw_cover(canvas, manual)
    total = len(pages) + 1
    for number, page in enumerate(pages, 2):
        draw_page(canvas, page, number, total)
    canvas.save()
    reader = PdfReader(str(path))
    if len(reader.pages) != total:
        raise RuntimeError(f"Unexpected page count for {path}: {len(reader.pages)} != {total}")


def main() -> None:
    if not FONT.exists():
        raise FileNotFoundError("Run scripts/prepare_report_font.py before building handbooks")
    pdfmetrics.registerFont(TTFont("NotoSansSC", str(FONT)))
    manual = OUT / "CUMCM_Lens_V5_严谨训练手册.pdf"
    workbook = OUT / "CUMCM_Lens_V5_训练作业册.pdf"
    build(manual, manual_pages(), manual=True)
    build(workbook, workbook_pages(), manual=False)
    result = {
        "manual": {"path": str(manual.relative_to(ROOT)), "pages": len(PdfReader(str(manual)).pages)},
        "workbook": {"path": str(workbook.relative_to(ROOT)), "pages": len(PdfReader(str(workbook)).pages)},
        "font": "Noto Sans SC (embedded)",
    }
    (OUT / "v5_pdf_manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
