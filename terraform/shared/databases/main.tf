# ============================================================
# 전체 DynamoDB 테이블 명세
#
# DB 라이프사이클은 Lambda 배포와 독립적이므로 shared/에서 관리.
# prevent_destroy = true 로 실수로 인한 데이터 유실 방지.
# 새 테이블 추가 시 해당 도메인 locals 블록에 항목만 추가하면 됩니다.
# ============================================================

# ── User 도메인 테이블 ─────────────────────────────────────────
locals {
  user_tables = {
    users = {
      hash_key  = "PK"
      range_key = "SK"

      ttl_attribute          = "expires_at"
      point_in_time_recovery = true

      gsi = [
        {
          name          = "email-index"
          hash_key      = "email"
          hash_key_type = "S"
        }
      ]
    }
  }

  # 새 도메인 테이블 추가 시 여기에 locals 블록 추가
  # order_tables = { ... }
}

module "user_tables" {
  source       = "../../modules/dynamodb"
  project_name = var.project_name
  stage        = var.stage
  tables       = local.user_tables
  tags         = var.tags
}

# module "order_tables" {
#   source       = "../../modules/dynamodb"
#   project_name = var.project_name
#   stage        = var.stage
#   tables       = local.order_tables
# }
