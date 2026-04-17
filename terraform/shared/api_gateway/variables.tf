variable "project_name" { type = string }
variable "stage"        { type = string }

variable "fe_url" {
  description = "프론트엔드 풀 URL (CORS 허용 origin). 스킴 포함. ex) https://example.com"
  type        = string
}

variable "cors_extra_origins" {
  description = "추가 CORS 허용 origin 목록. dev 로컬 개발 시 http://localhost:5173 등 추가"
  type        = list(string)
  default     = []
}

variable "cors_allow_methods" {
  type    = list(string)
  default = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
}

variable "cors_allow_headers" {
  type    = list(string)
  default = ["Content-Type", "Authorization"]
}

variable "cors_max_age" {
  type    = number
  default = 300
}

variable "throttling_burst_limit" {
  description = "API Gateway 최대 동시 요청 수 (버스트). 초과 시 429 반환"
  type        = number
  default     = 200
}

variable "throttling_rate_limit" {
  description = "API Gateway 초당 최대 요청 수 (steady-state). 초과 시 429 반환"
  type        = number
  default     = 100
}

variable "tags" {
  type    = map(string)
  default = {}
}
