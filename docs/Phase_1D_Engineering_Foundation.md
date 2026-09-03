# Phase 1D: Engineering Foundation

## 1. Repository Layout

```text
.
├── .github/
│   └── workflows/
│       └── ci.yml                  # GitHub Actions CI pipeline
├── deploy/
│   ├── docker/
│   │   ├── Dockerfile.api          # FastAPI runtime image
│   │   └── Dockerfile.worker       # Celery media/AI worker image
│   └── init-db.sql                 # Baseline DB setup & extensions
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application entry point
│   │   ├── core/                   # Security, config, DB connections
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── logging.py
│   │   ├── api/                    # API Routers
│   │   │   └── v1/
│   │   │       ├── auth.py
│   │   │       ├── meetings.py
│   │   │       ├── chat.py
│   │   │       └── admin.py
│   │   ├── services/               # Domain service logic
│   │   └── models/                 # SQLAlchemy models / Pydantic schemas
│   ├── workers/                    # Celery task definitions
│   │   ├── celery_app.py
│   │   └── tasks/
│   ├── alembic/                    # Database migration scripts
│   ├── pyproject.toml              # Ruff, Mypy, and Pytest configuration
│   └── requirements.txt
├── frontend/                       # Next.js web application
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── tsconfig.json
├── docs/                           # Architecture, specs, ADRs
│   └── architecture.md
├── .env.example                    # Template environment configuration
├── docker-compose.yml              # Local orchestration stack
└── Makefile                        # Single-command developer targets
```

---

## 2. Docker Compose Infrastructure

```yaml
version: '3.8'

x-environment: &common-env
  ENVIRONMENT: local
  POSTGRES_USER: ${POSTGRES_USER:-app_user}
  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-app_password}
  POSTGRES_DB: ${POSTGRES_DB:-platform_db}
  POSTGRES_HOST: db
  POSTGRES_PORT: 5432
  DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-app_user}:${POSTGRES_PASSWORD:-app_password}@db:5432/${POSTGRES_DB:-platform_db}
  REDIS_URL: redis://redis:6379/0
  MINIO_ENDPOINT: minio:9000
  MINIO_ROOT_USER: ${MINIO_ROOT_USER:-minioadmin}
  MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-minioadmin}

services:
  db:
    image: pgvector/pgvector:pg16
    container_name: platform_db
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-app_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-app_password}
      POSTGRES_DB: ${POSTGRES_DB:-platform_db}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./deploy/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-app_user} -d ${POSTGRES_DB:-platform_db}"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: platform_redis
    restart: always
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio:RELEASE.2024-01-18T22-51-28Z
    container_name: platform_minio
    restart: always
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-minioadmin}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-minioadmin}
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - miniodata:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 10s
      timeout: 5s
      retries: 3

  api:
    build:
      context: ./backend
      dockerfile: ../deploy/docker/Dockerfile.api
    container_name: platform_api
    restart: always
    environment: *common-env
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy

  worker:
    build:
      context: ./backend
      dockerfile: ../deploy/docker/Dockerfile.worker
    container_name: platform_worker
    restart: always
    environment: *common-env
    command: celery -A workers.celery_app worker --loglevel=info -c 4
    volumes:
      - ./backend:/app
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

volumes:
  pgdata:
  miniodata:
```

---

## 3. Database Scaffolding & Vector Setup

```sql
-- deploy/init-db.sql
-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Tenants Table
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Users Table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Meetings Table
CREATE TABLE meetings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    created_by_user_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'UPLOADED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Transcripts Table
CREATE TABLE transcripts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id UUID UNIQUE NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    language VARCHAR(10) DEFAULT 'en',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Transcript Chunks & Embeddings Table
CREATE TABLE transcript_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transcript_id UUID NOT NULL REFERENCES transcripts(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    speaker_label VARCHAR(50),
    start_time_ms INT,
    end_time_ms INT,
    embedding vector(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_meetings_tenant ON meetings(tenant_id);
CREATE INDEX idx_chunks_transcript ON transcript_chunks(transcript_id);

-- Vector Similarity Search Index (HNSW for L2 distance / Cosine)
CREATE INDEX idx_chunks_embedding_hnsw 
ON transcript_chunks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

---

## 4. FastAPI Modular Application Skeleton

```python
# backend/app/main.py
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Setup Structured Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("platform_api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Initializing DB connection pools and Redis client...")
    yield
    # Shutdown logic
    logger.info("Closing active connection pools...")

app = FastAPI(
    title="Enterprise Meeting & Organizational Intelligence Platform API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error processing request {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error occurred."},
    )

# Healthcheck
@app.get("/healthz", status_code=status.HTTP_200_OK, tags=["System"])
async def healthcheck():
    return {"status": "ok"}

# Router Stubs
from fastapi import APIRouter

auth_router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])
meetings_router = APIRouter(prefix="/api/v1/meetings", tags=["Meetings"])
chat_router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])
admin_router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])

@auth_router.post("/login")
async def login():
    return {"message": "login endpoint"}

@meetings_router.get("/")
async def list_meetings():
    return []

@chat_router.post("/query")
async def chat_query():
    return {"response": "rag query response"}

@admin_router.get("/metrics")
async def get_metrics():
    return {"metrics": {}}

# Register Routers
app.include_router(auth_router)
app.include_router(meetings_router)
app.include_router(chat_router)
app.include_router(admin_router)
```

---

## 5. Development Workflow & CI/CD Skeleton

### Local Developer Automation (`Makefile`)

```makefile
.PHONY: dev down test lint format

dev:
	docker compose up --build -d
	@echo "Services running. API at http://localhost:8000/docs, MinIO Console at http://localhost:9001"

down:
	docker compose down -v

test:
	docker compose exec api pytest -v

lint:
	docker compose exec api ruff check .
	docker compose exec api mypy .

format:
	docker compose exec api ruff format .
```

### GitHub Actions CI (`.github/workflows/ci.yml`)

```yaml
name: Continuous Integration

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U test_user -d test_db"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 5

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install ruff mypy pytest pytest-asyncio httpx -r backend/requirements.txt

      - name: Run Linting and Formatting Check
        run: |
          ruff check backend/
          ruff format --check backend/

      - name: Run Type Checker
        run: |
          mypy backend/app

      - name: Execute Pytest
        env:
          DATABASE_URL: postgresql+asyncpg://test_user:test_password@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379/0
        run: |
          pytest backend/ -v
