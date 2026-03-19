variable "project_name" { type = string }
variable "stage"        { type = string }

variable "tables" {
  description = "생성할 DynamoDB 테이블 명세. key = 테이블 식별자 (실제명: {project}-{stage}-{key})"
  type = map(object({
    # ── 키 설계 ────────────────────────────────────────────────
    hash_key      = string
    hash_key_type = optional(string, "S") # S | N | B

    range_key      = optional(string, null)
    range_key_type = optional(string, "S")

    # ── 빌링 ──────────────────────────────────────────────────
    billing_mode   = optional(string, "PAY_PER_REQUEST") # PAY_PER_REQUEST | PROVISIONED
    read_capacity  = optional(number, null)              # PROVISIONED 전용
    write_capacity = optional(number, null)

    # ── TTL ───────────────────────────────────────────────────
    ttl_attribute = optional(string, null) # null이면 TTL 비활성

    # ── 스트림 ────────────────────────────────────────────────
    stream_enabled   = optional(bool, false)
    stream_view_type = optional(string, "NEW_AND_OLD_IMAGES") # NEW_IMAGE | OLD_IMAGE | NEW_AND_OLD_IMAGES | KEYS_ONLY

    # ── 복구 / 암호화 ──────────────────────────────────────────
    point_in_time_recovery = optional(bool, false)
    server_side_encryption = optional(bool, false)
    kms_master_key_id      = optional(string, null) # null이면 AWS 관리형 키

    # ── GSI (Global Secondary Index) ──────────────────────────
    gsi = optional(list(object({
      name               = string
      hash_key           = string
      hash_key_type      = optional(string, "S")
      range_key          = optional(string, null)
      range_key_type     = optional(string, "S")
      projection_type    = optional(string, "ALL") # ALL | KEYS_ONLY | INCLUDE
      non_key_attributes = optional(list(string), [])
      read_capacity      = optional(number, null)
      write_capacity     = optional(number, null)
    })), [])

    # ── LSI (Local Secondary Index) ───────────────────────────
    lsi = optional(list(object({
      name               = string
      range_key          = string
      range_key_type     = optional(string, "S")
      projection_type    = optional(string, "ALL")
      non_key_attributes = optional(list(string), [])
    })), [])

    tags = optional(map(string), {})
  }))
}

variable "tags" {
  type    = map(string)
  default = {}
}
