locals {
  name_prefix        = "${var.project_name}-${var.environment}"
  create_github_oidc = var.github_owner != "" && var.github_repo != ""

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

data "archive_file" "market_jobs" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda/market_jobs"
  output_path = "${path.module}/.terraform-build/market_jobs.zip"
}

resource "aws_dynamodb_table" "symbols" {
  name         = "${local.name_prefix}-symbols"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "market"
  range_key    = "symbol"

  attribute {
    name = "market"
    type = "S"
  }

  attribute {
    name = "symbol"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = local.common_tags
}

resource "aws_dynamodb_table" "market_snapshots" {
  name         = "${local.name_prefix}-market-snapshots"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "symbol"
  range_key    = "asOf"

  attribute {
    name = "symbol"
    type = "S"
  }

  attribute {
    name = "asOf"
    type = "S"
  }

  ttl {
    attribute_name = "expiresAt"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = local.common_tags
}

resource "aws_dynamodb_table" "ranked_picks" {
  name         = "${local.name_prefix}-ranked-picks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "universe"
  range_key    = "scoreKey"

  attribute {
    name = "universe"
    type = "S"
  }

  attribute {
    name = "scoreKey"
    type = "S"
  }

  ttl {
    attribute_name = "expiresAt"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = local.common_tags
}

resource "aws_dynamodb_table" "portfolios" {
  name         = "${local.name_prefix}-portfolios"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "ownerKey"

  attribute {
    name = "ownerKey"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = local.common_tags
}

resource "aws_secretsmanager_secret" "alpaca" {
  name        = "${local.name_prefix}/alpaca"
  description = "Alpaca API credentials for scheduled market data jobs."
  tags        = local.common_tags
}

resource "aws_iam_role" "lambda" {
  name = "${local.name_prefix}-market-jobs-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "lambda" {
  name = "${local.name_prefix}-market-jobs"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:BatchWriteItem",
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:UpdateItem"
        ]
        Resource = [
          aws_dynamodb_table.symbols.arn,
          aws_dynamodb_table.market_snapshots.arn,
          aws_dynamodb_table.ranked_picks.arn,
          aws_dynamodb_table.portfolios.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.alpaca.arn
      }
    ]
  })
}

resource "aws_lambda_function" "market_jobs" {
  function_name    = "${local.name_prefix}-market-jobs"
  role             = aws_iam_role.lambda.arn
  handler          = "app.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.market_jobs.output_path
  source_code_hash = data.archive_file.market_jobs.output_base64sha256
  timeout          = 300
  memory_size      = 512

  environment {
    variables = {
      SYMBOLS_TABLE                  = aws_dynamodb_table.symbols.name
      SNAPSHOTS_TABLE                = aws_dynamodb_table.market_snapshots.name
      RANKED_PICKS_TABLE             = aws_dynamodb_table.ranked_picks.name
      ALPACA_SECRET_ARN              = aws_secretsmanager_secret.alpaca.arn
      ALPACA_DATA_FEED               = var.alpaca_data_feed
      MAX_SYMBOLS_CATALOG            = tostring(var.max_symbols_catalog)
      MAX_SYMBOLS_PER_MARKET_REFRESH = tostring(var.max_symbols_per_refresh)
    }
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "market_jobs" {
  name              = "/aws/lambda/${aws_lambda_function.market_jobs.function_name}"
  retention_in_days = 14
  tags              = local.common_tags
}

module "symbol_refresh_schedule" {
  source              = "./modules/lambda_schedule"
  name                = "${local.name_prefix}-refresh-symbols"
  schedule_expression = var.symbol_refresh_schedule
  lambda_arn          = aws_lambda_function.market_jobs.arn
  lambda_name         = aws_lambda_function.market_jobs.function_name
  payload             = jsonencode({ job = "refresh_symbols" })
}

module "market_refresh_schedule" {
  source              = "./modules/lambda_schedule"
  name                = "${local.name_prefix}-refresh-market-snapshots"
  schedule_expression = var.market_refresh_schedule
  lambda_arn          = aws_lambda_function.market_jobs.arn
  lambda_name         = aws_lambda_function.market_jobs.function_name
  payload             = jsonencode({ job = "refresh_market_snapshots" })
}

module "score_refresh_schedule" {
  source              = "./modules/lambda_schedule"
  name                = "${local.name_prefix}-score-symbols"
  schedule_expression = var.score_refresh_schedule
  lambda_arn          = aws_lambda_function.market_jobs.arn
  lambda_name         = aws_lambda_function.market_jobs.function_name
  payload             = jsonencode({ job = "score_symbols" })
}
