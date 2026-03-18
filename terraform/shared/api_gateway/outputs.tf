output "id" {
  value = aws_apigatewayv2_api.this.id
}

output "execution_arn" {
  value = aws_apigatewayv2_api.this.execution_arn
}

output "endpoint" {
  value = aws_apigatewayv2_api.this.api_endpoint
}
