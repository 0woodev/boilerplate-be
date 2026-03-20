data "aws_route53_zone" "this" {
  name = var.domain
}

# ============================================================
# CloudFront Distribution (API Gateway 앞단)
# ============================================================
resource "aws_cloudfront_distribution" "api" {
  enabled = true
  aliases = [var.be_domain]

  origin {
    # api_gateway_endpoint = "https://xxxxx.execute-api.region.amazonaws.com"
    domain_name = replace(var.api_gateway_endpoint, "https://", "")
    origin_id   = "apigw-${var.project_name}-${var.stage}"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id       = "apigw-${var.project_name}-${var.stage}"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods         = ["GET", "HEAD", "OPTIONS"]
    compress               = true

    # API는 동적 컨텐츠 → 캐싱 비활성화
    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Origin", "Access-Control-Request-Headers", "Access-Control-Request-Method"]
      cookies { forward = "all" }
    }

    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = var.acm_certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  tags = merge({ Project = var.project_name, Stage = var.stage }, var.tags)
}

# ============================================================
# Route53 A Record → CloudFront
# ============================================================
resource "aws_route53_record" "api" {
  zone_id = data.aws_route53_zone.this.zone_id
  name    = var.be_domain
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.api.domain_name
    zone_id                = "Z2FDTNDATAQYW2" # CloudFront global hosted zone ID (고정값)
    evaluate_target_health = false
  }
}
