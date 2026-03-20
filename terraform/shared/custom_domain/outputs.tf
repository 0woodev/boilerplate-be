output "domain_name" {
  description = "커스텀 도메인 (ex: myapp-api.wooapps.net)"
  value       = aws_apigatewayv2_domain_name.this.domain_name
}

output "api_url" {
  description = "유저가 실제 호출하는 커스텀 도메인 URL (ex: https://myapp-api.wooapps.net)"
  value       = "https://${aws_apigatewayv2_domain_name.this.domain_name}"
}
