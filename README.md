# NeutWeather API — AWS EKS DevOps Project

NeutWeather is a production-style weather forecasting API built with FastAPI and deployed on Kubernetes using AWS EKS.

This project demonstrates a complete DevOps workflow, starting from application containerization, CI/CD, Kubernetes manifests, AWS ECR image hosting, EKS deployment, persistent storage, Ingress exposure through an AWS Application Load Balancer, and Infrastructure as Code using Terraform.

---

## Project Overview

NeutWeather provides weather forecast data through a FastAPI backend and stores application-related data using PostgreSQL.

The goal of this project is not only to build an API, but to simulate a real-world DevOps deployment workflow using modern cloud-native tools.

---

## Tech Stack

### Application

* Python
* FastAPI
* PostgreSQL
* Redis
* Docker
* Docker Compose

### DevOps & Cloud

* AWS EKS
* AWS ECR
* AWS ALB
* AWS EBS
* AWS IAM
* Kubernetes
* Helm
* Terraform
* GitHub Actions

---

## Architecture

```text
User
  |
  v
AWS Application Load Balancer
  |
  v
Kubernetes Ingress
  |
  v
Kubernetes Service
  |
  v
FastAPI Application Pods
  |
  |------ PostgreSQL StatefulSet + EBS Volume
  |
  |------ Redis Deployment
```

---

## Main Features

* FastAPI weather forecasting API
* Dockerized application
* PostgreSQL database integration
* Redis service inside Kubernetes
* Kubernetes manifests for deployment
* Persistent database storage using EBS
* AWS ECR image repository
* AWS EKS cluster deployment
* AWS Load Balancer Controller integration
* Public access through AWS Application Load Balancer
* Terraform infrastructure code for AWS resources
* GitHub Actions workflow for CI/CD

---

## Kubernetes Resources

The application is deployed using Kubernetes manifests located in the `k8s/` directory.

```text
k8s/
├── 00-namespace.yaml
├── 01-configmap.yaml
├── 02-postgres-headless-service.yaml
├── 03-postgres-statefulset.yaml
├── 04-postgres-service.yaml
├── 05-redis-deployment.yaml
├── 06-redis-service.yaml
├── 07-app-deployment.yaml
├── 08-app-service.yaml
├── 09-ingress.yaml
└── secret.example.yaml
```

### Kubernetes Components

* Namespace for resource isolation
* ConfigMap for non-sensitive configuration
* Secret example file for sensitive environment variables
* PostgreSQL StatefulSet for persistent database workloads
* Redis Deployment for caching
* FastAPI Deployment for the application
* ClusterIP Service for internal routing
* Ingress resource for external access through ALB

---

## AWS Deployment

The application was deployed on AWS using:

* AWS EKS for Kubernetes orchestration
* AWS ECR for Docker image storage
* AWS EBS for PostgreSQL persistent storage
* AWS Load Balancer Controller for Ingress
* AWS ALB for public traffic routing
* AWS IAM roles and policies for secure AWS service access

---

## Docker Image

The application image is built locally and pushed to AWS ECR.

Example:

```bash
docker build -t neutweather .
docker tag neutweather:latest <aws-account-id>.dkr.ecr.<region>.amazonaws.com/neutweather:latest
docker push <aws-account-id>.dkr.ecr.<region>.amazonaws.com/neutweather:latest
```

---

## Kubernetes Deployment

Apply the Kubernetes manifests:

```bash
kubectl apply -f k8s/
```

Check running resources:

```bash
kubectl get all -n neutweather
```

Check Ingress:

```bash
kubectl get ingress -n neutweather
```

Check application logs:

```bash
kubectl logs -n neutweather deployment/neutweather-app
```

---

## AWS Load Balancer Controller

The project uses AWS Load Balancer Controller to provision an AWS Application Load Balancer from a Kubernetes Ingress resource.

The Ingress resource uses annotations such as:

```yaml
alb.ingress.kubernetes.io/scheme: internet-facing
alb.ingress.kubernetes.io/target-type: ip
alb.ingress.kubernetes.io/listen-ports: '[{"HTTP":80}]'
alb.ingress.kubernetes.io/healthcheck-path: /health
```

---

## Terraform Infrastructure

Terraform code is included in the `terraform/` directory to define AWS infrastructure as code.

```text
terraform/
├── versions.tf
├── provider.tf
├── variables.tf
├── main.tf
├── outputs.tf
└── terraform.tfvars.example
```

### Terraform Resources

The Terraform configuration is designed to provision:

* VPC
* Public subnets
* Private subnets
* Internet Gateway
* NAT Gateway
* ECR Repository
* EKS Cluster
* EKS Managed Node Group
* IAM roles and policies
* Security Groups

### Terraform Commands

Initialize Terraform:

```bash
terraform init
```

Format Terraform files:

```bash
terraform fmt
```

Validate configuration:

```bash
terraform validate
```

Preview infrastructure changes:

```bash
terraform plan
```

Apply infrastructure:

```bash
terraform apply
```

Destroy infrastructure:

```bash
terraform destroy
```

---

## Environment Variables

Create a `.env` file locally for development.

Example:

```env
RAPIDAPI_KEY=your_api_key
RAPIDAPI_HOST=your_api_host
POSTGRES_DB=weather_db
POSTGRES_USER=app_user
POSTGRES_PASSWORD=your_password
DATABASE_URL=postgresql://app_user:your_password@db:5432/weather_db
```

For Kubernetes, use `secret.example.yaml` as a template and create real secrets safely.

Do not commit real secrets to GitHub.

---

## Local Development

Run the application locally using Docker Compose:

```bash
docker compose up --build
```

Open the API:

```text
http://localhost:8000
```

Open API documentation:

```text
http://localhost:8000/docs
```

Health check:

```text
http://localhost:8000/health
```

---

## CI/CD

GitHub Actions is used to automate:

* Installing dependencies
* Running tests
* Building the Docker image
* Validating the application health endpoint
* Preparing the image for deployment

---

## Important Notes

This project was built as a DevOps learning and portfolio project.

It demonstrates practical experience with:

* Containerization
* Kubernetes deployments
* Stateful workloads
* Cloud networking
* AWS IAM integration
* Load balancing
* Persistent storage
* Infrastructure as Code
* CI/CD automation
* Cloud troubleshooting

---

## Lessons Learned

During this project, several real-world DevOps issues were handled, including:

* Kubernetes Service configuration errors
* Ingress YAML structure issues
* AWS Load Balancer Controller IAM permission errors
* EBS CSI Driver setup for persistent volumes
* PostgreSQL password mismatch after Kubernetes Secret updates
* HTTP vs HTTPS behavior on mobile browsers
* EKS and kubectl context management
* Terraform plan validation before applying infrastructure

---

## Future Improvements

* Add HTTPS using ACM and a custom domain
* Add Route 53 DNS records
* Add Terraform remote state using S3 and DynamoDB
* Automate AWS Load Balancer Controller installation with Terraform and Helm
* Add monitoring with Prometheus and Grafana
* Add centralized logging
* Add separate environments for dev, staging, and production
* Add GitHub Actions workflow for Terraform plan and apply

---

## Author

Built by Ahmed Omar as a practical DevOps and Cloud Engineering project.

GitHub: https://github.com/AhmedKarimo
