variable "project_name" {
  description = "프로젝트 이름"
  type        = string
  default     = "{{PROJECT_NAME}}"
}

variable "stage" {
  description = "배포 환경 (dev / stage / prod)"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS 리전"
  type        = string
  default     = "{{AWS_REGION}}"
}

variable "aws_account_id" {
  description = "AWS 계정 ID"
  type        = string
  default     = "{{AWS_ACCOUNT_ID}}"
}

variable "github_owner" {
  description = "GitHub 유저/org명"
  type        = string
  default     = "{{GITHUB_OWNER}}"
}

variable "fe_domain" {
  description = "프론트엔드 도메인 (CORS 허용 origin). ex) https://example.com"
  type        = string
  default     = "https://{{FE_DOMAIN}}"
}
