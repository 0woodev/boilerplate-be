terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # key는 CI에서 -backend-config="key=..." 로 동적 주입 (stage별 분리)
  # ex) {{PROJECT_NAME}}/dev/terraform.tfstate
  # bucket, key, region, dynamodb_table은 -backend-config 로 주입
  # 로컬: make tf-init / CI: workflow에서 -backend-config 플래그로 전달
  backend "s3" {
    encrypt = true
  }
}

provider "aws" {
  region = var.aws_region
}

# ============================================================
# AWS AppRegistry — 앱 단위 리소스 그룹핑
# ============================================================
resource "aws_servicecatalogappregistry_application" "app" {
  name        = "${var.project_name}-${var.stage}"
  description = "${var.project_name} application (${var.stage})"
}

resource "aws_servicecatalogappregistry_attribute_group" "app" {
  name        = "${var.project_name}-${var.stage}"
  description = "Metadata for ${var.project_name}-${var.stage}"
  attributes = jsonencode({
    project = var.project_name
    stage   = var.stage
    runtime = "python3.12"
    type    = "serverless"
  })
}

resource "aws_servicecatalogappregistry_attribute_group_association" "app" {
  application_id     = aws_servicecatalogappregistry_application.app.id
  attribute_group_id = aws_servicecatalogappregistry_attribute_group.app.id
}

# ============================================================
# Lambda Layers
# ============================================================

# requirements.txt 의존성 Layer (make zip-layer-all 로 빌드)
resource "aws_lambda_layer_version" "requirements" {
  filename            = "${path.module}/../.build/layer/layer.zip"
  layer_name          = "${var.project_name}-${var.stage}-requirements"
  compatible_runtimes = ["python3.12"]
  source_code_hash    = filebase64sha256("${path.module}/../.build/layer/layer.zip")
}

# 공통 코드 Layer (common/ → make zip-common-src-all 로 빌드)
resource "aws_lambda_layer_version" "common" {
  filename            = "${path.module}/../.build/common/layer.zip"
  layer_name          = "${var.project_name}-${var.stage}-common"
  compatible_runtimes = ["python3.12"]
  source_code_hash    = filebase64sha256("${path.module}/../.build/common/layer.zip")
}

# ============================================================
# Shared: API Gateway
# ============================================================
module "api_gateway" {
  source       = "./shared/api_gateway"
  project_name = var.project_name
  stage        = var.stage
  fe_domain    = var.fe_domain
  tags         = aws_servicecatalogappregistry_application.app.application_tag
}

# ============================================================
# Shared: Databases (Lambda 배포와 라이프사이클 분리)
# ============================================================
module "databases" {
  source       = "./shared/databases"
  project_name = var.project_name
  stage        = var.stage
  tags         = aws_servicecatalogappregistry_application.app.application_tag
}

# ============================================================
# Domains
# ============================================================
module "user_domain" {
  source       = "./domains/user"
  project_name = var.project_name
  stage        = var.stage

  api_gateway_id            = module.api_gateway.id
  api_gateway_execution_arn = module.api_gateway.execution_arn
  common_layer_arns         = [aws_lambda_layer_version.requirements.arn, aws_lambda_layer_version.common.arn]
  tags                      = aws_servicecatalogappregistry_application.app.application_tag
}

# 새 도메인 추가 시 여기에 module 블록만 추가
# module "order_domain" {
#   source       = "./domains/order"
#   project_name = var.project_name
#   stage        = var.stage
#   api_gateway_id            = module.api_gateway.id
#   api_gateway_execution_arn = module.api_gateway.execution_arn
#   common_layer_arns         = [aws_lambda_layer_version.requirements.arn, aws_lambda_layer_version.common.arn]
# }
