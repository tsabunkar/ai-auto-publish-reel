data "aws_iot_endpoint" "ats" {
  endpoint_type = "iot:Data-ATS"
}

resource "aws_iot_topic_rule" "image_completed" {
  name        = "image_completed_${var.environment}"
  enabled     = true
  sql         = "SELECT * FROM 'image/completed'"
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
  source_arn    = aws_iot_topic_rule.image_completed.arn
}

resource "aws_iot_policy" "macbook_controller" {
  name = "macbook_controller_${var.environment}"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "iot:Connect",
        "iot:Subscribe",
        "iot:Receive",
        "iot:Publish",
      ]
      Resource = [
        "arn:aws:iot:${var.aws_region}:${data.aws_caller_identity.current.account_id}:client/macbook-control-plane",
        "arn:aws:iot:${var.aws_region}:${data.aws_caller_identity.current.account_id}:topicfilter/${var.job_queue_topic}",
        "arn:aws:iot:${var.aws_region}:${data.aws_caller_identity.current.account_id}:topicfilter/image/completed",
        "arn:aws:iot:${var.aws_region}:${data.aws_caller_identity.current.account_id}:topic/image/completed",
      ]
    }]
  })
}
