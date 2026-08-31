resource "aws_secretsmanager_secret" "runtime" {
  name = var.secret_name
}

resource "aws_secretsmanager_secret_version" "runtime" {
  secret_id     = aws_secretsmanager_secret.runtime.id
  secret_string = jsonencode(var.runtime_secrets)
}
