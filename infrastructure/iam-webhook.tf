data "aws_iam_policy_document" "assume_lambda_role_github_permission_manager_webhook" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "github_permission_manager_webhook" {
  name               = "AssumeLambdaRole_github_permission_manager_webhook"
  description        = "Role for lambda to assume lambda"
  assume_role_policy = data.aws_iam_policy_document.assume_lambda_role_github_permission_manager_webhook.json
}

data "aws_iam_policy_document" "allow_lambda_logging_github_permission_manager_webhook" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = [
      "arn:aws:logs:*:*:*",
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "ssm:GetParameter",
    ]
    resources = [
      aws_ssm_parameter.github_permission_manager_webhook_secret_for_webhook.arn,
      aws_ssm_parameter.github_permission_manager_webhook_app_id.arn,
      aws_ssm_parameter.github_permission_manager_webhook_private_key.arn,
      aws_ssm_parameter.github_permission_manager_demotion_step_function_arn.arn,
      aws_ssm_parameter.github_permission_manager_webhook_installation_id.arn,
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:GetItem",
      "dynamodb:UpdateItem",
      "dynamodb:Query",
    ]
    resources = [
      aws_dynamodb_table.elevation_requests.arn,
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "states:StartExecution",
    ]
    resources = [
      aws_sfn_state_machine.user_demotion.arn,
    ]
  }
}

resource "aws_iam_policy" "function_logging_policy_github_permission_manager_webhook" {
  name        = "AllowLambdaLoggingPolicy_github_permission_manager_webhook"
  description = "Policy for lambda cloudwatch logging"
  policy      = data.aws_iam_policy_document.allow_lambda_logging_github_permission_manager_webhook.json
}

resource "aws_iam_role_policy_attachment" "lambda_logging_policy_attachment_github_permission_manager_webhook" {
  role       = aws_iam_role.github_permission_manager_webhook.id
  policy_arn = aws_iam_policy.function_logging_policy_github_permission_manager_webhook.arn
}
