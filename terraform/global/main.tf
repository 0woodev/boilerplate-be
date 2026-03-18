terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # global 리소스는 별도 state로 관리 (stage 무관, 계정당 1회)
  backend "s3" {
    bucket         = "{{TF_STATE_BUCKET}}"
    key            = "{{PROJECT_NAME}}/global.tfstate"
    region         = "{{AWS_REGION}}"
    dynamodb_table = "{{PROJECT_NAME}}-tf-lock"
    encrypt        = true
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
    # 이미 존재하는 경우 import 후 사용: terraform import aws_iam_openid_connect_provider.github <arn>
    prevent_destroy = true
  }
}
