terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # global 리소스는 별도 state로 관리 (stage 무관, 계정당 1회)
  # bucket, key, region, dynamodb_table은 -backend-config 로 주입
  # 로컬: make tf-global / CI: global.yml 워크플로우
  backend "s3" {
    encrypt = true
  }
}

provider "aws" {
  region = var.aws_region
}

# ============================================================
# GitHub Actions OIDC Provider
# AWS 계정당 URL 기준으로 1개만 존재 가능 → global에서 1회 생성
# ============================================================
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]

  lifecycle {
    prevent_destroy = true
  }
}

# ============================================================
# GitHub Actions IAM Role (stage별)
# OIDC와 함께 생성해야 apply.yml이 OIDC 인증 가능
# ============================================================
resource "aws_iam_role" "github_actions" {
  for_each = toset(var.stages)

  name = "${var.project_name}-${each.key}-github-actions"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.github.arn
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

  tags = { Project = var.project_name, Stage = each.key }
}

resource "aws_iam_role_policy" "github_actions" {
  for_each = toset(var.stages)

  name = "${var.project_name}-${each.key}-github-actions"
  role = aws_iam_role.github_actions[each.key].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
        Resource = ["arn:aws:s3:::${var.tf_state_bucket}", "arn:aws:s3:::${var.tf_state_bucket}/*"]
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
          "iam:*",
          "logs:*"
        ]
        Resource = "*"
      }
    ]
  })
}
