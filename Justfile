# Run tests and generate coverage report
test:
    uv run coverage run --source src --module pytest tests/ -v -ra --log-cli-level=INFO
    uv run coverage report -m

# Format and fix
format:
    uv run ruff check --select I --fix .
    uv run ruff format .

# Update test snapshots
update-snapshots:
    uv run pytest tests/ --snapshot-update --allow-snapshot-deletion

# Build sdist and wheel
build:
    rm -rf dist
    uv build

# Publish package to PyPI
publish: build
    uv publish
