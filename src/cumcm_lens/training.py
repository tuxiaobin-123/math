"""Local-first training, coaching and reproducibility services for CUMCM Lens V5."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Mapping


DIMENSIONS = ("mathematics", "coding", "data", "writing", "mechanism")


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    message: str
    action: str
    evidence: str = "R:rule"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


TRACKS = {
    "2023E": {
        "name": "黄河水沙数据建模",
        "weights": {"mathematics": 0.15, "coding": 0.2, "data": 0.35, "writing": 0.15, "mechanism": 0.15},
        "first_task": "完成时间索引、缺失模式与时间外推切分审计",
    },
    "2016A": {
        "name": "系泊系统机理建模",
        "weights": {"mathematics": 0.3, "coding": 0.15, "data": 0.05, "writing": 0.15, "mechanism": 0.35},
        "first_task": "画完整受力图并独立推导悬链线几何闭合方程",
    },
    "2024C": {
        "name": "种植策略运筹优化",
        "weights": {"mathematics": 0.25, "coding": 0.3, "data": 0.15, "writing": 0.15, "mechanism": 0.15},
        "first_task": "把适种、连作和三年豆类规则写成可测试约束",
    },
}


def _bounded_scores(scores: Mapping[str, Any]) -> dict[str, int]:
    clean: dict[str, int] = {}
    for name in DIMENSIONS:
        value = int(scores.get(name, 0))
        if not 0 <= value <= 100:
            raise ValueError(f"{name} must be between 0 and 100")
        clean[name] = value
    return clean


def diagnose_profile(scores: Mapping[str, Any]) -> dict[str, Any]:
    clean = _bounded_scores(scores)
    ranking = []
    for case, track in TRACKS.items():
        readiness = round(sum(clean[key] * weight for key, weight in track["weights"].items()), 1)
        ranking.append({"case": case, "track": track["name"], "readiness": readiness})
    ranking.sort(key=lambda item: item["readiness"], reverse=True)
    weakest = sorted(clean.items(), key=lambda item: item[1])[:2]
    return {
        "scores": clean,
        "recommended_case": ranking[0]["case"],
        "ranking": ranking,
        "weakest_dimensions": [{"dimension": key, "score": value} for key, value in weakest],
        "next_action": TRACKS[ranking[0]["case"]]["first_task"],
        "evidence": "R: deterministic weighted rubric v5.0; not a psychometric assessment",
    }


def recommend_models(task: str, *, time_ordered: bool = False, nonlinear: bool = False) -> dict[str, Any]:
    task = task.strip().lower()
    catalog = {
        "regression": ["mean/linear baseline", "ridge regression", "gradient boosting"],
        "classification": ["majority/logistic baseline", "random forest", "gradient boosting"],
        "forecast": ["seasonal naive", "damped trend", "tree model with lag-only features"],
        "optimization": ["rule-based feasible baseline", "linear/integer programming", "robust scenarios"],
        "mechanism": ["dimensional/limit baseline", "governing equations", "numerical solver + residual audit"],
        "evaluation": ["transparent weighted score", "PCA/entropy sensitivity comparison", "rank stability audit"],
        "simulation": ["analytic expectation", "fixed-seed Monte Carlo", "variance-reduction comparison"],
    }
    models = catalog.get(task, catalog["regression"])
    validations = ["simple baseline must be reported", "save seed, parameters, runtime and dependency versions"]
    if time_ordered or task == "forecast":
        validations.extend(["chronological or rolling split", "reject random split and future-derived features"])
    else:
        validations.append("use held-out or nested cross-validation suited to sampling structure")
    if nonlinear:
        validations.append("compare nonlinear gain against the simplest adequate baseline")
    return {
        "task": task,
        "candidate_sequence": models,
        "validation_plan": validations,
        "stop_rule": "Do not add complexity unless out-of-sample evidence or constraint quality improves.",
        "evidence": "C: structured recommendation; model choice remains problem-dependent",
    }


def coach_review(text: str, context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    context = dict(context or {})
    normalized = text.lower()
    findings: list[Finding] = []
    rules = [
        (("随机划分" in text or "random split" in normalized) and context.get("time_ordered", True),
         Finding("error", "TIME_SPLIT", "时间序列使用随机划分会泄漏未来结构。", "改用时间外推或滚动起点验证。")),
        (not any(word in normalized for word in ("baseline", "基线", "朴素", "线性")),
         Finding("warning", "NO_BASELINE", "方案没有可解释的简单基线。", "先定义最低比较线，再判断复杂模型是否真正增益。")),
        (any(word in normalized for word in ("最优", "optimal", "全局最优")) and not any(word in normalized for word in ("gap", "证明", "bound", "界")),
         Finding("error", "UNPROVEN_OPTIMAL", "出现“最优”结论，但没有最优性证明或求解器界。", "报告可行性、停止状态与 MIP gap；无法证明时改称候选解。")),
        (not any(word in normalized for word in ("误差", "残差", "rmse", "mae", "敏感性", "审计")),
         Finding("warning", "NO_AUDIT", "方案没有误差、残差或约束审计。", "至少加入一个预测误差审计和一个结构/约束审计。")),
        (any(word in normalized for word in ("因果", "导致", "证明了")) and not any(word in normalized for word in ("对照", "识别", "实验", "工具变量", "断点")),
         Finding("warning", "CAUSAL_OVERCLAIM", "因果措辞缺少识别设计。", "降级为相关/筛查结论，或补充可信的因果识别方案。")),
        (not any(word in normalized for word in ("来源", "附件", "官方", "sha", "证据")),
         Finding("info", "NO_SOURCE", "未说明题面、附件或参数来源。", "为关键输入增加来源 ID、版本和文件校验值。")),
    ]
    findings.extend(finding for condition, finding in rules if condition)
    if not findings:
        findings.append(Finding("pass", "BASIC_PASS", "未触发基础规则风险。", "继续人工核验公式、数据与边界条件。"))
    score = max(0, 100 - sum({"error": 24, "warning": 12, "info": 5, "pass": 0}[item.level] for item in findings))
    questions = [
        "你的最简单基线是什么，复杂模型比它好在哪里？",
        "哪一条结论最依赖额外假设，如何做敏感性分析？",
        "如果删掉一个关键特征或约束，结果会怎样？",
    ]
    return {
        "mode": "auditable_rule_coach",
        "score": score,
        "findings": [item.to_dict() for item in findings],
        "socratic_questions": questions,
        "boundary": "规则结果用于训练诊断，不是官方评审意见，也不替代复算。",
    }


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def certify_submission(manifest: Mapping[str, Any], root: Path) -> dict[str, Any]:
    findings: list[Finding] = []
    required = ("case", "source_ids", "seed", "metrics", "artifacts", "limitations")
    for field in required:
        if field not in manifest or manifest[field] in (None, "", [], {}):
            findings.append(Finding("error", "MISSING_FIELD", f"缺少清单字段：{field}", "补齐后重新认证。"))
    verified = []
    for artifact in manifest.get("artifacts", []):
        path = (root / str(artifact.get("path", ""))).resolve()
        try:
            path.relative_to(root.resolve())
        except ValueError:
            findings.append(Finding("error", "PATH_ESCAPE", f"文件越出项目根目录：{path}", "只引用仓库内文件。"))
            continue
        if not path.is_file():
            findings.append(Finding("error", "FILE_MISSING", f"文件不存在：{artifact.get('path')}", "提交实际可复算文件。"))
            continue
        actual = file_sha256(path)
        expected = artifact.get("sha256")
        if expected and expected != actual:
            findings.append(Finding("error", "HASH_MISMATCH", f"校验值不一致：{artifact.get('path')}", "更新文件或清单校验值。"))
        verified.append({"path": artifact.get("path"), "sha256": actual})
    if not manifest.get("time_split") and manifest.get("task") in {"forecast", "time_series"}:
        findings.append(Finding("error", "NO_TIME_SPLIT", "时序提交没有声明时间切分。", "写明训练、验证、测试边界。"))
    errors = sum(item.level == "error" for item in findings)
    warnings = sum(item.level == "warning" for item in findings)
    score = max(0, 100 - 20 * errors - 8 * warnings)
    status = "verified" if not errors and len(verified) > 0 else "rejected"
    return {
        "schema": "cumcm-lens-certificate/v1",
        "status": status,
        "score": score,
        "verified_artifacts": verified,
        "findings": [item.to_dict() for item in findings],
        "boundary": "仓库级复现认证，不代表 CUMCM 官方或高校认证。",
    }


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
