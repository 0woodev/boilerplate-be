locals {
  # 네이밍 컨벤션: {project_name}-{stage}-{table_key}
  # IAM은 modules/lambda에서 {project_name}* 와일드카드로 처리되므로 ARN 불필요
  #
  # Service-per-table 패턴: 각 도메인이 전용 테이블을 가진다.
  # Lambda 에는 PROJECT_NAME / STAGE 만 주입하고, 각 모델
  # (`common/dynamo` DynamoModel 서브클래스) 의 `table_name` 템플릿
  # ("{project_name}-{stage}-users" 등) 으로 런타임에 치환한다.
  common_env = {
    PROJECT_NAME = var.project_name
    STAGE        = var.stage
  }

  # ──────────────────────────────────────────────────────────────
  # Lambda 목록
  # 새 API 추가 시 여기에 항목만 추가하면 됩니다.
  #
  # zip_path: make zip-src-all 로 빌드된 경로 (endpoint별 개별 zip)
  # handler:  "handler.handler" 고정 (zip 내 handler.py의 handler 함수)
  # ──────────────────────────────────────────────────────────────
  lambdas = {
    api_post_user = {
      zip_path          = "${path.module}/../../../.build/app/api/user/api_post_user/build.zip"
      handler           = "handler.handler"
      api_gateway_route = "POST /users"
      environment_variables = local.common_env
    }

    api_get_user = {
      zip_path          = "${path.module}/../../../.build/app/api/user/api_get_user/build.zip"
      handler           = "handler.handler"
      api_gateway_route = "GET /users/{user_id}"
      environment_variables = local.common_env
    }

    # api_put_user = {
    #   zip_path          = "${path.module}/../../../.build/app/api/user/api_put_user/build.zip"
    #   handler           = "handler.handler"
    #   api_gateway_route = "PUT /users/{user_id}"
    #   environment_variables = local.common_env
    # }

    # api_delete_user = {
    #   zip_path          = "${path.module}/../../../.build/app/api/user/api_delete_user/build.zip"
    #   handler           = "handler.handler"
    #   api_gateway_route = "DELETE /users/{user_id}"
    #   environment_variables = local.common_env
    # }

    api_get_users = {
      zip_path          = "${path.module}/../../../.build/app/api/user/api_get_users/build.zip"
      handler           = "handler.handler"
      api_gateway_route = "GET /users"
      environment_variables = local.common_env
    }
  }
}

# 주: DynamoDB 테이블 선언은 terraform/shared/databases/main.tf 에서 중앙 관리
# (DB 라이프사이클은 Lambda 배포와 독립적)

module "lambda" {
  for_each = local.lambdas
  source   = "../../modules/lambda"

  project_name = var.project_name
  stage        = var.stage
  name         = each.key

  zip_path    = each.value.zip_path
  handler     = each.value.handler
  memory_size = try(each.value.memory_size, 128)
  timeout     = try(each.value.timeout, 30)

  environment_variables = try(each.value.environment_variables, {})
  layer_arns            = concat(var.common_layer_arns, try(each.value.layer_arns, []))

  api_gateway_id            = var.api_gateway_id
  api_gateway_execution_arn = var.api_gateway_execution_arn
  api_gateway_route         = try(each.value.api_gateway_route, null)

  reserved_concurrent_executions = try(each.value.reserved_concurrent_executions, -1)
  dead_letter_target_arn         = try(each.value.dead_letter_target_arn, null)
  log_retention_days             = try(each.value.log_retention_days, 14)

  tags = var.tags
}
