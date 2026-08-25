output "frontend_url" {
  description = "CloudFront distribution URL for the React demo UI"
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "backend_url" {
  description = "App Runner URL for the FastAPI backend"
  value       = "https://${aws_apprunner_service.backend.service_url}"
}

output "ecr_repository_url" {
  description = "ECR repository URL for pushing the backend image"
  value       = aws_ecr_repository.backend.repository_url
}
