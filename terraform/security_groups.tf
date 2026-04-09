# ──────────────────────────────────────────────
# ALB Security Group — public HTTP access
# ──────────────────────────────────────────────
resource "aws_security_group" "alb" {
  name        = "ticket-alb-sg"
  description = "Allow HTTP inbound to ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "ticket-alb-sg" }
}

# ──────────────────────────────────────────────
# ECS Security Group — only ALB can reach services
# ──────────────────────────────────────────────
resource "aws_security_group" "ecs" {
  name        = "ticket-ecs-sg"
  description = "Allow inbound from ALB on service ports"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Ticket service from ALB"
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    description     = "Order service from ALB"
    from_port       = 8081
    to_port         = 8081
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "ticket-ecs-sg" }
}

# ──────────────────────────────────────────────
# RDS Security Group — only ECS can reach Postgres
# ──────────────────────────────────────────────
resource "aws_security_group" "rds" {
  name        = "ticket-rds-sg"
  description = "Allow PostgreSQL from ECS tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL from ECS"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "ticket-rds-sg" }
}

# ──────────────────────────────────────────────
# Redis Security Group — only ECS can reach Redis
# ──────────────────────────────────────────────
resource "aws_security_group" "redis" {
  name        = "ticket-redis-sg"
  description = "Allow Redis from ECS tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Redis from ECS"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "ticket-redis-sg" }
}
