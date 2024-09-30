resource "aws_apigatewayv2_api" "github_permission_manager_webhook" {
  name          = "${terraform.workspace}_github_permission_manager_webhook"
  protocol_type = "HTTP"
  description   = "Serverless API gateway for HTTP API and AWS Lambda function python"

  cors_configuration {
    allow_headers = ["*"]
    allow_methods = [
      "GET",
      "POST",
    ]
    allow_origins = [
      "*"
    ]
    expose_headers = []
    max_age        = 0
  }
}

resource "aws_apigatewayv2_stage" "github_permission_manager_webhook" {
  api_id = aws_apigatewayv2_api.github_permission_manager_webhook.id

  name        = "${terraform.workspace}_github_permission_manager_webhook"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.github_permission_manager_webhook.arn

    format = jsonencode({
      requestId               = "$context.requestId"
      sourceIp                = "$context.identity.sourceIp"
      requestTime             = "$context.requestTime"
      protocol                = "$context.protocol"
      httpMethod              = "$context.httpMethod"
      resourcePath            = "$context.resourcePath"
      routeKey                = "$context.routeKey"
      status                  = "$context.status"
      responseLength          = "$context.responseLength"
      integrationErrorMessage = "$context.integrationErrorMessage"
      }
    )
  }
  depends_on = [aws_cloudwatch_log_group.github_permission_manager_webhook]
}

resource "aws_cloudwatch_log_group" "github_permission_manager_webhook" {
  name = "/aws/api_gw/${aws_apigatewayv2_api.github_permission_manager_webhook.name}"

  retention_in_days = 30
}

resource "aws_apigatewayv2_integration" "github_permission_manager_webhook_lambda" {
  api_id = aws_apigatewayv2_api.github_permission_manager_webhook.id

  integration_uri  = aws_lambda_function.github_permission_manager_webhook.arn
  integration_type = "AWS_PROXY"

}

resource "aws_apigatewayv2_route" "github_permission_manager_webhook_lambda" {
  api_id    = aws_apigatewayv2_api.github_permission_manager_webhook.id
  route_key = "POST /api/v1/github_permission_manager_webhook"
  target    = "integrations/${aws_apigatewayv2_integration.github_permission_manager_webhook_lambda.id}"
}

resource "aws_lambda_permission" "github_permission_manager_webhook_lambda" {
  statement_id  = "github_permission_manager_webhook"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.github_permission_manager_webhook.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_apigatewayv2_api.github_permission_manager_webhook.execution_arn}/*/*"
}

output "github_permission_manager_webhook_full_url" {
  value = "${aws_apigatewayv2_api.github_permission_manager_webhook.api_endpoint}/${aws_apigatewayv2_stage.github_permission_manager_webhook.name}/api/v1/github_permission_manager_webhook"
}
