output "table_names" {
  description = "테이블 식별자 → 실제 DynamoDB 테이블명"
  value       = { for k, t in aws_dynamodb_table.this : k => t.name }
}

output "table_arns" {
  description = "테이블 식별자 → ARN"
  value       = { for k, t in aws_dynamodb_table.this : k => t.arn }
}

output "stream_arns" {
  description = "스트림 활성화된 테이블의 stream ARN"
  value       = { for k, t in aws_dynamodb_table.this : k => t.stream_arn if t.stream_enabled }
}
