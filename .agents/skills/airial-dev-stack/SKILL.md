---
name: airial-dev-stack
description: >-
  Use this skill when managing, running, debugging, or restarting the Airial container stack (Podman/Docker compose), Valkey, Postgres, SpiceDB, or the Flask/Vue dev servers.
---

# Airial Local Development & Container Stack

This runbook covers operating and troubleshooting the local development environment for the Airial application.

## 1. Container Environments

The project uses Podman (or Docker) Compose configurations at the repository root.

### Development Mode (with Sample Data)
Uses pre-populated database backups (`local_db/pct_b`) and SpiceDB relationships (`local_db/backup.zed`):
```bash
podman compose -f development.compose.yml up -d
# or docker compose -f development.compose.yml up -d
```

### Clean Bootstrap Mode (Fresh Schema)
Initializes an empty schema using `local_db/db_definitions.sql` and writes the SpiceDB schema from `airial_api/database/spicedb_schema/schema.zed`:
```bash
podman compose -f bootstrap-dev.compose.yml up -d
```

### Checking Status & Logs
```bash
# View running containers
podman compose -f development.compose.yml ps

# Inspect API logs
podman logs -f prong_dev_api

# Inspect Database logs
podman logs -f prong_gres

# Inspect SpiceDB logs
podman logs -f prong_spicedb

# Inspect Valkey logs
podman logs -f prong_dev_valkey
```

---

## 2. Local Process Execution (Non-Container)

When developing frontend or backend outside containers:

### Frontend (`generator_web_app/`)
* **Dev Server**: `npm run dev` (Served on `http://localhost:5173`)
* **Type Check**: `npm run type-check` (`vue-tsc --build`)
* **Build**: `npm run build`

### Backend API (`airial_api/`)
* **Dependency Management**: Uses Astral `uv` (`pyproject.toml`, `uv.lock`)
* **Sync Environment**: `uv sync`
* **Run Server**: `uv run python app.py` (Runs on `http://0.0.0.0:8000` with debug enabled)
* **Environment Configuration**: Sourced from root `.env` or `airial_api/.env` via `python-dotenv`.

---

## 3. Services Port Reference

* `5173`: Vue 3 Vite Dev Server
* `8000`: Flask REST API
* `5432`: PostgreSQL 18
* `6379`: Valkey (Redis-compatible)
* `50051`: SpiceDB gRPC
