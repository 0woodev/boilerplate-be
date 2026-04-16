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

    # ── 복구 / 암호화 / 보호 ─────────────────────────────────
    point_in_time_recovery = optional(bool, false)
    server_side_encryption = optional(bool, false)
    kms_master_key_id      = optional(string, null) # null이면 AWS 관리형 키

    # AWS-level 삭제 차단. terraform destroy도 API에서 거부됨.
    # prevent_destroy(terraform lifecycle)보다 강함 — module 통째 제거 우회 케이스도 막음.
    # prod에서 권장. dev에서는 false로 자유롭게 리셋 가능.
    deletion_protection_enabled = optional(bool, false)

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
