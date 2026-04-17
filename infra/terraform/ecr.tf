# ──────────────────────────────────────────────
# ECR Repositories
# ──────────────────────────────────────────────

locals {
  ecr_repositories = [
    "frontend",
    "coordinator-agent",
    "resume-intake-agent",
    "screening-agent",
    "skill-assessment-agent",
    "ranking-agent",
    "audit-agent",
    "mlflow"
  ]
}

resource "aws_ecr_repository" "services" {
  for_each = toset(local.ecr_repositories)

  name                 = "${var.project_name}/${each.key}"
  image_tag_mutability = "MUTABLE"
  force_delete         = var.environment == "dev" ? true : false

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name    = each.key
    Service = each.key
  }
}

# ── Lifecycle Policy: keep only the last 10 images ──
resource "aws_ecr_lifecycle_policy" "cleanup" {
  for_each   = toset(local.ecr_repositories)
  repository = aws_ecr_repository.services[each.key].name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep only last 10 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
