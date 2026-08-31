output "frontend_url" {
  description = "CloudFront distribution URL for the React demo UI"
  value       = module.frontend.frontend_url
}

output "backend_url" {
  description = "App Runner URL for the FastAPI backend"
  value       = "https://${module.apprunner.service_url}"
}

output "ecr_repository_url" {
  description = "ECR repository URL for pushing the backend image"
  value       = module.ecr.repository_url
}

output "runtime_secret_arn" {
  description = "Secrets Manager ARN for the runtime JSON secret"
  value       = module.secrets.secret_arn
}
