variable "project_name" { type = string }
variable "stage"        { type = string }

variable "fe_domain" {
  description = "프론트엔드 도메인 (CORS 허용 origin). ex) https://example.com"
  type        = string
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

variable "tags" {
  type    = map(string)
  default = {}
}
