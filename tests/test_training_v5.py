import json
from pathlib import Path

from cumcm_lens.training import certify_submission, coach_review, diagnose_profile


def test_diagnosis_is_bounded_and_recommends_track() -> None:
    result = diagnose_profile(
        {"mathematics": 70, "coding": 60, "data": 90, "writing": 50, "mechanism": 40}
    )
    assert result["recommended_case"] == "2023E"
    assert len(result["ranking"]) == 3
    try:
        diagnose_profile({"mathematics": 101})
    except ValueError:
        pass
    else:
        raise AssertionError("out-of-range score must fail")


def test_coach_flags_time_leakage_and_unproven_optimality() -> None:
    review = coach_review("随机划分后用遗传算法得到全局最优解")
    codes = {finding["code"] for finding in review["findings"]}
    assert {"TIME_SPLIT", "UNPROVEN_OPTIMAL"} <= codes
    assert review["score"] < 60


def test_certificate_checks_hash_and_required_fields(tmp_path: Path) -> None:
    artifact = tmp_path / "result.json"
    artifact.write_text(json.dumps({"rmse": 1.2}), encoding="utf-8")
    manifest = {
        "case": "demo",
        "source_ids": ["SRC-1"],
        "seed": 42,
        "metrics": {"rmse": 1.2},
        "limitations": ["demo"],
        "artifacts": [{"path": "result.json"}],
    }
    report = certify_submission(manifest, tmp_path)
    assert report["status"] == "verified"
    assert report["verified_artifacts"][0]["sha256"]
