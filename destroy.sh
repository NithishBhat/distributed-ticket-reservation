#!/bin/bash
set -e
echo ">>> Tearing down all infrastructure..."
cd "$(dirname "$0")/terraform"
terraform destroy -var="db_password=unused" -auto-approve
echo ">>> Done. All resources destroyed."
