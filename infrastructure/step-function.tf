resource "aws_sfn_state_machine" "user_demotion" {
  name     = "github-user-demotion"
  role_arn = aws_iam_role.step_functions_exec.arn

  definition = jsonencode({
    Comment = "A state machine that waits and then demotes a GitHub user"
    StartAt = "Wait"
    States = {
      Wait = {
        Type        = "Wait"
        SecondsPath = "$.wait_seconds"
        Next        = "DemoteUser"
      }
      DemoteUser = {
        Type     = "Task"
        Resource = aws_lambda_function.github_permission_manager_demotion.arn
        End      = true
      }
    }
  })
}
