# ──────────────────────────────────────────────
# ElastiCache Subnet Group
# ──────────────────────────────────────────────
resource "aws_elasticache_subnet_group" "redis" {
  name       = "ticket-redis-subnet-group"
  subnet_ids = [aws_subnet.private_1.id, aws_subnet.private_2.id]
  tags       = { Name = "ticket-redis-subnet-group" }
}

# ──────────────────────────────────────────────
# ElastiCache Redis Cluster
# ──────────────────────────────────────────────
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "ticket-redis"
  engine               = "redis"
  engine_version       = "7.1"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  port                 = 6379
  parameter_group_name = "default.redis7"
  subnet_group_name    = aws_elasticache_subnet_group.redis.name
  security_group_ids   = [aws_security_group.redis.id]

  tags = { Name = "ticket-redis" }
}
