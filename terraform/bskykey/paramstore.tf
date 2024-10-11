variable bsky_username {
  type        = string
  #default     = ""
  description = "Bluesky username"
}

variable bsky_apppassword {
  type        = string
  #default     = ""
  description = "Bluesky app password"
}

resource "aws_ssm_parameter" "bsky_username" {
    name = "/resetter/bsky_username"
    type = "String"
    value = var.bsky_username
}

resource "aws_ssm_parameter" "bsky_apppassword" {
    name = "/resetter/bsky_apppassword"
    type = "SecureString"
    value = var.bsky_apppassword
}


output "bsky_username_param_arn" {
    value = aws_ssm_parameter.bsky_username.arn
}
output "bsky_apppassword_param_arn" {
    value = aws_ssm_parameter.bsky_apppassword.arn
}
