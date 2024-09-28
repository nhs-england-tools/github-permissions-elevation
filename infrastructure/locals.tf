locals {
  github_permission_manager_webhook_function_name = "github_permission_manager_webhook"
  github_permission_manager_webhook_archive_path = "${path.module}/tf_generated/${local.github_permission_manager_webhook_function_name}.zip"

  github_permission_manager_demotion_function_name = "github_permission_manager_demotion"
  github_permission_manager_demotion_archive_path = "${path.module}/tf_generated/${local.github_permission_manager_demotion_function_name}.zip"
}