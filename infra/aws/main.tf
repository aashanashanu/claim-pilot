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

resource "aws_ecr_repository" "backend" {
  name                 = var.ecr_repository_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_s3_bucket" "frontend" {
  bucket        = var.frontend_bucket_name
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_cloudfront_origin_access_control" "frontend" {
  name                              = "claimpilot-frontend-oac"
  description                       = "Origin access control for ClaimPilot frontend bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "frontend" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  http_version        = "http2and3"
  price_class         = "PriceClass_100"

  origin {
    origin_id   = "s3-origin"
    domain_name = aws_s3_bucket.frontend.bucket_regional_domain_name

    origin_access_control_id = aws_cloudfront_origin_access_control.frontend.id
    s3_origin_config {
      origin_access_identity = ""
    }
  }

  default_cache_behavior {
    target_origin_id       = "s3-origin"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
  }

  custom_error_response {
    error_code            = 403
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }

  custom_error_response {
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

resource "aws_iam_role" "apprunner_ecr" {
  name = "claimpilot-apprunner-ecr-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "build.apprunner.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "apprunner_ecr" {
  role = aws_iam_role.apprunner_ecr.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role" "apprunner_instance" {
  name = "claimpilot-apprunner-instance-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "tasks.apprunner.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "apprunner_instance" {
  role = aws_iam_role.apprunner_instance.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "kms:Decrypt"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:Converse",
          "bedrock:ConverseStream"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_secretsmanager_secret" "strands_access_key" {
  name = "claimpilot/strands/aws_access_key_id"
}

resource "aws_secretsmanager_secret_version" "strands_access_key" {
  secret_id     = aws_secretsmanager_secret.strands_access_key.id
  secret_string = var.aws_access_key_id
}

resource "aws_secretsmanager_secret" "strands_secret_key" {
  name = "claimpilot/strands/aws_secret_access_key"
}

resource "aws_secretsmanager_secret_version" "strands_secret_key" {
  secret_id     = aws_secretsmanager_secret.strands_secret_key.id
  secret_string = var.aws_secret_access_key
}

resource "aws_secretsmanager_secret" "strands_session_token" {
  name = "claimpilot/strands/aws_session_token"
}

resource "aws_secretsmanager_secret_version" "strands_session_token" {
  secret_id     = aws_secretsmanager_secret.strands_session_token.id
  secret_string = var.aws_session_token
}

resource "aws_apprunner_service" "backend" {
  service_name = var.app_runner_service_name

  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_ecr.arn
    }

    image_repository {
      image_identifier      = "${aws_ecr_repository.backend.repository_url}:latest"
      image_repository_type = "ECR"

      image_configuration {
        port = "8000"
        runtime_environment_variables = {
          CLAIMPILOT_ENV      = "aws-demo"
          AWS_REGION          = var.aws_region
          CLAIMPILOT_MODEL_ID = var.claimpilot_model_id
        }
        runtime_environment_secrets = {
          AWS_ACCESS_KEY_ID     = aws_secretsmanager_secret.strands_access_key.arn
          AWS_SECRET_ACCESS_KEY = aws_secretsmanager_secret.strands_secret_key.arn
          AWS_SESSION_TOKEN     = aws_secretsmanager_secret.strands_session_token.arn
        }
      }
    }

    auto_deployments_enabled = false
  }

  instance_configuration {
    cpu              = 1024
    memory           = 2048
    instance_role_arn = aws_iam_role.apprunner_instance.arn
  }

  tags = {
    Project          = "ClaimPilot"
    Tier             = "demo"
    Runtime          = "strands"
    DecisionBackend  = "bedrock"
  }
}
