variable "project_name" {
  description = "프로젝트 이름"
  type        = string
}

variable "stage" {
  description = "배포 환경 (dev / prod)"
  type        = string
}

variable "aws_region" {
  description = "AWS 리전"
  type        = string
}

variable "aws_account_id" {
  description = "AWS 계정 ID"
  type        = string
}

variable "github_owner" {
  description = "GitHub 유저/org명"
  type        = string
}

variable "fe_domain" {
  description = "프론트엔드 도메인 (CORS 허용 origin). ex) https://my-app.com"
  type        = string
}

variable "tf_state_bucket" {
  description = "Terraform 상태 저장 S3 버킷명. dev.env의 TF_STATE_BUCKET과 동일해야 함"
  type        = string
}




