variable "project_name" { type = string }
variable "stage"        { type = string }

variable "api_gateway_id" {
  description = "연결할 API Gateway v2 ID"
  type        = string
}

variable "api_gateway_execution_arn" {
  description = "API Gateway execution ARN (Lambda permission용)"
  type        = string
}

variable "common_layer_arns" {
  description = "공통 Lambda Layer ARN 목록"
  type        = list(string)
  default     = []
}

variable "tags" {
  type    = map(string)
  default = {}
}
