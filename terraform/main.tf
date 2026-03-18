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
}

# ============================================================
# GitHub Actions OIDC
# OIDC provider는 global/에서 계정당 1회 생성 후 data로 참조
# ============================================================
data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

resource "aws_iam_role" "github_actions" {
  # stage별로 독립된 Role → dev/prod 각각 다른 권한 부여 가능
  name = "${var.project_name}-${var.stage}-github-actions"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = data.aws_iam_openid_connect_provider.github.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_owner}/${var.project_name}-be:*"
        }
      }
    }]
  })

  tags = { Project = var.project_name, Stage = var.stage }
}

resource "aws_iam_role_policy" "github_actions" {
  name = "${var.project_name}-${var.stage}-github-actions"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
        Resource = ["arn:aws:s3:::${var.github_owner}-${var.project_name}-tf-state", "arn:aws:s3:::${var.github_owner}-${var.project_name}-tf-state/*"]
      },
      {
        Effect   = "Allow"
        Action   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem"]
        Resource = "arn:aws:dynamodb:${var.aws_region}:${var.aws_account_id}:table/${var.project_name}-tf-lock"
      },
      {
        Effect = "Allow"
        Action = [
          "lambda:*", "apigateway:*", "dynamodb:*", "sqs:*",
          "iam:GetRole", "iam:PassRole", "iam:CreateRole", "iam:AttachRolePolicy",
          "iam:PutRolePolicy", "iam:DeleteRolePolicy", "iam:DetachRolePolicy",
          "logs:*"
        ]
        Resource = "*"
      }
    ]
  })
}

# ============================================================
# Shared: Databases (Lambda 배포와 라이프사이클 분리)
# ============================================================
module "databases" {
  source       = "./shared/databases"
  project_name = var.project_name
  stage        = var.stage
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
