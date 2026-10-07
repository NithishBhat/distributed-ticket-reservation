#!/bin/bash
set -e

# ── Configuration ────────────────────────────────────────
DB_PASSWORD="${DB_PASSWORD:-ChangeMe123!}"
REGION="us-east-1"
USERS=200
SPAWN_RATE=20
RUN_TIME="5m"
ORDER_SERVICE_COUNT=4
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
TERRAFORM_DIR="$PROJECT_DIR/terraform"
LOCUST_FILE="$PROJECT_DIR/locust/locustfile.py"

# ── Low contention: spread across all 4 tickets ─────────
unset LOCUST_HOT_TICKET

echo "========================================"
echo "  Experiment 2 — Low Contention Test"
echo "  Users: $USERS  Spawn rate: $SPAWN_RATE  Duration: $RUN_TIME"
echo "  LOCUST_HOT_TICKET: (unset — random across tickets 1-4)"
echo "========================================"

# ── Get ALB URL ──────────────────────────────────────────
cd "$TERRAFORM_DIR"
ALB=$(terraform output -raw alb_dns_name)
HOST="http://$ALB"
echo "ALB: $HOST"

# ── Helper: get DB connection info from terraform ────────
# rds_endpoint includes port (e.g. "host:5432"), strip it
RDS_ENDPOINT=$(terraform output -raw rds_endpoint 2>/dev/null || echo "")
DB_HOST="${RDS_ENDPOINT%%:*}"
if [ -z "$DB_HOST" ]; then
    echo ""
    echo "NOTE: Could not get rds_endpoint from terraform output."
    echo "You will need to reset the DB manually between runs:"
    echo "  UPDATE tickets SET tickets_reserved = 0;"
    echo "  DELETE FROM orders;"
    echo ""
fi

reset_db() {
    if [ -n "$DB_HOST" ]; then
        echo ">>> Resetting DB..."
        PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U postgres -d ticketdb -c \
            "UPDATE tickets SET tickets_reserved = 0; DELETE FROM orders;" 2>/dev/null || \
            echo "WARNING: Auto-reset failed. Please reset DB manually."
    else
        echo ""
        echo ">>> Please reset the DB now (UPDATE tickets SET tickets_reserved = 0; DELETE FROM orders;)"
        read -p "Press Enter when done..."
    fi
}

# ── Helper: verify no overselling ────────────────────────
verify_db() {
    local label=$1
    if [ -n "$DB_HOST" ]; then
        echo ">>> DB state after $label:"
        PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U postgres -d ticketdb -c \
            "SELECT id, name, quantity, tickets_reserved FROM tickets;" 2>/dev/null || \
            echo "WARNING: Could not query DB automatically."
        PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U postgres -d ticketdb -c \
            "SELECT COUNT(*) AS total_orders FROM orders WHERE status = 'confirmed';" 2>/dev/null || true
    else
        echo ">>> Please verify DB state (no overselling) for $label"
    fi
}

# ════════════════════════════════════════════════════════
#  Run 1: Pessimistic Locking
# ════════════════════════════════════════════════════════
echo ""
echo "──────────────────────────────────────"
echo "  Run 1: PESSIMISTIC locking"
echo "──────────────────────────────────────"

reset_db

cd "$TERRAFORM_DIR"
terraform apply -var="db_password=$DB_PASSWORD" \
    -var="order_service_count=$ORDER_SERVICE_COUNT" \
    -var="lock_strategy=pessimistic" -auto-approve

echo ">>> Waiting for ECS to stabilize..."
aws ecs wait services-stable --region $REGION --cluster ticket-cluster --services order-service

echo ">>> Running Locust (pessimistic, low contention)..."
python3 -m locust -f "$LOCUST_FILE" --host="$HOST" \
    --users $USERS --spawn-rate $SPAWN_RATE --run-time $RUN_TIME \
    --headless \
    --csv="$SCRIPT_DIR/pessimistic" \
    2>&1 | tee "$SCRIPT_DIR/pessimistic_log.txt"

verify_db "pessimistic"

# ════════════════════════════════════════════════════════
#  Run 2: Optimistic Locking
# ════════════════════════════════════════════════════════
echo ""
echo "──────────────────────────────────────"
echo "  Run 2: OPTIMISTIC locking"
echo "──────────────────────────────────────"

reset_db

cd "$TERRAFORM_DIR"
terraform apply -var="db_password=$DB_PASSWORD" \
    -var="order_service_count=$ORDER_SERVICE_COUNT" \
    -var="lock_strategy=optimistic" -auto-approve

echo ">>> Waiting for ECS to stabilize..."
aws ecs wait services-stable --region $REGION --cluster ticket-cluster --services order-service

echo ">>> Running Locust (optimistic, low contention)..."
python3 -m locust -f "$LOCUST_FILE" --host="$HOST" \
    --users $USERS --spawn-rate $SPAWN_RATE --run-time $RUN_TIME \
    --headless \
    --csv="$SCRIPT_DIR/optimistic" \
    2>&1 | tee "$SCRIPT_DIR/optimistic_log.txt"

verify_db "optimistic"

# ════════════════════════════════════════════════════════
#  Done
# ════════════════════════════════════════════════════════
echo ""
echo "========================================"
echo "  Low contention test complete!"
echo "  CSV data saved to: $SCRIPT_DIR/"
echo "    pessimistic_stats.csv"
echo "    pessimistic_stats_history.csv"
echo "    optimistic_stats.csv"
echo "    optimistic_stats_history.csv"
echo "========================================"
