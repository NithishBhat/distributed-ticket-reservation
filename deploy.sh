#!/bin/bash
set -e

DB_PASSWORD="${DB_PASSWORD:-ChangeMe123!}"
REGION="us-east-1"

# ── 1. Terraform ─────────────────────────────
echo ">>> Creating infrastructure..."
cd "$(dirname "$0")/terraform"
terraform init -input=false
terraform apply -var="db_password=$DB_PASSWORD" -auto-approve

ALB=$(terraform output -raw alb_dns_name)
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)

# ── 2. Build & push Docker images ────────────
echo ">>> Building and pushing Docker images..."
ECR="$ACCOUNT.dkr.ecr.$REGION.amazonaws.com"
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin "$ECR"

cd ../services/ticket-service
docker build -t "$ECR/ticket-service:latest" .
docker push "$ECR/ticket-service:latest"

cd ../order-service
docker build -t "$ECR/order-service:latest" .
docker push "$ECR/order-service:latest"

# ── 3. Deploy to ECS ────────────────────────
echo ">>> Deploying to ECS..."
aws ecs update-service --region $REGION --cluster ticket-cluster --service ticket-service --force-new-deployment > /dev/null
aws ecs update-service --region $REGION --cluster ticket-cluster --service order-service --force-new-deployment > /dev/null

echo ">>> Waiting for services to stabilize (~2 min)..."
aws ecs wait services-stable --region $REGION --cluster ticket-cluster --services ticket-service order-service

# ── 4. Verify ────────────────────────────────
echo ""
echo "========================================="
echo "  DEPLOY COMPLETE"
echo "  ALB: http://$ALB"
echo "========================================="
echo ""
echo "Verifying..."
curl -s "http://$ALB/tickets" | python3 -m json.tool 2>/dev/null || curl -s "http://$ALB/tickets"
echo ""
