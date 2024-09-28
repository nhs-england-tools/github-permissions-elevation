data "aws_iam_policy_document" "assume_lambda_role_github_permission_manager_demotion" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "github_permission_manager_demotion" {
  name               = "AssumeLambdaRole_github_permission_manager_demotion"
  description        = "Role for lambda to assume lambda"
  assume_role_policy = data.aws_iam_policy_document.assume_lambda_role_github_permission_manager_demotion.json
}

data "aws_iam_policy_document" "allow_lambda_logging_github_permission_manager_demotion" {
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
      aws_ssm_parameter.github_permission_manager_webhook_app_id.arn,
      aws_ssm_parameter.github_permission_manager_webhook_private_key.arn,
      aws_ssm_parameter.github_permission_manager_webhook_installation_id.arn,
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:GetItem",
    ]
    resources = [
      aws_dynamodb_table.elevation_requests.arn,
    ]
  }
}

resource "aws_iam_policy" "function_logging_policy_github_permission_manager_demotion" {
  name        = "AllowLambdaLoggingPolicy_github_permission_manager_demotion"
  description = "Policy for lambda cloudwatch logging"
  policy      = data.aws_iam_policy_document.allow_lambda_logging_github_permission_manager_demotion.json
}

resource "aws_iam_role_policy_attachment" "lambda_logging_policy_attachment_github_permission_manager_demotion" {
  role       = aws_iam_role.github_permission_manager_demotion.id
  policy_arn = aws_iam_policy.function_logging_policy_github_permission_manager_demotion.arn
}

resource "aws_iam_role" "step_functions_exec" {
  name = "github-permission-manager-step-functions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "step_functions_lambda" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaRole"
  role       = aws_iam_role.step_functions_exec.name
}
