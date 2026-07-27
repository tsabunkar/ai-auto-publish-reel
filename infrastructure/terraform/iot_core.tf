data "aws_iot_endpoint" "ats" {
  endpoint_type = "iot:Data-ATS"
}

resource "aws_iot_topic_rule" "reel_completed" {
  name        = "reel_completed_${var.environment}"
  enabled     = true
  sql         = "SELECT * FROM 'reel/completed'"
  sql_version = "2016-03-23"

  lambda {
    function_arn = aws_lambda_function.publisher.arn
  }
}

resource "aws_lambda_permission" "iot_publisher" {
  statement_id  = "AllowIoTInvokePublisherLambda"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.publisher.function_name
  principal     = "iot.amazonaws.com"
  source_arn    = aws_iot_topic_rule.reel_completed.arn
}
