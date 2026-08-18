variable "name" {
  type = string
}

variable "schedule_expression" {
  type = string
}

variable "lambda_arn" {
  type = string
}

variable "lambda_name" {
  type = string
}

variable "payload" {
  type = string
}

resource "aws_cloudwatch_event_rule" "this" {
  name                = var.name
  schedule_expression = var.schedule_expression
}

resource "aws_cloudwatch_event_target" "this" {
  rule      = aws_cloudwatch_event_rule.this.name
  target_id = var.name
  arn       = var.lambda_arn
  input     = var.payload
}

resource "aws_lambda_permission" "this" {
  statement_id  = "AllowExecutionFrom-${var.name}"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.this.arn
}
