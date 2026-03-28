"""
Load test for the ticket platform ALB.

Experiment 1 (auto-scaling): keep Locust settings identical while changing
`order_service_count` in Terraform; compare req/s, p50/p95/p99, error rate.

Experiment 2 (locking): use the same Locust *user count / duration* for both
runs, but set LOCUST_HOT_TICKET so most contention hits one row — otherwise
load spreads across tickets 1–4 and lock-strategy differences are hard to see.
Example: LOCUST_HOT_TICKET=1 (see how-to-test.txt).

Suggested headless run (same args every time you change task count):
  locust -f locust/locustfile.py --host=http://<ALB_DNS> \\
    --users 200 --spawn-rate 20 --run-time 5m --headless

Web UI:
  locust -f locust/locustfile.py --host=http://<ALB_DNS>
  open http://localhost:8089
"""

import os
import random
import uuid

from locust import HttpUser, between, task

# Seed data: ticket-service creates ids 1..4 with large capacities.
TICKET_IDS = (1, 2, 3, 4)


def pick_ticket_id() -> int:
    """
    Default: random spread across TICKET_IDS (good for experiment 1).
    If LOCUST_HOT_TICKET is set (e.g. 1), always use that id for high row
    contention (recommended for experiment 2 — locking strategies).
    """
    raw = os.environ.get("LOCUST_HOT_TICKET", "").strip()
    if raw:
        return int(raw)
    return random.choice(TICKET_IDS)


class OrderHeavyUser(HttpUser):
    """
    Stresses POST /orders (routed to order-service). This matches experiment 1
    where you scale `order_service_count`.
    """

    wait_time = between(0.1, 0.5)

    @task(20)
    def place_order(self):
        payload = {
            "ticket_id": pick_ticket_id(),
            "quantity": 1,
            "idempotency_key": str(uuid.uuid4()),
        }
        with self.client.post(
            "/orders",
            json=payload,
            catch_response=True,
            name="POST /orders",
        ) as resp:
            if resp.status_code in (200, 201):
                resp.success()
            elif resp.status_code == 409:
                # Business conflict (sold out); not an infra error for scaling runs
                resp.success()
            elif resp.status_code >= 500:
                resp.failure(f"server error {resp.status_code}")
            else:
                resp.failure(f"unexpected status {resp.status_code}")

    @task(1)
    def browse_tickets(self):
        """Light read traffic to ticket-service (optional realism)."""
        self.client.get("/tickets", name="GET /tickets")
