variable slack_web_hook_url {
  type        = string
  #default     = ""
  description = "Slack web hook URL"
}

resource "aws_ssm_parameter" "slack_web_hook_url" {
    name = "/resetter/slack_web_hook_url"
    type = "SecureString"
    value = var.slack_web_hook_url
}

output "slack_web_hook_param_arn" {
    value = aws_ssm_parameter.slack_web_hook_url.arn
}
