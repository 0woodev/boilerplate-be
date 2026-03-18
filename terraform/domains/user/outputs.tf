output "lambda_function_names" {
  description = "Lambda 식별자 → 실제 함수명"
  value       = { for k, m in module.lambda : k => m.function_name }
}

output "lambda_arns" {
  description = "Lambda 식별자 → ARN"
  value       = { for k, m in module.lambda : k => m.function_arn }
}

output "lambda_role_names" {
  description = "Lambda 식별자 → IAM Role명 (추가 정책 연결 시 활용)"
  value       = { for k, m in module.lambda : k => m.role_name }
}
