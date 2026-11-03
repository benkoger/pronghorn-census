# Pre-Commit Hooks: Ruff Linting & Formatting

Branch `hooks`.

## 1. Overview

Adds automated code linting and formatting using Ruff via Git pre-commit hooks to ensure consistent Python style across the backend (`airial_api`).

## 2. Configuration

### `.pre-commit-config.yaml`
Configured at the repository root:
- **`ruff-check`**: Runs Ruff linter with `--fix` (sorts imports, fixes autofixable errors).
- **`ruff-format`**: Enforces Ruff code formatting.
- **Hygiene hooks**:
  - `trailing-whitespace`
  - `end-of-file-fixer`
  - `check-yaml`
  - `check-added-large-files` (`--maxkb=2000`)

### `airial_api/pyproject.toml`
- **Target version**: Python 3.13 (`py313`)
- **Line length**: 126 characters
- **Lint rules enabled**:
  - `E`, `W`: pycodestyle errors and warnings
  - `F`: Pyflakes
  - `I`: isort (import sorting)
- **Dev dependencies**: `ruff>=0.17.3`, `pre-commit>=4.0.0`

## 3. Setup & Usage

### Initial Hook Installation
From repo root, install the git hook into `.git/hooks/`:
```bash
cd airial_api
uv run pre-commit install
```

### Manual Runs
Run across all files manually without committing:
```bash
cd airial_api
uv run pre-commit run --all-files
```

Run Ruff directly:
```bash
cd airial_api
uv run ruff check . --fix
uv run ruff format .
```

## 4. Verification

- [x] Hook runs automatically on `git commit`.
- [x] Ruff lint checks (`E`, `F`, `W`, `I`) pass across `airial_api/`.
- [x] Ruff formatter passes across `airial_api/`.
