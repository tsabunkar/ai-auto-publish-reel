locals {
  orchestrator_name = "ai-content-orchestrator-${var.environment}"
  publisher_name    = "ai-content-publisher-${var.environment}"
}

resource "aws_lambda_function" "orchestrator" {
  function_name = local.orchestrator_name
  role          = aws_iam_role.orchestrator.arn
  handler       = "aws.orchestrator_lambda.handler.handler"
  runtime       = "python3.13"
  timeout       = 300
  memory_size   = 512
  filename      = var.orchestrator_lambda_zip
  source_code_hash = filebase64sha256(var.orchestrator_lambda_zip)

  environment {
    variables = {
      CONTENT_BUCKET   = aws_s3_bucket.content.id
      RSS_FEED_URLS    = var.rss_feed_urls
      BEDROCK_MODEL_ID = var.bedrock_model_id
      POLLY_VOICE_ID   = var.polly_voice_id
      JOB_QUEUE_TOPIC  = "image/generate"
      AWS_REGION       = var.aws_region
    }
  }

  ephemeral_storage {
    size = 512
  }
}

resource "aws_lambda_function" "publisher" {
  function_name = local.publisher_name
  role          = aws_iam_role.publisher.arn
  handler       = "aws.publisher_lambda.handler.handler"
  runtime       = "python3.13"
  timeout       = 600
  memory_size   = 1024
  filename      = var.publisher_lambda_zip
  source_code_hash = filebase64sha256(var.publisher_lambda_zip)

  environment {
    variables = {
      CONTENT_BUCKET          = aws_s3_bucket.content.id
      INSTAGRAM_SECRET_ID     = aws_secretsmanager_secret.instagram.name
      LINKEDIN_SECRET_ID      = aws_secretsmanager_secret.linkedin.name
      YOUTUBE_SECRET_ID       = aws_secretsmanager_secret.youtube.name
      AWS_REGION              = var.aws_region
    }
  }

  ephemeral_storage {
    size = 1024
  }
}
