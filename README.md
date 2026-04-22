# 🛒 E-Commerce Platform — Microservices on Kubernetes

A cloud-native e-commerce backend built on microservices, containerised with Docker,
orchestrated on Kubernetes, and deployed via a full CI/CD pipeline.

## Services
| Service              | Port | Stack            |
|----------------------|------|------------------|
| api-gateway          | 80   | NGINX            |
| user-service         | 3001 | Python/FastAPI   |
| product-service      | 3002 | Python/FastAPI   |
| order-service        | 3003 | Go/Gin           |
| notification-service | 3004 | Node.js          |

## Quick Start (Local)
```bash
cp services/user-service/.env.example services/user-service/.env
docker compose up --build
```

## Deploy to Kubernetes
```bash
helm upgrade --install ecommerce ./infra/helm/ecommerce \
  --namespace ecommerce --create-namespace \
  -f infra/helm/ecommerce/values.dev.yaml
```

## Tech Stack
Docker · Kubernetes · Helm · GitHub Actions · Prometheus · Grafana · PostgreSQL · RabbitMQ
