output "queue_urls" {
  description = "큐 식별자 → URL"
  value       = { for k, q in aws_sqs_queue.this : k => q.url }
}

output "queue_arns" {
  description = "큐 식별자 → ARN"
  value       = { for k, q in aws_sqs_queue.this : k => q.arn }
}

output "queue_names" {
  description = "큐 식별자 → 실제 큐명"
  value       = { for k, q in aws_sqs_queue.this : k => q.name }
}

output "dlq_arns" {
  description = "DLQ 식별자 → ARN"
  value       = { for k, q in aws_sqs_queue.dlq : k => q.arn }
}

output "dlq_urls" {
  description = "DLQ 식별자 → URL"
  value       = { for k, q in aws_sqs_queue.dlq : k => q.url }
}
