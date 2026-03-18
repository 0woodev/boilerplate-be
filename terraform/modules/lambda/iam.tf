# ============================================================
# Lambda 실행 IAM Role
# ============================================================
resource "aws_iam_role" "this" {
  name = local.function_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = merge(local.default_tags, var.tags)
}

# 기본 실행 권한: CloudWatch Logs 쓰기
resource "aws_iam_role_policy_attachment" "basic_execution" {
  role       = aws_iam_role.this.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# VPC 배포 시 ENI 생성 권한 추가
resource "aws_iam_role_policy_attachment" "vpc_access" {
  count      = var.vpc_config != null ? 1 : 0
  role       = aws_iam_role.this.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# 추가 Managed Policy 연결 (ex. AmazonDynamoDBFullAccess 등)
resource "aws_iam_role_policy_attachment" "additional" {
  for_each   = toset(var.additional_policy_arns)
  role       = aws_iam_role.this.name
  policy_arn = each.value
}

# 앱 리소스 기본 접근 권한
# 모든 인프라가 {project_name} 프리픽스를 가지므로 와일드카드로 통합 관리
resource "aws_iam_role_policy" "app_resources" {
  name = "${local.function_name}-app-resources"
  role = aws_iam_role.this.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem",
          "dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan",
          "dynamodb:BatchGetItem", "dynamodb:BatchWriteItem",
          "dynamodb:TransactGetItems", "dynamodb:TransactWriteItems"
        ]
        Resource = [
          "arn:aws:dynamodb:*:*:table/${var.project_name}*",
          "arn:aws:dynamodb:*:*:table/${var.project_name}*/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage", "sqs:ReceiveMessage", "sqs:DeleteMessage",
          "sqs:GetQueueAttributes", "sqs:GetQueueUrl", "sqs:ChangeMessageVisibility"
        ]
        Resource = "arn:aws:sqs:*:*:${var.project_name}*"
      }
    ]
  })
}

# 추가 인라인 정책 (기본 외 특수 권한이 필요한 경우)
resource "aws_iam_role_policy" "inline" {
  for_each = var.inline_policies
  name     = each.key
  role     = aws_iam_role.this.id
  policy   = each.value
}
