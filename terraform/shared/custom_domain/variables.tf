variable "domain" {
  description = "루트 도메인 (Route53 Hosted Zone). ex) wooapps.net"
  type        = string
}

variable "be_domain" {
  description = "BE 서브도메인. ex) myapp-api.wooapps.net"
  type        = string
}

variable "api_gateway_id" {
  description = "API Gateway ID"
  type        = string
}

variable "project_name" {
  type = string
}

variable "stage" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
