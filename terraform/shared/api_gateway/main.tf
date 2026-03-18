locals {
  name = "${var.project_name}-${var.stage}"
  default_tags = {
    Project = var.project_name
    Stage   = var.stage
  }
}

resource "aws_apigatewayv2_api" "this" {
  name          = local.name
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = [var.fe_domain]
    allow_methods = var.cors_allow_methods
    allow_headers = var.cors_allow_headers
    max_age       = var.cors_max_age
  }

  tags = merge(local.default_tags, var.tags)
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.this.id
  name        = "$default"
  auto_deploy = true

  tags = merge(local.default_tags, var.tags)
}
