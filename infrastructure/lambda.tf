resource "aws_lambda_function" "github_permission_manager_webhook" {
  function_name = local.github_permission_manager_webhook_function_name
  description   = "handles requests to elevate permissions"
  role          = aws_iam_role.github_permission_manager_webhook.arn
  handler       = "handler.handler"
  memory_size   = 128
  runtime       = "python3.12"
  architectures = ["x86_64"]
  timeout       = 30

  filename         = local.github_permission_manager_webhook_archive_path
  source_code_hash = filebase64sha256(local.github_permission_manager_webhook_archive_path)

  environment {
    variables = {
      ELEVATION_DURATION = "300"
      STEP_FUNCTION_ARN  = aws_sfn_state_machine.user_demotion.arn
    }
  }
}

resource "aws_cloudwatch_log_group" "github_permission_manager_webhook_log_group" {
  name              = "/aws/lambda/${aws_lambda_function.github_permission_manager_webhook.function_name}"
  retention_in_days = 7
}

resource "aws_lambda_function" "github_permission_manager_demotion" {
  function_name = "github_permission_manager_demotion"
  description   = "demotes users back to normal members"
  role          = aws_iam_role.github_permission_manager_demotion.arn
  handler       = "handler.handler"
  memory_size   = 128
  runtime       = "python3.12"
  architectures = ["x86_64"]
  timeout       = 30

  filename         = local.github_permission_manager_demotion_archive_path
  source_code_hash = filebase64sha256(local.github_permission_manager_demotion_archive_path)

}

resource "aws_cloudwatch_log_group" "github_permission_manager_demotion_log_group" {
  name              = "/aws/lambda/${aws_lambda_function.github_permission_manager_demotion.function_name}"
  retention_in_days = 7
}
