output "api_endpoint" {
  description = "API Gateway 엔드포인트"
  value       = module.api_gateway.endpoint
}

output "github_actions_role_arn" {
  description = "GitHub Actions OIDC Role ARN"
  value       = aws_iam_role.github_actions.arn
}

output "user_lambda_names" {
  description = "User 도메인 Lambda 함수명 목록"
  value       = module.user_domain.lambda_function_names
}

output "user_table_names" {
  description = "User 도메인 DynamoDB 테이블명 목록"
  value       = module.user_domain.table_names
}
