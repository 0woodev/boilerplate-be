output "api_endpoint" {
  description = "API Gateway 기본 엔드포인트 (execute-api URL)"
  value       = module.api_gateway.endpoint
}

output "api_custom_url" {
  description = "커스텀 도메인 API URL (ex: https://myapp-api.wooapps.net)"
  value       = module.custom_domain.api_url
}

output "user_lambda_names" {
  description = "User 도메인 Lambda 함수명 목록"
  value       = module.user_domain.lambda_function_names
}

output "app_registry_application_arn" {
  description = "AWS AppRegistry application ARN"
  value       = aws_servicecatalogappregistry_application.app.arn
}
