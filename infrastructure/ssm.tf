resource "aws_ssm_parameter" "github_permission_manager_webhook_private_key" {
  name  = "/github_permission_manager_webhook/private_key"
  type  = "SecureString"
  value = "ReplaceMe"

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "github_permission_manager_webhook_app_id" {
  name  = "/github_permission_manager_webhook/app_id"
  type  = "SecureString"
  value = "ReplaceMe"

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "github_permission_manager_webhook_installation_id" {
  name  = "/github_permission_manager_webhook/installation_id"
  type  = "SecureString"
  value = "ReplaceMe"

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "github_permission_manager_webhook_secret" {
  name  = "/github_permission_manager_webhook/secret"
  type  = "SecureString"
  value = "ReplaceMe"

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "github_permission_manager_webhook_secret_for_webhook" {
  name  = "/github_permission_manager_webhook/secret_for_webhook"
  type  = "SecureString"
  value = "ReplaceMe"

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "github_permission_manager_demotion_step_function_arn" {
  name  = "/github_permission_manager_demotion/step_function_arn"
  type  = "SecureString"
  value = aws_sfn_state_machine.user_demotion.arn
}