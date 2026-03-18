locals {
  default_tags = {
    Project = var.project_name
    Stage   = var.stage
  }

  # FIFO 큐는 이름에 .fifo suffix 필요
  queue_names = {
    for k, q in var.queues : k => "${var.project_name}-${var.stage}-${k}${q.fifo_queue ? ".fifo" : ""}"
  }
  dlq_names = {
    for k, q in var.queues : k => "${var.project_name}-${var.stage}-${k}-dlq${q.fifo_queue ? ".fifo" : ""}"
    if q.enable_dlq
  }

  dlq_queues = { for k, q in var.queues : k => q if q.enable_dlq }
}

# ── Dead Letter Queues ─────────────────────────────────────────
resource "aws_sqs_queue" "dlq" {
  for_each = local.dlq_queues

  name       = local.dlq_names[each.key]
  fifo_queue = each.value.fifo_queue

  message_retention_seconds = each.value.dlq_retention_seconds

  kms_master_key_id                 = each.value.kms_master_key_id
  kms_data_key_reuse_period_seconds = each.value.kms_master_key_id != null ? each.value.kms_data_key_reuse_period_seconds : null

  tags = merge(local.default_tags, each.value.tags, { Role = "dlq" })
}

# ── Main Queues ────────────────────────────────────────────────
resource "aws_sqs_queue" "this" {
  for_each = var.queues

  name                        = local.queue_names[each.key]
  fifo_queue                  = each.value.fifo_queue
  content_based_deduplication = each.value.fifo_queue ? each.value.content_based_deduplication : null

  visibility_timeout_seconds = each.value.visibility_timeout_seconds
  message_retention_seconds  = each.value.message_retention_seconds
  max_message_size           = each.value.max_message_size
  delay_seconds              = each.value.delay_seconds
  receive_wait_time_seconds  = each.value.receive_wait_time_seconds

  kms_master_key_id                 = each.value.kms_master_key_id
  kms_data_key_reuse_period_seconds = each.value.kms_master_key_id != null ? each.value.kms_data_key_reuse_period_seconds : null

  redrive_policy = each.value.enable_dlq ? jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq[each.key].arn
    maxReceiveCount     = each.value.dlq_max_receive_count
  }) : null

  tags = merge(local.default_tags, each.value.tags)
}
