.PHONY: install run seed test

install:
	uv sync

run:
	uv run uvicorn app.main:app --reload --port 8000

seed:
	uv run python -m scripts.seed

test:
	uv run pytest
