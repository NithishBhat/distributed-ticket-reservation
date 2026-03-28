how to run

1. set AWS creds
   aws configure
   export AWS_ACCESS_KEY_ID=...
   export AWS_SECRET_ACCESS_KEY=...
   export AWS_SESSION_TOKEN=...

2. deploy everything
   bash deploy.sh

3. script prints the ALB url when it's done. test with:
   curl http://<ALB_URL>/tickets
   curl -X POST -H "Content-Type: application/json" \
     -d '{"ticket_id":1,"quantity":2,"idempotency_key":"test-001"}' \
     http://<ALB_URL>/orders

4. tear it all down
   bash destroy.sh
