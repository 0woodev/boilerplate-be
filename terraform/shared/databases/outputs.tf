output "user_table_names" {
  description = "User 도메인 테이블 식별자 → 실제 테이블명"
  value       = module.user_tables.table_names
}

output "user_table_arns" {
  description = "User 도메인 테이블 식별자 → ARN"
  value       = module.user_tables.table_arns
}
