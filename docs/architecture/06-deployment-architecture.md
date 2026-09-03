# 06: Deployment Architecture

## 1. Environments
- **Development:** Local Docker Compose.
- **Staging:** AWS EC2 / Azure VM single-node Docker Compose (MVP Baseline).
- **Production:** Managed Kubernetes (EKS/AKS) (Target Architecture).

## 2. Containerization Topology (MVP)
```yaml
services:
  api:
    image: enterprise-api:latest
    deploy:
      replicas: 2
  worker-media:
    image: enterprise-worker:latest
    command: celery -A core worker -Q media
  worker-ai:
    image: enterprise-worker:latest
    command: celery -A core worker -Q ai
    deploy:
      resources:
        reservations:
          devices: [{driver: nvidia, count: 1, capabilities: [gpu]}]
  postgres:
    image: pgvector/pgvector:pg16
  redis:
    image: redis:7-alpine
  minio:
    image: minio/minio
```

## 3. Resource Allocations
- **API:** 2 CPU, 4GB RAM.
- **AI Worker (ASR):** 4 CPU, 16GB RAM, 1x NVIDIA T4 or L4 GPU (24GB VRAM).
- **Media Worker:** 2 CPU, 4GB RAM.
- **DB:** 4 CPU, 16GB RAM, NVMe SSD.

## 4. Networking & Observability
- **Ingress:** Traefik Reverse Proxy, TLS termination (Let's Encrypt).
- **Logging:** JSON structured logs pushed to ELK/Loki.
- **Metrics:** Prometheus endpoints on FastAPI and Celery.
