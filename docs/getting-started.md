# Getting Started with Airial

This guide walks human developers through setting up, configuring, and running the Airial platform locally.

---

## Prerequisites

* **Operating System**: Linux (recommended) or macOS (Apple Silicon or Intel).
* **Container Engine**:
  * [Podman](https://podman.io/) (v5.0+) with `podman-compose` **OR**
  * [Docker](https://www.docker.com/) (v25+) with `docker compose`
* **Host Tooling (optional for running outside containers)**:
  * [Python 3.13+](https://www.python.org/) with [uv](https://docs.astral.sh/uv/)
  * [Node.js 22+](https://nodejs.org/) with `npm`

---

## 1. Environment Configuration (`.env`)

Copy or create a `.env` file in the root of the repository. All services (containers, API, and frontend) source their configuration from this file.

### Environment Variables Reference

#### Database (PostgreSQL 18)
| Variable | Description | Typical Dev Value |
| :--- | :--- | :--- |
| `DB_NAME` | Database name | `testing` |
| `DB_USER` | Database role username | `pronghorn_count` |
| `DB_PASS` | Database password | `<your-password>` |
| `DB_HOST` | Hostname (`prong_gres` in containers, `localhost` on host) | `prong_gres` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `DB_SSL` | Enable SSL for database connections | `false` |
| `DB_SSL_MODE` | PostgreSQL SSL verification mode | `disable` / `verify-full` |
| `DB_SSL_ROOT_CERT_PATH` | Path to root CA cert when using `verify-full` | `""` |

#### API & Session Security
| Variable | Description | Typical Dev Value |
| :--- | :--- | :--- |
| `SECRET_KEY` | Cryptographic key for Flask session signing | `<long-random-string>` |
| `ORIGIN_URL` | Allowed CORS origin for frontend | `http://localhost:5173` |
| `APPLICATION_URL` | Base application URL (used in production) | `http://localhost:5173` |
| `NUM_API_WORKERS` | Gunicorn worker processes (production WSGI) | `3` |
| `SESSION_COOKIE_SAMESITE` | Cookie SameSite attribute | `Lax` |
| `SESSION_COOKIE_SECURE` | Set `true` if serving over HTTPS | `false` |
| `SESSION_PERMANENT` | Persist session cookies | `true` |
| `SESSION_USE_SIGNER` | Cryptographically sign session cookies | `true` |

#### Cache & Sessions (Valkey)
| Variable | Description | Typical Dev Value |
| :--- | :--- | :--- |
| `VALKEY_HOST` | Hostname for Valkey container | `prong_dev_valkey` |
| `VALKEY_PASS` | Password required by Valkey server | `<your-valkey-pass>` |
| `SESSION_REDIS` | Redis connection URI for Flask-Session (DB 0) | `redis://:<pass>@valkey:6379/0` |
| `CACHE_REDIS` | Redis connection URI for Flask-Caching (DB 1) | `redis://:<pass>@valkey:6379/1` |

#### Object Storage (S3 / Ceph)
| Variable | Description | Typical Dev Value |
| :--- | :--- | :--- |
| `AWS_ENDPOINT_URL_S3` | S3 API endpoint (ARCC Ceph Gateway or AWS S3) | `https://s3.arcc.uwyo.edu` |
| `AWS_ACCESS_KEY_ID` | S3 access key ID | `<your-access-key>` |
| `AWS_SECRET_ACCESS_KEY` | S3 secret access key | `<your-secret-key>` |
| `BUCKET_NAME` | S3 bucket containing aerial imagery and crops | `pronghorn-count-test` |

#### SpiceDB (ReBAC Permissions)
| Variable | Description | Typical Dev Value |
| :--- | :--- | :--- |
| `SPICE_URL` | SpiceDB gRPC endpoint | `prong_spicedb:50051` |
| `SPICEDB_GRPC_PRESHARED_KEY` | Preshared key for gRPC authentication | `<your-preshared-key>` |
| `SPICEDB_GRPC_LOGLEVEL` | Logging level for SpiceDB (`debug`, `info`, `warn`) | `debug` |
| `SPICEDB_DATASTORE_ENGINE` | Storage engine (`memory` or `postgres`) | `memory` |
| `SPICEDB_DATASTORE_CONN_URI` | Postgres connection string if datastore is `postgres` | `postgres://...` |
| `SPICE_TLS` | Enable TLS for SpiceDB gRPC channel | `false` |

#### Web App (Vue 3 Frontend)
| Variable | Description | Typical Dev Value |
| :--- | :--- | :--- |
| `VITE_API_URL` | Base API URL called by frontend | `http://localhost:8000/api/v1` |

#### OAuth 2.0 Authentication
| Variable | Description | Typical Dev Value |
| :--- | :--- | :--- |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID for user login | `<client-id>.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | `<client-secret>` |

---

## 2. Running the System

### Option A: Standard Local Development (with Sample Dataset)

If you are developing features or testing workflows with pre-populated sample surveys and annotations:

```bash
# Using Podman
podman compose -f development.compose.yml up -d

# Or using Docker
docker compose -f development.compose.yml up -d
```

This starts:
1. **PostgreSQL 18** (`prong_gres` on port `5432`): Auto-restores sample data from `local_db/pct_b`.
2. **SpiceDB** (`prong_spicedb` on port `50051`): Restores permissions from `local_db/backup.zed`.
3. **Valkey 8.1** (`prong_dev_valkey` on port `6379`): Redis-compatible caching and session store.
4. **Flask API** (`prong_dev_api` on port `8000`): Flask debug server with code mounted live from `./airial_api`.
5. **Vue 3 Web App** (`prong_dev_webapp` on port `5173`): Vite dev server with hot-reload mounted live from `./generator_web_app/src`.

### Option B: Clean Bootstrap Mode (Empty Schema)

If you need to initialize a fresh environment from scratch:

```bash
podman compose -f bootstrap-dev.compose.yml up -d
```

This runs `local_db/bootstrap.sh` with `docs/database/schemas/airial1-1.sql`, writes the fresh SpiceDB schema from `schema.zed`, and allows you to run through the initial bootstrap wizard at `http://localhost:5173/setup`.

---

## 3. Running Services Locally on the Host

For rapid debugging with IDE breakpoints or fast iteration, you can run the supporting services (Postgres, SpiceDB, Valkey) in containers and run the API / Web App directly on your host machine:

### 1. Start Infrastructure Containers
```bash
podman compose -f development.compose.yml up -d db valkey spicedb spicedb-restore
```

### 2. Run the Backend API
```bash
cd airial_api

# Install dependencies using uv
uv sync

# Run the Flask development server
uv run python app.py
```
API runs at `http://localhost:8000`.

### 3. Run the Frontend Web App
```bash
cd generator_web_app

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```
Web app runs at `http://localhost:5173`.

---

## 4. Helpful Commands

```bash
# View running containers
podman compose -f development.compose.yml ps

# Tail logs for a specific service
podman logs -f prong_dev_api
podman logs -f prong_gres
podman logs -f prong_spicedb
podman logs -f prong_dev_valkey

# Run frontend TypeScript type checking
cd generator_web_app && npm run type-check

# Stop all containers
podman compose -f development.compose.yml down
```
