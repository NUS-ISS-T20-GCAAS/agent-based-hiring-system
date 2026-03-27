# ──────────────────────────────────────────────
# EKS Cluster & Managed Node Group
# ──────────────────────────────────────────────

# ── Security Group for EKS Cluster ────────────
resource "aws_security_group" "eks_cluster" {
  name_prefix = "${local.cluster_name}-eks-cluster-"
  vpc_id      = aws_vpc.main.id
  description = "Security group for EKS cluster control plane"

  tags = {
    Name = "${local.cluster_name}-eks-cluster-sg"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_security_group_rule" "eks_cluster_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.eks_cluster.id
  description       = "Allow all outbound traffic"
}

data "aws_caller_identity" "current" {}
data "aws_iam_users" "all" {}

# ── EKS Cluster ───────────────────────────────
resource "aws_eks_cluster" "main" {
  name     = local.cluster_name
  version  = var.eks_cluster_version
  role_arn = aws_iam_role.eks_cluster.arn

  access_config {
    authentication_mode                         = "API_AND_CONFIG_MAP"
    bootstrap_cluster_creator_admin_permissions = true
  }

  vpc_config {
    subnet_ids = concat(
      aws_subnet.public[*].id,
      aws_subnet.private[*].id
    )
    security_group_ids      = [aws_security_group.eks_cluster.id]
    endpoint_private_access = true
    endpoint_public_access  = true # Set to false for production
  }

  enabled_cluster_log_types = [
    "api",
    "audit",
    "authenticator",
  ]

  tags = {
    Name = local.cluster_name
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
    aws_iam_role_policy_attachment.eks_vpc_resource_controller,
  ]
}

# ── Security Group for EKS Worker Nodes ────────
resource "aws_security_group" "eks_nodes" {
  name_prefix = "${local.cluster_name}-eks-nodes-"
  vpc_id      = aws_vpc.main.id
  description = "Security group for EKS worker nodes"

  tags = {
    Name = "${local.cluster_name}-eks-nodes-sg"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Allow inbound NodePort traffic (30000-32767) from anywhere in the VPC
# This is required for the Classic Load Balancer to reach Kubernetes Services
resource "aws_security_group_rule" "eks_nodes_nodeport_ingress" {
  type              = "ingress"
  from_port         = 30000
  to_port           = 32767
  protocol          = "tcp"
  cidr_blocks       = [var.vpc_cidr]
  security_group_id = aws_security_group.eks_nodes.id
  description       = "Allow NodePort traffic from VPC (for ELB health checks)"
}

# Allow all traffic between worker nodes (inter-node communication)
resource "aws_security_group_rule" "eks_nodes_self_ingress" {
  type                     = "ingress"
  from_port                = 0
  to_port                  = 0
  protocol                 = "-1"
  source_security_group_id = aws_security_group.eks_nodes.id
  security_group_id        = aws_security_group.eks_nodes.id
  description              = "Allow all traffic between worker nodes"
}

# Allow all outbound traffic from worker nodes
resource "aws_security_group_rule" "eks_nodes_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.eks_nodes.id
  description       = "Allow all outbound traffic"
}

# ── Managed Node Group (for frontend & system workloads) ──
resource "aws_eks_node_group" "general" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${local.cluster_name}-general"
  node_role_arn   = aws_iam_role.eks_node_group.arn
  subnet_ids      = aws_subnet.private[*].id

  launch_template {
    id      = aws_launch_template.eks_nodes.id
    version = aws_launch_template.eks_nodes.latest_version
  }

  scaling_config {
    desired_size = var.node_desired_size
    min_size     = var.node_min_size
    max_size     = var.node_max_size
  }

  update_config {
    max_unavailable = 1
  }

  labels = {
    role = "general"
  }

  tags = {
    Name = "${local.cluster_name}-node"
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.ecr_read_only,
  ]
}

# Attach the node security group to each node via a launch template
# Note: EKS managed node groups auto-attach the cluster security group,
# but we need to ensure the additional node SG is also applied.
resource "aws_launch_template" "eks_nodes" {
  name_prefix   = "${local.cluster_name}-nodes-"
  instance_type = var.node_instance_type

  vpc_security_group_ids = [
    aws_eks_cluster.main.vpc_config[0].cluster_security_group_id,
    aws_security_group.eks_nodes.id,
  ]

  tags = {
    Name = "${local.cluster_name}-node-lt"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# ── Allow Root Account Access ──────────────────
resource "aws_eks_access_entry" "root" {
  cluster_name  = aws_eks_cluster.main.name
  principal_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
  type          = "STANDARD"
}

resource "aws_eks_access_policy_association" "root_admin" {
  cluster_name  = aws_eks_cluster.main.name
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
  principal_arn = aws_eks_access_entry.root.principal_arn
  access_scope {
    type = "cluster"
  }
}

# ── Allow All IAM Users Access ────────────────
resource "aws_eks_access_entry" "all_users" {
  for_each      = setsubtract(data.aws_iam_users.all.arns, [data.aws_caller_identity.current.arn])
  cluster_name  = aws_eks_cluster.main.name
  principal_arn = each.value
  type          = "STANDARD"
}

resource "aws_eks_access_policy_association" "all_users_admin" {
  for_each      = aws_eks_access_entry.all_users
  cluster_name  = aws_eks_cluster.main.name
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
  principal_arn = each.value.principal_arn
  access_scope {
    type = "cluster"
  }
}
