variable "service_name" {
  description = "App Runner service name for the backend"
  type        = string
}

variable "repository_url" {
  description = "ECR repository URL for the backend image"
  type        = string
}

variable "runtime_secret_arn" {
  description = "Secrets Manager ARN for the runtime secret JSON"
  type        = string
}

variable "instance_cpu" {
  description = "App Runner CPU units"
  type        = number
  default     = 1024
}

variable "instance_memory" {
  description = "App Runner memory in MB"
  type        = number
  default     = 2048
}
