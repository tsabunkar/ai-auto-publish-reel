output "content_bucket" {
  description = "S3 bucket for content storage"
  value       = aws_s3_bucket.content.id
}

output "orchestrator_lambda_arn" {
  description = "Orchestrator Lambda function ARN"
  value       = aws_lambda_function.orchestrator.arn
}

output "publisher_lambda_arn" {
  description = "Publisher Lambda function ARN"
  value       = aws_lambda_function.publisher.arn
}

output "iot_endpoint" {
  description = "AWS IoT Core MQTT endpoint"
  value       = data.aws_iot_endpoint.ats.endpoint_address
}

output "iot_completed_rule_arn" {
  description = "IoT Topic Rule ARN for reel/completed"
  value       = aws_iot_topic_rule.reel_completed.arn
}
