.PHONY: install data run test notebooks reports site clean

install:
	python -m pip install -e ".[dev,notebook,report]"
	npm install

data:
	python scripts/download_official_data.py
	python scripts/prepare_official_data.py

run:
	cumcm-lens run-all

test:
	PYTHONPATH=src python scripts/run_tests.py

notebooks:
	python scripts/build_notebooks.py

reports:
	PYTHONPATH=src python scripts/refresh_2023e_forecast_from_processed.py
	cumcm-lens paper-figures
	python scripts/prepare_report_font.py
	python scripts/build_reports.py
	python scripts/build_v5_handbooks.py
	python scripts/sync_docs_downloads.py

site:
	python -m http.server 8000 -d docs

clean:
	python scripts/clean_generated.py
