# NeutWeather API

A production-style weather forecasting application built with **FastAPI**, **PostgreSQL**, **Redis**, **Docker**, **Kubernetes**, and **GitHub Actions CI/CD**.

This project demonstrates how to build, containerize, test, and deploy a backend API with persistent storage, caching, secrets management, Kubernetes manifests, and automated Docker image publishing.

---

## Table of Contents

* [Project Overview](#project-overview)
* [Features](#features)
* [Architecture](#architecture)
* [Tech Stack](#tech-stack)
* [Project Structure](#project-structure)
* [Environment Variables](#environment-variables)
* [Run Locally](#run-locally)
* [Run with Docker Compose](#run-with-docker-compose)
* [Kubernetes Deployment](#kubernetes-deployment)
* [Ingress Access](#ingress-access)
* [API Endpoints](#api-endpoints)
* [CI/CD Pipeline](#cicd-pipeline)
* [Testing](#testing)
* [Troubleshooting](#troubleshooting)
* [Security Notes](#security-notes)
* [Future Improvements](#future-improvements)
* [Author](#author)

---

## Project Overview

**NeutWeather API** is a weather intelligence dashboard and backend API that allows users to search for weather forecasts by city.

The application integrates with an external weather provider through RapidAPI, stores user search activity and favorites in PostgreSQL, and uses Redis for caching weather responses to improve performance and reduce repeated API calls.

This project was built as a DevOps-focused application to practice:

* Docker containerization
* Docker Compose multi-service development
* PostgreSQL persistence
* Redis caching
* Kubernetes Deployments, StatefulSets, Services, ConfigMaps, Secrets, PVCs, and Ingress
* GitHub Actions CI/CD
* Health checks and deployment validation

---

## Features

* Weather forecast search by city
* City suggestions
* Favorites API
* Search history API
* PostgreSQL database integration
* Redis caching layer
* FastAPI automatic API documentation
* Static frontend served by FastAPI
* Dockerized application
* Docker Compose setup for local development
* Kubernetes manifests for local or cloud deployment
* Ingress-based access using a local domain
* GitHub Actions CI workflow
* Docker image build and push workflow

---

## Architecture

```text
User / Browser
      |
      v
Ingress Controller
      |
      v
Kubernetes Ingress
      |
      v
neutweather-service
      |
      v
FastAPI Pods
   |        |
   |        +----------------+
   |                         |
   v                         v
PostgreSQL Service       Redis Service
   |                         |
   v                         v
PostgreSQL StatefulSet   Redis Deployment
   |
   v
Persistent Volume Claim
```

---

## Tech Stack

### Backend

* Python 3.12
* FastAPI
* SQLAlchemy
* Pydantic
* Uvicorn

### Database

* PostgreSQL
* SQLAlchemy ORM

### Cache

* Redis

### DevOps

* Docker
* Docker Compose
* Kubernetes
* Minikube
* NGINX Ingress Controller
* GitHub Actions
* Docker Hub

### Testing

* Pytest
* FastAPI TestClient

---

## Project Structure

```text
Weather-forecasting-App/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── cd.yml
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   └── weather.py
├── k8s/
│   ├── 00-namespace.yaml
│   ├── 01-configmap.yaml
│   ├── 02-postgres-headless-service.yaml
│   ├── 03-postgres-statefulset.yaml
│   ├── 04-postgres-service.yaml
│   ├── 05-redis-deployment.yaml
│   ├── 06-redis-service.yaml
│   ├── 07-app-deployment.yaml
│   ├── 08-app-service.yaml
│   ├── 09-ingress.yaml
│   └── secret.example.yaml
├── static/
│   └── frontend files
├── tests/
│   └── test files
├── Dockerfile
├── compose.yaml
├── requirements.txt
├── pytest.ini
└── README.md
```

---

## Environment Variables

Create a local `.env` file in the project root.

Example:

```env
RAPIDAPI_KEY=your_rapidapi_key
RAPIDAPI_HOST=open-weather13.p.rapidapi.com

WEATHER_CITY_ENDPOINT=/city
WEATHER_FORECAST_ENDPOINT=/fivedaysforcast
WEATHER_LANGUAGE=EN

POSTGRES_DB=neutweather
POSTGRES_USER=neutuser
POSTGRES_PASSWORD=neutpassword123

DATABASE_URL=postgresql://neutuser:neutpassword123@db:5432/neutweather

REDIS_URL=redis://redis:6379/0
REDIS_CACHE_ENABLED=true
REDIS_KEY_PREFIX=neutweather
WEATHER_CACHE_TTL_SECONDS=600
WEATHER_COORDINATE_CACHE_TTL_SECONDS=86400
```

> Do not commit `.env` to GitHub.

---

## Run Locally

### 1. Clone the repository

```bash
git clone <repository-url>
cd Weather-forecasting-App
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create `.env`

```bash
cp .env.open-weather13.example .env
```

Then update the values inside `.env`.

### 5. Run the application

```bash
uvicorn app.main:app --reload
```

The application will be available at:

```text
http://localhost:8000
```

API documentation:

```text
http://localhost:8000/docs
```

---

## Run with Docker Compose

Build and start the full stack:

```bash
docker compose up --build
```

This starts:

* FastAPI application
* PostgreSQL database
* Redis cache

Check running containers:

```bash
docker compose ps
```

Test the application:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/cache/health
curl "http://localhost:8000/forecast?city=Cairo&days=3"
```

Stop the stack:

```bash
docker compose down
```

Stop and remove volumes:

```bash
docker compose down -v
```

---

## Kubernetes Deployment

This project includes Kubernetes manifests inside the `k8s/` directory.

### 1. Start Minikube

```bash
minikube start
```

### 2. Enable Ingress

```bash
minikube addons enable ingress
```

### 3. Create the namespace

```bash
kubectl apply -f k8s/00-namespace.yaml
```

### 4. Apply the ConfigMap

```bash
kubectl apply -f k8s/01-configmap.yaml
```

### 5. Create Kubernetes Secrets

Do not commit real secrets to GitHub.

Create the secret from your local `.env` file:

```bash
kubectl -n neutweather create secret generic neutweather-secrets \
  --from-literal=POSTGRES_PASSWORD="$(grep '^POSTGRES_PASSWORD=' .env | cut -d= -f2-)" \
  --from-literal=RAPIDAPI_KEY="$(grep '^RAPIDAPI_KEY=' .env | cut -d= -f2-)" \
  --dry-run=client -o yaml | kubectl apply -f -
```

Verify the secret:

```bash
kubectl get secret -n neutweather
```

### 6. Deploy PostgreSQL

```bash
kubectl apply -f k8s/02-postgres-headless-service.yaml
kubectl apply -f k8s/03-postgres-statefulset.yaml
kubectl apply -f k8s/04-postgres-service.yaml
```

Check PostgreSQL:

```bash
kubectl get pods -n neutweather
kubectl get pvc -n neutweather
```

### 7. Deploy Redis

```bash
kubectl apply -f k8s/05-redis-deployment.yaml
kubectl apply -f k8s/06-redis-service.yaml
```

Test Redis:

```bash
kubectl exec -it -n neutweather deployment/redis -- redis-cli ping
```

Expected output:

```text
PONG
```

### 8. Deploy the FastAPI application

```bash
kubectl apply -f k8s/07-app-deployment.yaml
kubectl apply -f k8s/08-app-service.yaml
```

Check the application pods:

```bash
kubectl get pods -n neutweather
```

### 9. Apply Ingress

```bash
kubectl apply -f k8s/09-ingress.yaml
```

Check Ingress:

```bash
kubectl get ingress -n neutweather
```

---

## Ingress Access

Get Minikube IP:

```bash
minikube ip
```

Edit `/etc/hosts`:

```bash
sudo nano /etc/hosts
```

Add:

```text
<minikube-ip> neutweather.local
```

Example:

```text
192.168.49.2 neutweather.local
```

Now access the application:

```text
http://neutweather.local
```

Test endpoints:

```bash
curl http://neutweather.local/health
curl http://neutweather.local/cache/health
curl "http://neutweather.local/forecast?city=Cairo&days=3"
```

---

## API Endpoints

### Health

```http
GET /health
```

Checks if the FastAPI application is running.

### Cache Health

```http
GET /cache/health
```

Checks Redis cache status.

### Cities

```http
GET /cities
```

Returns supported city suggestions.

### Forecast

```http
GET /forecast?city=Cairo&days=3
```

Returns weather forecast data for the requested city.

### Favorites

```http
GET /favorites
POST /favorites
PUT /favorites/{favorite_id}
DELETE /favorites/{favorite_id}
```

Manages favorite cities.

### Search History

```http
GET /search-history
POST /search-history
PUT /search-history/{history_id}
DELETE /search-history/{history_id}
```

Manages search history records.

---

## CI/CD Pipeline

This repository includes GitHub Actions workflows.

### CI Workflow

The CI workflow runs on code changes and performs:

* Checkout repository
* Set up Python
* Install dependencies
* Run tests with Pytest
* Build Docker image
* Run the container
* Test the `/health` endpoint

### CD Workflow

The CD workflow builds and pushes the Docker image to Docker Hub.

Required GitHub Actions secrets:

```text
DOCKER_USERNAME
DOCKER_PASSWORD
RAPIDAPI_KEY
RAPIDAPI_HOST
POSTGRES_PASSWORD
```

Recommended future improvement:

```text
GitHub Actions → Docker Hub → Kubernetes cluster deployment
```

---

## Testing

Run tests locally:

```bash
pytest -q
```

Run tests with verbose output:

```bash
pytest -v
```

Current tests include health endpoint validation.

Recommended additional tests:

* Forecast endpoint with mocked provider response
* Redis cache health
* Favorites CRUD
* Search history CRUD
* Database connection behavior
* Error handling for missing or invalid cities

---

## Troubleshooting

### Pod is not running

```bash
kubectl get pods -n neutweather
kubectl describe pod <pod-name> -n neutweather
kubectl logs <pod-name> -n neutweather
```

### Check all Kubernetes resources

```bash
kubectl get all -n neutweather
```

### Check Persistent Volume Claim

```bash
kubectl get pvc -n neutweather
```

`Bound` means the PostgreSQL storage is attached successfully.

### Check ConfigMap

```bash
kubectl describe configmap neutweather-config -n neutweather
```

### Check Secret keys

```bash
kubectl describe secret neutweather-secrets -n neutweather
```

### Restart the FastAPI deployment

```bash
kubectl rollout restart deployment/neutweather-app -n neutweather
```

### Check rollout status

```bash
kubectl rollout status deployment/neutweather-app -n neutweather
```

### PostgreSQL password issue

If PostgreSQL was initialized with old credentials, changing the Kubernetes Secret will not update the existing database user automatically.

For local testing only, reset PostgreSQL by deleting the StatefulSet and PVC:

```bash
kubectl delete statefulset postgres -n neutweather
kubectl delete pvc postgres-data-postgres-0 -n neutweather
kubectl apply -f k8s/03-postgres-statefulset.yaml
```

Warning: deleting the PVC removes the local PostgreSQL data.

---

## Security Notes

* Do not commit `.env`
* Do not commit real Kubernetes Secret files
* Use `secret.example.yaml` only as a template
* Store production secrets in:

  * GitHub Actions Secrets
  * Kubernetes Secrets
  * External secret managers such as AWS Secrets Manager, Azure Key Vault, or Google Secret Manager
* Keep database services internal using `ClusterIP`
* Expose only the application through Ingress

---

## Future Improvements

* Add Alembic database migrations
* Add more automated tests
* Add Kubernetes resource limits and requests
* Add Horizontal Pod Autoscaler
* Add production-grade logging
* Add Prometheus and Grafana monitoring
* Add GitHub Actions deployment to Kubernetes
* Add HTTPS/TLS support for Ingress
* Add Helm chart for easier deployment
* Add cloud deployment using AWS EKS or Azure AKS

---

## Author

Built by **Ahmed Omar**.

DevOps-focused project demonstrating backend development, containerization, Kubernetes deployment, caching, persistence, and CI/CD automation.
Updated from local terminal
