.PHONY: install validate lint test smoke schemas tree

install:
	python -m pip install -e ".[dev]"

validate:
	python scripts/validate_repo.py

lint:
	python -m ruff check src tests scripts
	python -m ruff format --check src tests scripts

test:
	python scripts/run_full_pytest.py

smoke:
	bash scripts/smoke_demo.sh

schemas:
	python scripts/export_schemas.py

tree:
	find . -maxdepth 3 -type f | sort
