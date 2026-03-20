output "github_oidc_provider_arn" {
  value = data.aws_iam_openid_connect_provider.github.arn
}
