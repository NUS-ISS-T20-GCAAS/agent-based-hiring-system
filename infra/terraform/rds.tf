# ──────────────────────────────────────────────
# RDS PostgreSQL
# ──────────────────────────────────────────────

# ── DB Subnet Group ──────────────────────────
resource "aws_db_subnet_group" "main" {
  name = "${local.cluster_name}-db-subnet"
  # subnet_ids = aws_subnet.private[*].id
  # Using public subnets for dev so the DB is reachable from the internet (for dev purpose and need to revert back to private subnets for production)
  subnet_ids = aws_subnet.public[*].id

  tags = {
    Name = "${local.cluster_name}-db-subnet"
  }
}

# ── Security Group for RDS ───────────────────
resource "aws_security_group" "rds" {
  name_prefix = "${local.cluster_name}-rds-"
  vpc_id      = aws_vpc.main.id
  description = "Allow PostgreSQL access"

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

# ⚠️ Dev only — allows public access to RDS (for dev purpose and need to revert back to private subnets for production)
resource "aws_security_group_rule" "rds_ingress_public" {
  type              = "ingress"
  from_port         = 5432
  to_port           = 5432
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.rds.id
  description       = "PostgreSQL from anywhere (dev only!)"
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
  publicly_accessible    = true  # ⚠️ Dev only — set to false for production!
  multi_az               = false # Single-AZ for dev, set true for prod

  # Storage (Free Tier: 20 GB gp2, no encryption on t3.micro)
  allocated_storage = 20
  storage_type      = "gp2"
  storage_encrypted = false

  # Backup & Maintenance
  # Free Tier: backup_retention_period must be 0 (automated backups not supported)
  backup_retention_period = 0
  maintenance_window      = "sun:05:00-sun:06:00"

  # Dev convenience — disable for production!
  skip_final_snapshot       = var.environment == "dev" ? true : false
  final_snapshot_identifier = var.environment == "dev" ? null : "${local.cluster_name}-final-snapshot"
  deletion_protection       = var.environment == "dev" ? false : true

  # Performance Insights — not supported on Free Tier db.t3.micro
  performance_insights_enabled = false

  tags = {
    Name = "${local.cluster_name}-postgres"
  }
}
