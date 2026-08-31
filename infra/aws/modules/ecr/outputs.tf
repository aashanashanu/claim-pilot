output "repository_url" {
  value       = aws_ecr_repository.this.repository_url
  description = "Full ECR repository URL"
}
