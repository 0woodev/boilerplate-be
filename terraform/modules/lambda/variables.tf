variable "project_name" { type = string }
variable "stage"        { type = string }

variable "name" {
  description = "Lambda 함수 식별자. 실제 함수명: {project}-{stage}-{name}"
  type        = string
}

# ── 소스 ────────────────────────────────────────────────────
variable "zip_path" {
  description = "Lambda zip 파일 경로. s3_bucket이 null이면 로컬 파일, 있으면 S3 key"
  type        = string
}

variable "s3_bucket" {
  description = "zip이 S3에 있을 경우 버킷명. null이면 로컬 zip 사용"
  type        = string
  default     = null
}

variable "handler" {
  description = "ex) app.lambdas.user.create_user.handler"
  type        = string
}

variable "runtime" {
  type    = string
  default = "python3.12"
}

# ── 리소스 ──────────────────────────────────────────────────
variable "memory_size" {
  type    = number
  default = 128
}

variable "timeout" {
  type    = number
  default = 30
}

variable "ephemeral_storage_size" {
  description = "/tmp 스토리지 (MB). 512~10240"
  type        = number
  default     = 512
}

variable "reserved_concurrent_executions" {
  description = "-1 이면 제한 없음"
  type        = number
  default     = -1
}

variable "publish" {
  description = "버전 발행 여부. alias 사용 시 true 필요"
  type        = bool
  default     = true
}

# ── 환경변수 / 레이어 ────────────────────────────────────────
variable "environment_variables" {
  type    = map(string)
  default = {}
}

variable "layer_arns" {
  type    = list(string)
  default = []
}

# ── 네트워킹 ─────────────────────────────────────────────────
variable "vpc_config" {
  type = object({
    subnet_ids         = list(string)
    security_group_ids = list(string)
  })
  default = null
}

# ── IAM ──────────────────────────────────────────────────────
variable "additional_policy_arns" {
  description = "추가로 attach 할 managed policy ARN 목록"
  type        = list(string)
  default     = []
}

variable "inline_policies" {
  description = "인라인 정책. map key = 정책명, value = JSON string"
  type        = map(string)
  default     = {}
}

# ── Dead Letter Queue ─────────────────────────────────────────
variable "dead_letter_target_arn" {
  description = "DLQ SQS ARN 또는 SNS ARN. null이면 미설정"
  type        = string
  default     = null
}

# ── 관찰 가능성 ───────────────────────────────────────────────
variable "tracing_mode" {
  description = "PassThrough | Active"
  type        = string
  default     = "PassThrough"
}

variable "log_retention_days" {
  type    = number
  default = 14
}

# ── API Gateway 연동 ──────────────────────────────────────────
variable "api_gateway_id" {
  description = "연결할 API Gateway v2 ID. null이면 미연결"
  type        = string
  default     = null
}

variable "api_gateway_execution_arn" {
  description = "API Gateway execution ARN (lambda permission용)"
  type        = string
  default     = null
}

variable "api_gateway_route" {
  description = "ex) POST /users   GET /users/{id}   null이면 route 미생성"
  type        = string
  default     = null
}

# ── 공통 태그 ────────────────────────────────────────────────
variable "tags" {
  type    = map(string)
  default = {}
}
