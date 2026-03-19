output "api_endpoint" {
  description = "API Gateway 엔드포인트"
  value       = module.api_gateway.endpoint
}

output "user_lambda_names" {
  description = "User 도메인 Lambda 함수명 목록"
  value       = module.user_domain.lambda_function_names
}

output "app_registry_application_arn" {
  description = "AWS AppRegistry application ARN"
  value       = aws_servicecatalogappregistry_application.app.arn
}
