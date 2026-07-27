variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "content_bucket_name" {
  description = "Name of the S3 bucket for content storage"
  type        = string
}

variable "rss_feed_urls" {
  description = "Comma-separated RSS feed URLs for the orchestrator"
  type        = string
  default     = "https://feeds.hbr.org/harvardbusiness,https://www.forbes.com/leadership/feed/"
}

variable "bedrock_model_id" {
  description = "Amazon Bedrock model ID for content generation"
  type        = string
  default     = "anthropic.claude-3-5-sonnet-20241022-v2:0"
}

variable "polly_voice_id" {
  description = "Amazon Polly voice ID for narration"
  type        = string
  default     = "Matthew"
}

variable "orchestrator_lambda_zip" {
  description = "Path to orchestrator Lambda deployment package"
  type        = string
  default     = "../../build/orchestrator.zip"
}

variable "publisher_lambda_zip" {
  description = "Path to publisher Lambda deployment package"
  type        = string
  default     = "../../build/publisher.zip"
}

variable "schedule_expression" {
  description = "EventBridge cron expression for orchestrator schedule"
  type        = string
  default     = "cron(30 4 ? * MON *)"
}
