resource "aws_iam_role" "orchestrator" {
  name               = "ai-content-orchestrator-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role" "publisher" {
  name               = "ai-content-publisher-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_policy" "orchestrator" {
  name   = "ai-content-orchestrator-policy-${var.environment}"
  policy = data.aws_iam_policy_document.orchestrator.json
}

resource "aws_iam_policy" "publisher" {
  name   = "ai-content-publisher-policy-${var.environment}"
  policy = data.aws_iam_policy_document.publisher.json
}

data "aws_iam_policy_document" "orchestrator" {
  statement {
    actions   = ["s3:PutObject", "s3:GetObject"]
    resources = ["${aws_s3_bucket.content.arn}/*"]
  }
  statement {
    actions   = ["bedrock:InvokeModel"]
    resources = ["arn:aws:bedrock:${var.aws_region}::foundation-model/${var.bedrock_model_id}"]
  }
  statement {
    actions   = ["polly:SynthesizeSpeech"]
    resources = ["*"]
  }
  statement {
    actions   = ["iot:Publish"]
    resources = ["arn:aws:iot:${var.aws_region}:${data.aws_caller_identity.current.account_id}:topic/${var.job_queue_topic}"]
  }
  statement {
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/ai-content-orchestrator-*:*"]
  }
}

data "aws_iam_policy_document" "publisher" {
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.content.arn}/*"]
  }
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [
      aws_secretsmanager_secret.instagram.arn,
      aws_secretsmanager_secret.linkedin.arn,
      aws_secretsmanager_secret.youtube.arn,
    ]
  }
  statement {
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/ai-content-publisher-*:*"]
  }
}

resource "aws_iam_role_policy_attachment" "orchestrator" {
  role       = aws_iam_role.orchestrator.name
  policy_arn = aws_iam_policy.orchestrator.arn
}

resource "aws_iam_role_policy_attachment" "publisher" {
  role       = aws_iam_role.publisher.name
  policy_arn = aws_iam_policy.publisher.arn
}

resource "aws_iam_role_policy_attachment" "orchestrator_basic_exec" {
  role       = aws_iam_role.orchestrator.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "publisher_basic_exec" {
  role       = aws_iam_role.publisher.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_caller_identity" "current" {}
