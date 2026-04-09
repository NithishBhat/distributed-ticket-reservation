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

from locust import HttpUser, between, task, events

# Seed data: ticket-service creates ids 1..50 with large capacities.
TICKET_IDS = tuple(range(1, 51))

# Small pool of reusable keys to stress the idempotency path (~5% of requests)
_recent_keys: list[str] = []
_MAX_RECENT = 50


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


def pick_idempotency_key() -> str:
    """
    ~5% of the time, replay a recently used key to exercise the idempotency
    path and stress-test the duplicate-key race condition fix.
    """
    if _recent_keys and random.random() < 0.05:
        return random.choice(_recent_keys)
    key = str(uuid.uuid4())
    _recent_keys.append(key)
    if len(_recent_keys) > _MAX_RECENT:
        _recent_keys.pop(0)
    return key


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
            "idempotency_key": pick_idempotency_key(),
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

    @task(1)
    def validate_no_overselling(self):
        """Calls /validate to check for overselling during the test."""
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
