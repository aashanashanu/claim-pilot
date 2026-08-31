variable "aws_region" {
  description = "AWS region used for the demo deployment"
  type        = string
  default     = "us-west-2"
}

variable "frontend_bucket_name" {
  description = "Globally unique S3 bucket name for the static frontend"
  type        = string
  default     = "claimpilot-demo-frontend"
}

variable "ecr_repository_name" {
  description = "ECR repository name for the FastAPI backend image"
  type        = string
  default     = "claimpilot-backend-demo"
}

variable "app_runner_service_name" {
  description = "App Runner service name for the demo backend"
  type        = string
  default     = "claimpilot-backend-demo"
}

variable "runtime_secret_name" {
  description = "Secrets Manager name for the runtime configuration JSON"
  type        = string
  default     = "claimpilot/runtime-config"
}

variable "runtime_secrets" {
  description = "Runtime configuration and secrets encoded into one JSON object and stored in Secrets Manager"
  type = object({
    aws_access_key_id      = string
    aws_secret_access_key  = string
    aws_session_token      = string
    claimpilot_model_id    = string
    gmail_credentials_json = string
    gmail_token_json       = string
    gmail_target_address   = string
    gmail_query            = string
  })
  sensitive = true
}
