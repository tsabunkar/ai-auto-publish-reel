resource "aws_cloudwatch_log_group" "orchestrator" {
  name              = "/aws/lambda/ai-content-orchestrator-${var.environment}"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "publisher" {
  name              = "/aws/lambda/ai-content-publisher-${var.environment}"
  retention_in_days = 7
}
