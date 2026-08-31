output "secret_arn" {
  value       = aws_secretsmanager_secret.runtime.arn
  description = "Runtime secret ARN"
}
