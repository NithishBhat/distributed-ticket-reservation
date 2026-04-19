# Distributed Ticket Reservation System

A distributed ticket reservation platform built to study concurrency control strategies under high load.

## Why a Ticket System?

Ticket reservation is a natural fit for studying distributed systems challenges. A single popular event can attract thousands of concurrent buyers all competing for the same limited inventory. This creates real pressure on the system to handle:

- **High concurrency** -- many users placing orders at the same time
- **Data consistency** -- the system must never sell more tickets than available (no overbooking)
- **Idempotency** -- network retries should not result in duplicate orders
- **Fault tolerance** -- the system should recover gracefully when instances go down

These are the same challenges faced by production systems at Ticketmaster, StubHub, and similar platforms, making it an ideal testbed for comparing different concurrency control mechanisms in a distributed environment.

## Architecture

Two Go microservices deployed on AWS Fargate behind an Application Load Balancer:

```
                    Internet
                       |
              ┌────────┴────────┐
              │  ALB (port 80)  │
              └───┬─────────┬───┘
                  │         │
        /tickets, │         │ /orders
        /validate │         │
          ┌───────┴──┐  ┌───┴────────┐
          │  Ticket  │  │   Order    │
          │  Service │  │  Service   │
          │  (8080)  │  │  (8081)    │
          └────┬─────┘  └──┬────────┘
               │           │
        ┌──────┴───────────┴──────┐
        │   PostgreSQL (RDS)      │
        │   - tickets table       │
        │   - orders table        │
        │   - CHECK constraint    │
        └─────────────────────────┘
               │
        ┌──────┴──────────────────┐
        │   Redis (ElastiCache)   │
        │   - read caching        │
        │   - distributed locks   │
        └─────────────────────────┘
```

- **Ticket Service** -- read-only service for browsing tickets, with optional Redis caching
- **Order Service** -- handles reservations with configurable locking strategy

Both services run as Fargate tasks in private subnets with configurable replica counts for scaling experiments.

## Concurrency Control Strategies

The core of this project is comparing three locking strategies for preventing overbooking:

### Pessimistic Locking
Uses `SELECT FOR UPDATE` to lock the ticket row during the entire transaction. Other requests for the same ticket wait in line. Safe but can bottleneck under high contention.

### Optimistic Locking
No explicit lock. Performs a conditional `UPDATE ... WHERE tickets_reserved + qty <= quantity`. If the update affects 0 rows, another request got there first. Retries up to 3 times with exponential backoff and jitter. Faster under low contention but retry rate climbs under load.

### Redis Distributed Locking
Acquires a distributed lock via Redis `SetNX` before touching the database. Uses UUID-based ownership and a 3-second TTL to prevent deadlocks. Up to 10 retries with short spin waits.

All three strategies are backed by a PostgreSQL `CHECK` constraint (`tickets_reserved <= quantity`) as a final safety net.

## Database Schema

```sql
tickets  -- id, name, quantity, tickets_reserved, created_at
         -- CHECK (tickets_reserved <= quantity)

orders   -- order_id, ticket_id, idempotency_key, quantity, status, created_at
         -- UNIQUE on idempotency_key (prevents duplicate orders on retry)
```

## Experiments

We ran three experiments using [Locust](https://locust.io/) for load generation:

| Experiment | What We Varied | What We Measured |
|---|---|---|
| **1. Auto-Scaling** | Order service replicas (1, 2, 4, 8) | Throughput, p50/p95/p99 latency, error rate |
| **2. Locking Strategies** | Pessimistic vs. Optimistic vs. Redis under hot-ticket contention | Throughput, latency, retry/conflict rates |
| **3. Failure Recovery** | Killed ECS tasks mid-test | Recovery time, data integrity |

After every run we validated that no overbooking occurred:
```sql
SELECT id, quantity, tickets_reserved FROM tickets WHERE tickets_reserved > quantity;
-- Expected: 0 rows
```

## Tech Stack

| Component | Technology |
|---|---|
| Services | Go 1.25 |
| Database | PostgreSQL 15 (RDS) |
| Cache / Locks | Redis 7.1 (ElastiCache) |
| Infrastructure | Terraform, AWS (ECS Fargate, ALB, VPC) |
| Containers | Docker |
| Load Testing | Python / Locust |

## Getting Started

### Prerequisites
- AWS credentials configured
- Terraform installed
- Docker installed

### Deploy
```bash
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...

bash deploy.sh
```
The script provisions all AWS infrastructure, builds and pushes Docker images, and deploys both services. It prints the ALB URL when finished.

### Test
```bash
# Browse tickets
curl http://<ALB_URL>/tickets

# Place an order
curl -X POST -H "Content-Type: application/json" \
  -d '{"ticket_id":1,"quantity":2,"idempotency_key":"test-001"}' \
  http://<ALB_URL>/orders

# Validate no overbooking
curl http://<ALB_URL>/validate
```

### Run Load Tests
```bash
pip install locust
locust -f locust/locustfile.py --host=http://<ALB_URL>
# Open http://localhost:8089 in your browser
```

### Change Locking Strategy
```bash
cd terraform
terraform apply -var='db_password=<YOUR_PASSWORD>' -var='lock_strategy=optimistic'
# Options: pessimistic, optimistic, redis
```

### Tear Down
```bash
bash destroy.sh
```
