locals {
  function_name = "${var.project_name}-${var.stage}-${var.name}"
  use_s3        = var.s3_bucket != null
  has_api_route = var.api_gateway_route != null

  default_tags = {
    Project = var.project_name
    Stage   = var.stage
    Lambda  = var.name
  }
}

# ── CloudWatch Log Group ──────────────────────────────────────
# Lambda가 자동 생성하기 전에 미리 만들어 retention 설정 보장
resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/lambda/${local.function_name}"
  retention_in_days = var.log_retention_days
  tags              = merge(local.default_tags, var.tags)
}

# ── Lambda Function ───────────────────────────────────────────
resource "aws_lambda_function" "this" {
  function_name = local.function_name
  role          = aws_iam_role.this.arn  # iam.tf에서 생성

  # 실행 진입점: "모듈경로.함수명" ex) app.lambdas.user.create_user.handler
  handler = var.handler

  # 런타임: python3.12, nodejs20.x 등
  runtime = var.runtime

  # 최대 실행 시간 (초). API Gateway 통합 시 29초 이하 권장 (GW 타임아웃 30초)
  timeout = var.timeout

  # 메모리 (MB). CPU 성능도 메모리에 비례해서 올라감
  memory_size = var.memory_size

  # true: 배포마다 버전 번호 발행. alias(live)가 특정 버전을 가리키게 하려면 필수
  publish = var.publish

  # 소스 코드: 로컬 zip 또는 S3 중 하나만 활성화됨
  filename         = local.use_s3 ? null : var.zip_path
  s3_bucket        = local.use_s3 ? var.s3_bucket : null
  s3_key           = local.use_s3 ? var.zip_path : null
  source_code_hash = local.use_s3 ? null : filebase64sha256(var.zip_path) # 코드 변경 감지용 hash

  # Lambda Layer ARN 목록 (공통 의존성 패키지 등). 최대 5개
  layers = var.layer_arns

  # 동시 실행 제한
  # -1: 제한 없음 (계정 리전 기본 한도 공유)
  #  0: 함수 비활성화 (배포 중 트래픽 차단 용도)
  #  N: 이 함수에 N개 예약 → 다른 함수가 사용할 수 있는 한도도 N만큼 줄어듦
  reserved_concurrent_executions = var.reserved_concurrent_executions

  # /tmp 임시 스토리지 크기 (MB). 기본 512, 최대 10240
  # 대용량 파일 처리(ML 모델 로딩, 이미지 변환 등)시 늘려야 함
  ephemeral_storage {
    size = var.ephemeral_storage_size
  }

  # 환경변수: 테이블명, 큐 URL 등 런타임에 주입하는 설정값
  dynamic "environment" {
    for_each = length(var.environment_variables) > 0 ? [1] : []
    content {
      variables = var.environment_variables
    }
  }

  # VPC 배포 설정: 프라이빗 RDS/ElastiCache 접근 시 필요
  # VPC 사용 시 콜드 스타트가 길어질 수 있음 (ENI 생성 비용)
  dynamic "vpc_config" {
    for_each = var.vpc_config != null ? [var.vpc_config] : []
    content {
      subnet_ids         = vpc_config.value.subnet_ids
      security_group_ids = vpc_config.value.security_group_ids
    }
  }

  # Dead Letter Queue: 처리 실패 메시지를 SQS/SNS로 전송
  # 비동기 호출(SQS trigger 등)에서 재시도 소진 후 메시지를 보존할 때 사용
  dynamic "dead_letter_config" {
    for_each = var.dead_letter_target_arn != null ? [1] : []
    content {
      target_arn = var.dead_letter_target_arn
    }
  }

  # X-Ray 분산 추적
  # PassThrough: 상위 서비스 설정 따름 (기본)
  # Active: 항상 샘플링 활성 (비용 발생)
  tracing_config {
    mode = var.tracing_mode
  }

  depends_on = [aws_cloudwatch_log_group.this]
  tags       = merge(local.default_tags, var.tags)
}

# ── Lambda Alias (live) ───────────────────────────────────────
# 안정적인 ARN 포인터. API Gateway는 alias ARN을 참조하므로
# 새 버전 배포 시 alias만 업데이트하면 됨 (Blue/Green 배포 기반)
resource "aws_lambda_alias" "live" {
  name             = "live"
  function_name    = aws_lambda_function.this.function_name
  function_version = aws_lambda_function.this.version
}

# ── API Gateway 연동 (선택적) ──────────────────────────────────
# api_gateway_route가 null이면 아래 리소스는 모두 생성하지 않음

# Lambda와 API Gateway 연결 설정
resource "aws_apigatewayv2_integration" "this" {
  count                  = local.has_api_route ? 1 : 0
  api_id                 = var.api_gateway_id
  integration_type       = "AWS_PROXY"          # Lambda Proxy: 요청/응답을 그대로 전달
  integration_uri        = aws_lambda_alias.live.invoke_arn
  payload_format_version = "2.0"                # HTTP API v2 포맷 (v1보다 경량)
}

# 라우팅 규칙: "METHOD /path" → integration
resource "aws_apigatewayv2_route" "this" {
  count     = local.has_api_route ? 1 : 0
  api_id    = var.api_gateway_id
  route_key = var.api_gateway_route             # ex) "POST /users"
  target    = "integrations/${aws_apigatewayv2_integration.this[0].id}"
}

# API Gateway가 이 Lambda를 호출할 수 있도록 권한 부여
resource "aws_lambda_permission" "apigw" {
  count         = local.has_api_route ? 1 : 0
  statement_id  = "AllowAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.this.function_name
  qualifier     = aws_lambda_alias.live.name    # alias 단위로 권한 부여
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_execution_arn}/*/*" # 모든 stage/method 허용
}
