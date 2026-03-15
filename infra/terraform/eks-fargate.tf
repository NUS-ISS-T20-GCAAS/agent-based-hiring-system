# ──────────────────────────────────────────────
# EKS Fargate Profiles
# ──────────────────────────────────────────────
# All pods in the "services" namespace are scheduled on
# Fargate for serverless, auto-scaling compute.
# ──────────────────────────────────────────────

# ── Fargate Profile: services namespace ───────
resource "aws_eks_fargate_profile" "services" {
  cluster_name           = aws_eks_cluster.main.name
  fargate_profile_name   = "${local.cluster_name}-services"
  pod_execution_role_arn = aws_iam_role.fargate_pod_execution.arn
  subnet_ids             = aws_subnet.private[*].id

  selector {
    namespace = "services"
  }

  tags = {
    Name = "${local.cluster_name}-fargate-services"
  }
}

# ── Fargate Profile: kube-system (CoreDNS) ────
# CoreDNS must run on Fargate if there are Fargate-only
# pods that need DNS resolution before node group is ready.
resource "aws_eks_fargate_profile" "kube_system" {
  cluster_name           = aws_eks_cluster.main.name
  fargate_profile_name   = "${local.cluster_name}-kube-system"
  pod_execution_role_arn = aws_iam_role.fargate_pod_execution.arn
  subnet_ids             = aws_subnet.private[*].id

  selector {
    namespace = "kube-system"
    labels = {
      k8s-app = "kube-dns"
    }
  }

  tags = {
    Name = "${local.cluster_name}-fargate-kube-system"
  }
}
