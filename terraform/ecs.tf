# ──────────────────────────────────────────────
# ECR Repositories
# ──────────────────────────────────────────────
resource "aws_ecr_repository" "ticket_service" {
  name                 = "ticket-service"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
  tags                 = { Name = "ticket-service" }
}

resource "aws_ecr_repository" "order_service" {
  name                 = "order-service"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
  tags                 = { Name = "order-service" }
}

# ──────────────────────────────────────────────
# CloudWatch Log Groups
# ──────────────────────────────────────────────
resource "aws_cloudwatch_log_group" "ticket_service" {
  name              = "/ecs/ticket-service"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "order_service" {
  name              = "/ecs/order-service"
  retention_in_days = 7
}

# ──────────────────────────────────────────────
# ECS Task Execution Role
# ──────────────────────────────────────────────
resource "aws_iam_role" "ecs_task_execution" {
  name = "ticket-ecs-task-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ──────────────────────────────────────────────
# ECS Cluster
# ──────────────────────────────────────────────
resource "aws_ecs_cluster" "main" {
  name = "ticket-cluster"
  tags = { Name = "ticket-cluster" }
}

# ──────────────────────────────────────────────
# Ticket Service — Task Definition + Service
# ──────────────────────────────────────────────
resource "aws_ecs_task_definition" "ticket_service" {
  family                   = "ticket-service"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn

  container_definitions = jsonencode([{
    name      = "ticket-service"
    image     = "${aws_ecr_repository.ticket_service.repository_url}:latest"
    essential = true

    portMappings = [{
      containerPort = 8080
      protocol      = "tcp"
    }]

    environment = [
      { name = "DB_HOST", value = aws_db_instance.postgres.address },
      { name = "DB_PORT", value = "5432" },
      { name = "DB_USER", value = var.db_username },
      { name = "DB_PASSWORD", value = var.db_password },
      { name = "DB_NAME", value = "ticketdb" },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.ticket_service.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}

resource "aws_ecs_service" "ticket_service" {
  name            = "ticket-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.ticket_service.arn
  desired_count   = var.ticket_service_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = [aws_subnet.private_1.id, aws_subnet.private_2.id]
    security_groups = [aws_security_group.ecs.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.ticket_service.arn
    container_name   = "ticket-service"
    container_port   = 8080
  }

  depends_on = [aws_lb_listener.http]
}

# ──────────────────────────────────────────────
# Order Service — Task Definition + Service
# ──────────────────────────────────────────────
resource "aws_ecs_task_definition" "order_service" {
  family                   = "order-service"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn

  container_definitions = jsonencode([{
    name      = "order-service"
    image     = "${aws_ecr_repository.order_service.repository_url}:latest"
    essential = true

    portMappings = [{
      containerPort = 8081
      protocol      = "tcp"
    }]

    environment = [
      { name = "DB_HOST", value = aws_db_instance.postgres.address },
      { name = "DB_PORT", value = "5432" },
      { name = "DB_USER", value = var.db_username },
      { name = "DB_PASSWORD", value = var.db_password },
      { name = "DB_NAME", value = "ticketdb" },
      { name = "LOCK_STRATEGY", value = var.lock_strategy },
      { name = "REDIS_HOST", value = aws_elasticache_cluster.redis.cache_nodes[0].address },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.order_service.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}

resource "aws_ecs_service" "order_service" {
  name            = "order-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.order_service.arn
  desired_count   = var.order_service_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = [aws_subnet.private_1.id, aws_subnet.private_2.id]
    security_groups = [aws_security_group.ecs.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.order_service.arn
    container_name   = "order-service"
    container_port   = 8081
  }

  depends_on = [aws_lb_listener.http]
}
