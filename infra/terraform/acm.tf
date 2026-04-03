# ──────────────────────────────────────────────
# ACM Certificate for Custom Domain (HTTPS)
# ──────────────────────────────────────────────
# DNS validation: After `terraform apply`, add the
# output CNAME records in Namecheap DNS panel.
# Certificate covers both apex and wildcard:
#   sentinelrecruit.me + *.sentinelrecruit.me

resource "aws_acm_certificate" "frontend" {
  count = var.domain_name != "" ? 1 : 0

  domain_name               = var.domain_name
  subject_alternative_names = ["*.${var.domain_name}"]
  validation_method         = "DNS"

  tags = {
    Name = "${local.cluster_name}-frontend-cert"
  }

  lifecycle {
    create_before_destroy = true
  }
}
