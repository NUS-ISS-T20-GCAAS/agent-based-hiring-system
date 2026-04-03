# ──────────────────────────────────────────────
# AWS Load Balancer Controller — IAM (IRSA)
# ──────────────────────────────────────────────
# Creates the IAM role + policy for the AWS Load
# Balancer Controller running in EKS. The actual
# controller is installed via Helm (see README).

# Official IAM policy from aws-load-balancer-controller v2.12
data "http" "alb_controller_policy" {
  url = "https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.12.0/docs/install/iam_policy.json"
}

resource "aws_iam_policy" "alb_controller" {
  name   = "${local.cluster_name}-alb-controller-policy"
  policy = data.http.alb_controller_policy.response_body

  tags = {
    Name = "${local.cluster_name}-alb-controller-policy"
  }
}

# IRSA — lets the LB Controller K8s ServiceAccount assume this role
resource "aws_iam_role" "alb_controller" {
  name = "${local.cluster_name}-alb-controller-role"

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
          "${replace(aws_eks_cluster.main.identity[0].oidc[0].issuer, "https://", "")}:sub" = "system:serviceaccount:kube-system:aws-load-balancer-controller"
          "${replace(aws_eks_cluster.main.identity[0].oidc[0].issuer, "https://", "")}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })

  tags = {
    Name = "${local.cluster_name}-alb-controller-role"
  }
}

resource "aws_iam_role_policy_attachment" "alb_controller" {
  policy_arn = aws_iam_policy.alb_controller.arn
  role       = aws_iam_role.alb_controller.name
}
