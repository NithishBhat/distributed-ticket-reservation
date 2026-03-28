# ──────────────────────────────────────────────
# RDS Subnet Group
# ──────────────────────────────────────────────
resource "aws_db_subnet_group" "postgres" {
  name       = "ticket-db-subnet-group"
  subnet_ids = [aws_subnet.private_1.id, aws_subnet.private_2.id]
  tags       = { Name = "ticket-db-subnet-group" }
}

# ──────────────────────────────────────────────
# RDS PostgreSQL Instance
# ──────────────────────────────────────────────
resource "aws_db_instance" "postgres" {
  identifier     = "ticket-db"
  engine         = "postgres"
  engine_version = "15"
  instance_class = "db.t3.micro"

  allocated_storage = 20
  storage_type      = "gp2"

  db_name  = "ticketdb"
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.postgres.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  multi_az            = false
  publicly_accessible = false
  skip_final_snapshot = true

  tags = { Name = "ticket-db" }
}
