locals {
  common_env = {
    PROJECT_NAME = var.project_name
    STAGE        = var.stage
  }

  lambdas = {
    api_get_health = {
      zip_path          = "${path.module}/../../../.build/app/api/health/api_get_health/build.zip"
      handler           = "handler.handler"
      api_gateway_route = "GET /health"
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
