# ──────────────────────────────────────────────
# RDS PostgreSQL
# ──────────────────────────────────────────────

# ── DB Subnet Group ──────────────────────────
resource "aws_db_subnet_group" "main" {
  name       = "${local.cluster_name}-db-subnet"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${local.cluster_name}-db-subnet"
  }
}

# ── Security Group for RDS ───────────────────
resource "aws_security_group" "rds" {
  name_prefix = "${local.cluster_name}-rds-"
  vpc_id      = aws_vpc.main.id
  description = "Allow PostgreSQL access from EKS private subnets"

  tags = {
    Name = "${local.cluster_name}-rds-sg"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_security_group_rule" "rds_ingress_private" {
  type              = "ingress"
  from_port         = 5432
  to_port           = 5432
  protocol          = "tcp"
  cidr_blocks       = var.private_subnet_cidrs
  security_group_id = aws_security_group.rds.id
  description       = "PostgreSQL from EKS private subnets"
}

resource "aws_security_group_rule" "rds_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.rds.id
  description       = "Allow all outbound"
}

# ── RDS Instance ─────────────────────────────
resource "aws_db_instance" "postgres" {
  identifier = "${local.cluster_name}-postgres"

  engine         = "postgres"
  engine_version = var.db_engine_version
  instance_class = var.db_instance_class

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  # Networking
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false
  multi_az               = false # Single-AZ for dev, set true for prod

  # Storage
  allocated_storage     = 20
  max_allocated_storage = 50 # Autoscaling up to 50 GB
  storage_type          = "gp3"
  storage_encrypted     = true

  # Backup & Maintenance
  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:05:00-sun:06:00"

  # Dev convenience — disable for production!
  skip_final_snapshot       = var.environment == "dev" ? true : false
  final_snapshot_identifier = var.environment == "dev" ? null : "${local.cluster_name}-final-snapshot"
  deletion_protection       = var.environment == "dev" ? false : true

  # Performance Insights (free tier for db.t3.micro)
  performance_insights_enabled = true

  tags = {
    Name = "${local.cluster_name}-postgres"
  }
}
