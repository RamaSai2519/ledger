output "api_url" {
  value = aws_apigatewayv2_stage.default.invoke_url
}

output "region" {
  value = data.aws_region.current.name
}
