import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_notebooks_are_valid_nbformat_four_json() -> None:
    notebooks = list((ROOT / "notebooks").glob("*.ipynb"))
    assert len(notebooks) == 3
    for path in notebooks:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["nbformat"] == 4
        assert len(payload["cells"]) >= 10


def test_reports_are_15_to_20_pages() -> None:
    reports = [
        ROOT / "output" / "pdf" / "2023E_yellow_river.pdf",
        ROOT / "output" / "pdf" / "2016A_mooring.pdf",
        ROOT / "output" / "pdf" / "2024C_crop_planning.pdf",
    ]
    assert len(reports) == 3
    for path in reports:
        result = subprocess.run(
            ["pdfinfo", str(path)], capture_output=True, text=True, check=True
        )
        pages_line = next(line for line in result.stdout.splitlines() if line.startswith("Pages:"))
        pages = int(pages_line.split(":")[1])
        assert 15 <= pages <= 20


def test_v5_handbooks_have_expected_page_counts() -> None:
    expected = {
        "CUMCM_Lens_V5_严谨训练手册.pdf": 76,
        "CUMCM_Lens_V5_训练作业册.pdf": 38,
    }
    for name, page_count in expected.items():
        result = subprocess.run(
            ["pdfinfo", str(ROOT / "output" / "pdf" / name)],
            capture_output=True,
            text=True,
            check=True,
        )
        pages_line = next(line for line in result.stdout.splitlines() if line.startswith("Pages:"))
        assert int(pages_line.split(":")[1]) == page_count


def test_processed_summaries_have_explicit_sources_and_limits() -> None:
    for case in ("2016A", "2023E", "2024C"):
        payload = json.loads(
            (ROOT / "data" / "processed" / case / "summary.json").read_text(encoding="utf-8")
        )
        assert payload["source"]
        assert any(key in payload for key in ("limitations", "assumptions", "assumptions_and_boundaries"))
