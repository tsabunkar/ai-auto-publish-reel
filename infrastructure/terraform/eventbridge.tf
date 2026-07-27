resource "aws_cloudwatch_event_rule" "weekly_schedule" {
  name                = "ai-content-weekly-${var.environment}"
  description         = "Triggers orchestrator Lambda every Monday at 10:00 AM IST"
  schedule_expression = var.schedule_expression
}

resource "aws_cloudwatch_event_target" "orchestrator" {
  rule      = aws_cloudwatch_event_rule.weekly_schedule.name
  target_id = "OrchestratorLambda"
  arn       = aws_lambda_function.orchestrator.arn
}

resource "aws_lambda_permission" "eventbridge_orchestrator" {
  statement_id  = "AllowEventBridgeInvokeOrchestrator"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.orchestrator.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.weekly_schedule.arn
}
