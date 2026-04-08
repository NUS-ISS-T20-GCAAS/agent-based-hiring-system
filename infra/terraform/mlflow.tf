# ──────────────────────────────────────────────
# MLflow — S3 Artifact Store + IRSA
# ──────────────────────────────────────────────
# Provisions the S3 bucket that MLflow uses to
# store experiment artifacts, and an IAM role
# bound to the mlflow Kubernetes ServiceAccount
# (via IRSA) granting least-privilege S3 access.
#
# Backend store: the existing hiring_system RDS
# PostgreSQL database (MLflow creates its own
# tables — no naming conflicts with app schema).

# ── S3 Artifact Bucket ──────────────────────────

resource "aws_s3_bucket" "mlflow_artifacts" {
  bucket = "${var.project_name}-mlflow-artifacts-${var.environment}"

  tags = {
    Name        = "${var.project_name}-mlflow-artifacts-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "mlflow_artifacts" {
  bucket = aws_s3_bucket.mlflow_artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "mlflow_artifacts" {
  bucket = aws_s3_bucket.mlflow_artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "mlflow_artifacts" {
  bucket                  = aws_s3_bucket.mlflow_artifacts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ── IAM Policy: S3 Least-Privilege ─────────────

resource "aws_iam_policy" "mlflow_s3" {
  name        = "${local.cluster_name}-mlflow-s3-policy"
  description = "Allows the MLflow pod to read/write artifacts in its S3 bucket"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
        ]
        Resource = "${aws_s3_bucket.mlflow_artifacts.arn}/*"
      },
      {
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = aws_s3_bucket.mlflow_artifacts.arn
      }
    ]
  })

  tags = {
    Name = "${local.cluster_name}-mlflow-s3-policy"
  }
}

# ── IRSA Role for MLflow Pod ────────────────────
# Follows the same pattern as alb-controller.tf.
# Trust is scoped to the exact Kubernetes
# ServiceAccount "mlflow" in the "services" namespace.

resource "aws_iam_role" "mlflow_pod" {
  name = "${local.cluster_name}-mlflow-pod-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.eks.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${replace(aws_eks_cluster.main.identity[0].oidc[0].issuer, "https://", "")}:sub" = "system:serviceaccount:services:mlflow"
          "${replace(aws_eks_cluster.main.identity[0].oidc[0].issuer, "https://", "")}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })

  tags = {
    Name = "${local.cluster_name}-mlflow-pod-role"
  }
}

resource "aws_iam_role_policy_attachment" "mlflow_s3" {
  policy_arn = aws_iam_policy.mlflow_s3.arn
  role       = aws_iam_role.mlflow_pod.name
}

# ── Outputs ─────────────────────────────────────

output "mlflow_s3_bucket" {
  description = "S3 bucket name for MLflow experiment artifacts"
  value       = aws_s3_bucket.mlflow_artifacts.id
}

output "mlflow_irsa_role_arn" {
  description = "IAM role ARN for the MLflow Kubernetes ServiceAccount (IRSA)"
  value       = aws_iam_role.mlflow_pod.arn
}
