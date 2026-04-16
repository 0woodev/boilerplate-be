# ============================================================
# 전체 DynamoDB 테이블 명세
#
# DB 라이프사이클은 Lambda 배포와 독립적이므로 shared/ 에서 관리.
# 새 도메인 테이블 추가 시 해당 도메인 locals 블록에 항목만 추가.
#
# 컬럼 네이밍/GSI 규칙은 common/models/<domain>.py 의 DynamoModel 서브클래스와 1:1.
# ============================================================

# ── User 도메인 ────────────────────────────────────────────────
# common/models/user.py :: User
locals {
  user_tables = {
    users = {
      hash_key               = "PK"
      range_key              = "SK"
      point_in_time_recovery = true

      gsi = [
        {
          name      = "ByEmail"
          hash_key  = "ByEmailPK"
          range_key = "ByEmailSK"
        },
        {
          name      = "ByStatus"
          hash_key  = "ByStatusPK"
          range_key = "ByStatusSK"
        },
      ]
    }
  }
}

module "user_tables" {
  source       = "../../modules/dynamodb"
  project_name = var.project_name
  stage        = var.stage
  tables       = local.user_tables
  tags         = var.tags
}

# ── Group 도메인 ───────────────────────────────────────────────
# common/models/group.py :: Group
locals {
  group_tables = {
    groups = {
      hash_key               = "PK"
      range_key              = "SK"
      point_in_time_recovery = true

      gsi = [
        {
          name      = "ByOwner"
          hash_key  = "ByOwnerPK"
          range_key = "ByOwnerSK"
        },
      ]
    }
  }
}

module "group_tables" {
  source       = "../../modules/dynamodb"
  project_name = var.project_name
  stage        = var.stage
  tables       = local.group_tables
  tags         = var.tags
}

# ── Member 도메인 ──────────────────────────────────────────────
# common/models/member.py :: Member
locals {
  member_tables = {
    members = {
      hash_key               = "PK"
      range_key              = "SK"
      point_in_time_recovery = true

      gsi = [
        {
          name      = "ByUser"
          hash_key  = "ByUserPK"
          range_key = "ByUserSK"
        },
        {
          name      = "ByRole"
          hash_key  = "ByRolePK"
          range_key = "ByRoleSK"
        },
      ]
    }
  }
}

module "member_tables" {
  source       = "../../modules/dynamodb"
  project_name = var.project_name
  stage        = var.stage
  tables       = local.member_tables
  tags         = var.tags
}
