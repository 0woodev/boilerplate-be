locals {
  common_env = {
    PROJECT_NAME = var.project_name
    STAGE        = var.stage
  }

  # ──────────────────────────────────────────────────────────────
  # Lambda 목록
  # 새 API 추가 시 여기에 항목만 추가하면 됩니다.
  # ──────────────────────────────────────────────────────────────
  lambdas = {
    api_get_patch_notes = {
      zip_path              = "${path.module}/../../../.build/app/api/patch_note/api_get_patch_notes/build.zip"
      handler               = "handler.handler"
      api_gateway_route     = "GET /patch-notes"
      environment_variables = local.common_env
    }

    api_post_patch_note = {
      zip_path              = "${path.module}/../../../.build/app/api/patch_note/api_post_patch_note/build.zip"
      handler               = "handler.handler"
      api_gateway_route     = "POST /patch-notes"
      environment_variables = local.common_env
    }

    api_patch_patch_note = {
      zip_path              = "${path.module}/../../../.build/app/api/patch_note/api_patch_patch_note/build.zip"
      handler               = "handler.handler"
      api_gateway_route     = "PATCH /patch-notes/{patch_note_id}"
      environment_variables = local.common_env
    }

    api_delete_patch_note = {
      zip_path              = "${path.module}/../../../.build/app/api/patch_note/api_delete_patch_note/build.zip"
      handler               = "handler.handler"
      api_gateway_route     = "DELETE /patch-notes/{patch_note_id}"
      environment_variables = local.common_env
    }
  }
}

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
