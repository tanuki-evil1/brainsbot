run:
	uv run python -m app.handlers.main

check:
	uv run ruff check .
	uv run ruff format --check .

install:
	uv sync

al:
	uv run alembic -c alembic.ini revision --autogenerate -m"$(comment)"

upgrade:
	uv run alembic -c alembic.ini upgrade head
