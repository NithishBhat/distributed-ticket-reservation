"""
Experiment 4: Caching Layer Impact

Read-heavy mixed workload to compare ticket-service performance
with and without the Redis caching layer.

Run WITHOUT cache (baseline):
  terraform apply -var='db_password=...' -var='enable_cache=false'
  locust -f locust/locustfile_cache.py --host=http://<ALB_DNS> \\
    --users 200 --spawn-rate 20 --run-time 5m --headless

Run WITH cache:
  terraform apply -var='db_password=...' -var='enable_cache=true'
  locust -f locust/locustfile_cache.py --host=http://<ALB_DNS> \\
    --users 200 --spawn-rate 20 --run-time 5m --headless

Metrics to collect from Locust CSV / UI:
  - GET /tickets        req/s, avg latency, p50/p95/p99
  - GET /tickets/{id}   req/s, avg latency, p50/p95/p99
  - POST /orders        req/s (kept low intentionally)
  - X-Cache HIT/MISS ratio: check via CloudWatch or curl -I

Cache hit rate proxy:
  After enabling cache, p99 latency on GET /tickets should drop
  sharply after the first TTL window (~10s warm-up).
"""

import random
import uuid

from locust import HttpUser, between, task

TICKET_IDS = tuple(range(1, 51))


class ReadHeavyUser(HttpUser):
    """
    Simulates a read-heavy browse workload:
      - 10x  GET /tickets          (list all — hits ticket:all cache key)
      - 5x   GET /tickets/{id}     (single ticket — hits ticket:id:{id})
      - 2x   POST /orders          (light write traffic to keep the system realistic)
      - 1x   GET /validate         (overselling guard, also exercises a DB-only path)

    Task ratio is 10:5:2:1 so ~56% of requests are GET /tickets,
    ~28% are GET /tickets/{id}, ~11% POST /orders, ~5% GET /validate.
    """

    wait_time = between(0.05, 0.3)

    @task(10)
    def browse_all_tickets(self):
        self.client.get("/tickets", name="GET /tickets")

    @task(5)
    def browse_single_ticket(self):
        ticket_id = random.choice(TICKET_IDS)
        self.client.get(f"/tickets/{ticket_id}", name="GET /tickets/{id}")

    @task(2)
    def place_order(self):
        payload = {
            "ticket_id": random.choice(TICKET_IDS),
            "quantity": 1,
            "idempotency_key": str(uuid.uuid4()),
        }
        with self.client.post(
            "/orders",
            json=payload,
            catch_response=True,
            name="POST /orders",
        ) as resp:
            if resp.status_code in (200, 201, 409):
                resp.success()
            elif resp.status_code >= 500:
                resp.failure(f"server error {resp.status_code}")
            else:
                resp.failure(f"unexpected status {resp.status_code}")

    @task(1)
    def validate_no_overselling(self):
        with self.client.get(
            "/validate",
            catch_response=True,
            name="GET /validate",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                if data.get("valid"):
                    resp.success()
                else:
                    resp.failure(f"OVERSELLING DETECTED: {data.get('violations')}")
            elif resp.status_code == 409:
                resp.failure(f"OVERSELLING DETECTED: {resp.text}")
            else:
                resp.failure(f"validate error {resp.status_code}")
