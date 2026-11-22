# Shortcuts for everyday tasks. Run `make <target>`, for example `make test`.
# Each target runs inside the project's virtual environment through `uv run`.

.PHONY: install migrate run seed test

# Create .venv and install the dependencies pinned in uv.lock.
install:
	uv sync

# Apply pending database migrations (the app also does this when it starts).
migrate:
	uv run alembic upgrade head

# Start the API with auto-reload: the server restarts when a file changes.
run:
	uv run uvicorn app.main:app --reload --port 8080

# Load the CDN providers in data/cdns.json into the local database.
seed:
	uv run python -m scripts.seed

# Run the test suite.
test:
	uv run pytest
