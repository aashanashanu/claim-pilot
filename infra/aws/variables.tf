variable "aws_region" {
  description = "AWS region used for the demo deployment"
  type        = string
  default     = "us-west-2"
}

variable "aws_access_key_id" {
  description = "AWS access key used by the App Runner Strands runtime for Bedrock access"
  type        = string
  default     = ""
  sensitive   = true
}

variable "aws_secret_access_key" {
  description = "AWS secret key used by the App Runner Strands runtime for Bedrock access"
  type        = string
  default     = ""
  sensitive   = true
}

variable "aws_session_token" {
  description = "Optional AWS session token used by the App Runner Strands runtime"
  type        = string
  default     = ""
  sensitive   = true
}

variable "claimpilot_model_id" {
  description = "Bedrock model ID used by the Strands agent in this demo"
  type        = string
  default     = "global.anthropic.claude-sonnet-4-6"
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
