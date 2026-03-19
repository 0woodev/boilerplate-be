variable "aws_region" {
  type = string
}

variable "project_name" {
  type = string
}

variable "github_owner" {
  type = string
}

variable "aws_account_id" {
  type = string
}

variable "tf_state_bucket" {
  type = string
}

variable "stages" {
  type    = list(string)
  default = ["dev", "prod"]
}
