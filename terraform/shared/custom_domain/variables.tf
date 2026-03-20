variable "domain" {
  description = "루트 도메인 (Route53 Hosted Zone). ex) wooapps.net"
  type        = string
}

variable "be_domain" {
  description = "BE 서브도메인. ex) myapp-api.wooapps.net"
  type        = string
}

variable "api_gateway_endpoint" {
  description = "API Gateway 기본 엔드포인트 URL. ex) https://xxxxx.execute-api.ap-northeast-2.amazonaws.com"
  type        = string
}

variable "acm_certificate_arn" {
  description = "CloudFront용 ACM 인증서 ARN (us-east-1)"
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
