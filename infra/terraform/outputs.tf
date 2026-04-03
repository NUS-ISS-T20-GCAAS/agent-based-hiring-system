# ──────────────────────────────────────────────
# Terraform Outputs
# ──────────────────────────────────────────────

# ── EKS ────────────────────────────────────────
output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = aws_eks_cluster.main.name
}

output "eks_cluster_endpoint" {
  description = "EKS cluster API endpoint"
  value       = aws_eks_cluster.main.endpoint
}

output "eks_cluster_ca_certificate" {
  description = "EKS cluster CA certificate (base64)"
  value       = aws_eks_cluster.main.certificate_authority[0].data
  sensitive   = true
}

output "eks_cluster_oidc_issuer" {
  description = "OIDC issuer URL for IRSA"
  value       = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

# ── ECR ────────────────────────────────────────
output "ecr_repository_urls" {
  description = "Map of service name → ECR repository URL"
  value = {
    for name, repo in aws_ecr_repository.services : name => repo.repository_url
  }
}

# ── RDS ────────────────────────────────────────
output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint (host:port)"
  value       = aws_db_instance.postgres.endpoint
}

output "rds_hostname" {
  description = "RDS hostname (without port)"
  value       = aws_db_instance.postgres.address
}

output "rds_port" {
  description = "RDS port"
  value       = aws_db_instance.postgres.port
}

output "rds_database_name" {
  description = "RDS database name"
  value       = aws_db_instance.postgres.db_name
}

# ── VPC ────────────────────────────────────────
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

# ── Kubeconfig helper ─────────────────────────
output "configure_kubectl" {
  description = "Command to update kubeconfig"
  value       = "aws eks update-kubeconfig --name ${aws_eks_cluster.main.name} --region ${var.aws_region}"
}

# -- Domain / HTTPS ----------------------------
output "acm_certificate_arn" {
  description = "ACM certificate ARN for HTTPS (used by K8s Ingress)"
  value       = var.domain_name != "" ? aws_acm_certificate.frontend[0].arn : ""
}

output "acm_dns_validation_records" {
  description = "CNAME records to add in Namecheap for ACM certificate validation"
  value = var.domain_name != "" ? {
    for dvo in aws_acm_certificate.frontend[0].domain_validation_options : dvo.domain_name => {
      name  = dvo.resource_record_name
      type  = dvo.resource_record_type
      value = dvo.resource_record_value
    }
  } : {}
}

output "alb_controller_role_arn" {
  description = "IAM role ARN for AWS Load Balancer Controller (used by Helm)"
  value       = aws_iam_role.alb_controller.arn
}

output "domain_name" {
  description = "Custom domain name"
  value       = var.domain_name
}
