locals {
  zip_path = "${path.module}/../../../.build/user.zip"

  # 네이밍 컨벤션: {project_name}-{stage}-{table_key}
  # IAM은 modules/lambda에서 {project_name}* 와일드카드로 처리되므로 ARN 불필요
  table_name = {
    users = "${var.project_name}-${var.stage}-users"
  }

  # ──────────────────────────────────────────────────────────────
  # Lambda 목록
  # 새 API 추가 시 여기에 항목만 추가하면 됩니다.
  #
  # 필수: handler, api_gateway_route
  # 선택(미입력 시 모듈 기본값 적용):
  #   memory_size, timeout, environment_variables, layer_arns,
  #   reserved_concurrent_executions, dead_letter_target_arn, log_retention_days
  # ──────────────────────────────────────────────────────────────
  lambdas = {
    create_user = {
      handler           = "app.lambdas.user.create_user.handler"
      memory_size       = 256
      api_gateway_route = "POST /users"
      environment_variables = {
        TABLE_NAME = local.table_name.users
      }
    }

    get_user = {
      handler           = "app.lambdas.user.get_user.handler"
      api_gateway_route = "GET /users/{id}"
      environment_variables = {
        TABLE_NAME = local.table_name.users
      }
    }

    update_user = {
      handler           = "app.lambdas.user.update_user.handler"
      api_gateway_route = "PUT /users/{id}"
      environment_variables = {
        TABLE_NAME = local.table_name.users
      }
    }

    delete_user = {
      handler           = "app.lambdas.user.delete_user.handler"
      api_gateway_route = "DELETE /users/{id}"
      environment_variables = {
        TABLE_NAME = local.table_name.users
      }
    }

    list_users = {
      handler           = "app.lambdas.user.list_users.handler"
      api_gateway_route = "GET /users"
      environment_variables = {
        TABLE_NAME = local.table_name.users
      }
    }
  }
}

module "lambda" {
  for_each = local.lambdas
  source   = "../../modules/lambda"

  project_name = var.project_name
  stage        = var.stage
  name         = each.key

  zip_path    = local.zip_path
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
}
