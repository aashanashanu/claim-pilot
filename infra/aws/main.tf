terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  repo_root     = abspath("${path.module}/../..")
  frontend_dir  = "${local.repo_root}/frontend"
  backend_build = "${local.repo_root}"
}

module "ecr" {
  source           = "./modules/ecr"
  repository_name  = var.ecr_repository_name
}

module "frontend" {
  source      = "./modules/frontend"
  bucket_name = var.frontend_bucket_name
}

module "secrets" {
  source           = "./modules/secrets"
  secret_name      = var.runtime_secret_name
  runtime_secrets  = var.runtime_secrets
}

resource "null_resource" "backend_artifact" {
  triggers = {
    repository_url = module.ecr.repository_url
    deploy_stamp   = timestamp()
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -euo pipefail
      aws ecr get-login-password --region "${var.aws_region}" | docker login --username AWS --password-stdin "${split("/", module.ecr.repository_url)[0]}"
      docker build -t "${var.ecr_repository_name}:latest" "${local.backend_build}"
      docker tag "${var.ecr_repository_name}:latest" "${module.ecr.repository_url}:latest"
      docker push "${module.ecr.repository_url}:latest"
    EOT
  }
}

module "apprunner" {
  source             = "./modules/apprunner"
  service_name       = var.app_runner_service_name
  repository_url     = module.ecr.repository_url
  runtime_secret_arn  = module.secrets.secret_arn

  depends_on = [null_resource.backend_artifact]
}

resource "null_resource" "frontend_artifact" {
  triggers = {
    backend_url  = module.apprunner.service_url
    deploy_stamp = timestamp()
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -euo pipefail
      cd "${local.frontend_dir}"
      npm install
      VITE_API_BASE="https://${module.apprunner.service_url}" npm run build
      aws s3 sync "${local.frontend_dir}/dist" "s3://${module.frontend.bucket_name}" --delete
    EOT
  }

  depends_on = [module.apprunner]
}
