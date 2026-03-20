# ============================================================
# 공유 리소스 참조 (setup.sh에서 AWS CLI로 생성됨 - Terraform 외부 관리)
# 없으면 plan/apply 단계에서 즉시 에러 → 안전
# ============================================================
data "aws_acm_certificate" "wildcard" {
  domain      = "*.${var.domain}"
  statuses    = ["ISSUED"]
  most_recent = true
}

data "aws_route53_zone" "this" {
  name = var.domain
}

# ============================================================
# API Gateway Custom Domain
# ============================================================
resource "aws_apigatewayv2_domain_name" "this" {
  domain_name = var.be_domain

  domain_name_configuration {
    certificate_arn = data.aws_acm_certificate.wildcard.arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }

  tags = var.tags
}

resource "aws_apigatewayv2_api_mapping" "this" {
  api_id      = var.api_gateway_id
  domain_name = aws_apigatewayv2_domain_name.this.id
  stage       = "$default"
}

# ============================================================
# Route53 A Record → API Gateway Custom Domain
# ============================================================
resource "aws_route53_record" "api" {
  zone_id = data.aws_route53_zone.this.zone_id
  name    = var.be_domain
  type    = "A"

  alias {
    name                   = aws_apigatewayv2_domain_name.this.domain_name_configuration[0].target_domain_name
    zone_id                = aws_apigatewayv2_domain_name.this.domain_name_configuration[0].hosted_zone_id
    evaluate_target_health = false
  }
}
