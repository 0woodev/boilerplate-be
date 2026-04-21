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
# setup.sh 에서 AWS CLI로 생성 (계정당 1회, Terraform 외부 관리)
# data source로 참조만 → terraform destroy 해도 절대 삭제 안 됨
# ============================================================
data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
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
      # ── Lambda Functions (stage-scoped) ─────────────────────────
      {
        Effect = "Allow"
        Action = [
          "lambda:CreateFunction", "lambda:UpdateFunctionCode", "lambda:UpdateFunctionConfiguration",
          "lambda:GetFunction", "lambda:GetFunctionConfiguration", "lambda:DeleteFunction",
          "lambda:AddPermission", "lambda:RemovePermission", "lambda:GetPolicy",
          "lambda:CreateAlias", "lambda:UpdateAlias", "lambda:DeleteAlias",
          "lambda:GetAlias", "lambda:ListAliases",
          "lambda:PublishVersion", "lambda:ListVersionsByFunction",
          "lambda:TagResource", "lambda:UntagResource", "lambda:ListTags",
          "lambda:GetFunctionCodeSigningConfig"
        ]
        Resource = "arn:aws:lambda:${var.aws_region}:${var.aws_account_id}:function:${var.project_name}-${each.key}-*"
      },
      # ── Lambda Layers (stage-scoped) ──────────────────────────
      {
        Effect = "Allow"
        Action = [
          "lambda:PublishLayerVersion", "lambda:DeleteLayerVersion",
          "lambda:GetLayerVersion", "lambda:ListLayerVersions",
          "lambda:GetLayerVersionPolicy",
          "lambda:AddLayerVersionPermission", "lambda:RemoveLayerVersionPermission"
        ]
        Resource = "arn:aws:lambda:${var.aws_region}:${var.aws_account_id}:layer:${var.project_name}-${each.key}-*"
      },
      # ── API Gateway (region-scoped, ID가 런타임에 결정되어 project 기반 ARN 제한 불가) ──
      {
        Effect   = "Allow"
        Action   = ["apigateway:GET", "apigateway:POST", "apigateway:PUT", "apigateway:PATCH", "apigateway:DELETE", "apigateway:TagResource"]
        Resource = "arn:aws:apigateway:${var.aws_region}::/*"
      },
      # ── DynamoDB App Tables (stage-scoped) ────────────────────
      {
        Effect = "Allow"
        Action = [
          "dynamodb:CreateTable", "dynamodb:DeleteTable", "dynamodb:DescribeTable", "dynamodb:UpdateTable",
          "dynamodb:ListTagsOfResource", "dynamodb:TagResource", "dynamodb:UntagResource",
          "dynamodb:UpdateTimeToLive", "dynamodb:DescribeTimeToLive",
          "dynamodb:UpdateContinuousBackups", "dynamodb:DescribeContinuousBackups"
        ]
        Resource = "arn:aws:dynamodb:${var.aws_region}:${var.aws_account_id}:table/${var.project_name}-${each.key}-*"
      },
      # ── SQS Queues (stage-scoped) ─────────────────────────────
      {
        Effect = "Allow"
        Action = [
          "sqs:CreateQueue", "sqs:DeleteQueue",
          "sqs:GetQueueAttributes", "sqs:SetQueueAttributes", "sqs:GetQueueUrl",
          "sqs:TagQueue", "sqs:UntagQueue"
        ]
        Resource = "arn:aws:sqs:${var.aws_region}:${var.aws_account_id}:${var.project_name}-${each.key}-*"
      },
      # ── IAM (Lambda 실행 Role만, stage-scoped) ────────────────
      # iam:* 대신 Lambda execution role 관리에 필요한 최소 권한만 부여
      # GitHub Actions Role 자체 수정 불가 → 권한 에스컬레이션 차단
      {
        Effect = "Allow"
        Action = [
          "iam:CreateRole", "iam:DeleteRole", "iam:GetRole", "iam:UpdateRole",
          "iam:TagRole", "iam:UntagRole", "iam:ListRoleTags",
          "iam:PutRolePolicy", "iam:GetRolePolicy", "iam:DeleteRolePolicy", "iam:ListRolePolicies",
          "iam:AttachRolePolicy", "iam:DetachRolePolicy", "iam:ListAttachedRolePolicies"
        ]
        Resource = "arn:aws:iam::${var.aws_account_id}:role/${var.project_name}-${each.key}-*"
      },
      {
        Effect   = "Allow"
        Action   = "iam:PassRole"
        Resource = "arn:aws:iam::${var.aws_account_id}:role/${var.project_name}-${each.key}-*"
        Condition = {
          StringEquals = { "iam:PassedToService" = "lambda.amazonaws.com" }
        }
      },
      # ── CloudWatch Logs (stage-scoped) ────────────────────────
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup", "logs:DeleteLogGroup",
          "logs:PutRetentionPolicy", "logs:DeleteRetentionPolicy",
          "logs:TagLogGroup", "logs:UntagLogGroup",
          "logs:TagResource", "logs:UntagResource", "logs:ListTagsForResource", "logs:ListTagsLogGroup"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${var.aws_account_id}:log-group:/aws/lambda/${var.project_name}-${each.key}-*"
      },
      {
        # DescribeLogGroups는 list 작업이라 Resource: * 필요
        Effect   = "Allow"
        Action   = ["logs:DescribeLogGroups"]
        Resource = "*"
      },
      # ── AppRegistry (resource-level 권한 미지원) ───────────────
      {
        Effect = "Allow"
        Action = [
          "servicecatalog:CreateApplication", "servicecatalog:GetApplication",
          "servicecatalog:UpdateApplication", "servicecatalog:DeleteApplication",
          "servicecatalog:CreateAttributeGroup", "servicecatalog:GetAttributeGroup",
          "servicecatalog:UpdateAttributeGroup", "servicecatalog:DeleteAttributeGroup",
          "servicecatalog:AssociateAttributeGroup", "servicecatalog:DisassociateAttributeGroup",
          "servicecatalog:ListAssociatedAttributeGroups",
          "servicecatalog:AssociateResource", "servicecatalog:DisassociateResource",
          "servicecatalog:GetAssociatedResource", "servicecatalog:ListAssociatedResources",
          "servicecatalog:TagResource", "servicecatalog:UntagResource",
          "servicecatalog:ListTagsForResource", "servicecatalog:SyncResource"
        ]
        Resource = "*"
      },
      # ── CloudFront (Distribution ARN은 랜덤 ID라 project 기반 제한 불가) ──
      {
        Effect = "Allow"
        Action = [
          "cloudfront:CreateDistribution", "cloudfront:GetDistribution",
          "cloudfront:GetDistributionConfig", "cloudfront:UpdateDistribution", "cloudfront:DeleteDistribution",
          "cloudfront:TagResource", "cloudfront:UntagResource", "cloudfront:ListTagsForResource",
          "cloudfront:ListDistributions"
        ]
        Resource = "*"
      },
      # ── ACM (read-only: Terraform data source로만 사용) ───────
      {
        Effect   = "Allow"
        Action   = ["acm:DescribeCertificate", "acm:ListCertificates", "acm:GetCertificate", "acm:ListTagsForCertificate"]
        Resource = "*"
      },
      # ── Route53 ───────────────────────────────────────────────
      {
        Effect = "Allow"
        Action = [
          "route53:GetHostedZone", "route53:ListHostedZones", "route53:ListHostedZonesByName",
          "route53:ChangeResourceRecordSets", "route53:GetChange",
          "route53:ListResourceRecordSets",
          "route53:ListTagsForResource", "route53:ChangeTagsForResource"
        ]
        Resource = "*"
      }
    ]
  })
}
