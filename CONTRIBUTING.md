# Contributing

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
pytest
```

## Quality gates

- `ruff check src tests`
- `ruff format src tests`
- `mypy src/atlasqueue`
- `pytest tests --cov=atlasqueue --cov-fail-under=60`

## Pull requests

- Keep changes focused and tested
- Update docs for API or architecture changes
- Ensure CI passes before requesting review
