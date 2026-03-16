PORT ?= 8000

.PHONY: dev
dev:
	uvicorn app.main:app --reload --port $(PORT) --reload-dir app --reload-exclude ".venv/*" --reload-exclude "__pycache__/*" --reload-exclude ".pytest_cache/*"
