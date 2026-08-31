variable "secret_name" {
  description = "Name of the runtime secret stored in Secrets Manager"
  type        = string
}

variable "runtime_secrets" {
  description = "Runtime secrets and configuration encoded into a single JSON object"
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
