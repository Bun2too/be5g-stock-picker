resource "aws_iam_user" "railway_api" {
  count = var.create_railway_api_user ? 1 : 0
  name  = "${local.name_prefix}-railway-api"
  tags  = local.common_tags
}

resource "aws_iam_user_policy" "railway_api" {
  count = var.create_railway_api_user ? 1 : 0
  name  = "${local.name_prefix}-dynamodb-access"
  user  = aws_iam_user.railway_api[0].name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:BatchGetItem",
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:UpdateItem"
        ]
        Resource = [
          aws_dynamodb_table.symbols.arn,
          aws_dynamodb_table.ranked_picks.arn,
          aws_dynamodb_table.portfolios.arn
        ]
      }
    ]
  })
}
