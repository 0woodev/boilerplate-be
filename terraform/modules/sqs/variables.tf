variable "project_name" { type = string }
variable "stage"        { type = string }

variable "queues" {
  description = "생성할 SQS 큐 명세. key = 큐 식별자 (실제명: {project}-{stage}-{key})"
  type = map(object({
    # ── FIFO ──────────────────────────────────────────────────
    fifo_queue                  = optional(bool, false)
    content_based_deduplication = optional(bool, false) # FIFO 전용

    # ── 메시지 설정 ────────────────────────────────────────────
    visibility_timeout_seconds = optional(number, 30)
    message_retention_seconds  = optional(number, 345600)  # 기본 4일 (max 14일)
    max_message_size           = optional(number, 262144)  # 기본 256KB
    delay_seconds              = optional(number, 0)
    receive_wait_time_seconds  = optional(number, 0)       # Long polling: 1~20

    # ── DLQ 자동 생성 ──────────────────────────────────────────
    enable_dlq            = optional(bool, true)
    dlq_max_receive_count = optional(number, 3)
    dlq_retention_seconds = optional(number, 1209600) # 기본 14일

    # ── 암호화 ────────────────────────────────────────────────
    kms_master_key_id                 = optional(string, null) # null이면 SQS 관리형 암호화
    kms_data_key_reuse_period_seconds = optional(number, 300)

    tags = optional(map(string), {})
  }))
}
