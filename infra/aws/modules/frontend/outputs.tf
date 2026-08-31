output "bucket_name" {
  value       = aws_s3_bucket.this.bucket
  description = "Frontend bucket name"
}

output "distribution_domain_name" {
  value       = aws_cloudfront_distribution.this.domain_name
  description = "CloudFront distribution domain name"
}

output "distribution_id" {
  value       = aws_cloudfront_distribution.this.id
  description = "CloudFront distribution ID"
}

output "frontend_url" {
  value       = "https://${aws_cloudfront_distribution.this.domain_name}"
  description = "CloudFront URL for the frontend"
}
