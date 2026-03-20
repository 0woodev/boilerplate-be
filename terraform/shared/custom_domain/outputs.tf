output "api_url" {
  description = "유저가 실제 호출하는 커스텀 도메인 URL (ex: https://myapp-api.wooapps.net)"
  value       = "https://${var.be_domain}"
}

output "cloudfront_distribution_id" {
  description = "CloudFront Distribution ID"
  value       = aws_cloudfront_distribution.api.id
}
