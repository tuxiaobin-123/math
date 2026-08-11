import pandas as pd

from cumcm_lens.cases.crop_planning import (
    allowed_crops,
    audit_schedule,
    official_stat_key,
)


def test_official_smart_greenhouse_note_mapping() -> None:
    assert official_stat_key(20, "智慧大棚", "第一季") == ("普通大棚", "第一季")
    assert official_stat_key(20, "智慧大棚", "第二季") == ("智慧大棚", "第二季")


def test_land_crop_eligibility_rules() -> None:
    assert 16 in allowed_crops("水浇地", "第一季")
    assert 35 in allowed_crops("水浇地", "第二季")
    assert 35 not in allowed_crops("普通大棚", "第一季")
    assert 40 in allowed_crops("普通大棚", "第二季")


def test_audit_detects_consecutive_crop_and_missing_legume() -> None:
    land = pd.DataFrame([{"plot": "A1", "land_type": "平旱地", "area_mu": 10}])
    planted = pd.DataFrame(
        [{"plot": "A1", "crop_id": 6, "area_mu": 10, "season": "单季"}]
    )
    schedule = pd.DataFrame(
        [
            {
                "plot": "A1",
                "land_type": "平旱地",
                "year": year,
                "season": "单季",
                "crop_id": 6,
                "crop_type": "粮食",
                "area_mu": 10,
            }
            for year in range(2024, 2031)
        ]
    )
    findings = {item["name"]: item for item in audit_schedule(schedule, land, planted)}
    assert not findings["consecutive_crop"]["passed"]
    assert not findings["legume_in_every_three_year_window"]["passed"]
