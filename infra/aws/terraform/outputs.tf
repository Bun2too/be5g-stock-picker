output "symbols_table_name" {
  value = aws_dynamodb_table.symbols.name
}

output "market_snapshots_table_name" {
  value = aws_dynamodb_table.market_snapshots.name
}

output "ranked_picks_table_name" {
  value = aws_dynamodb_table.ranked_picks.name
}

output "portfolios_table_name" {
  value = aws_dynamodb_table.portfolios.name
}

output "market_jobs_lambda_name" {
  value = aws_lambda_function.market_jobs.function_name
}

output "alpaca_secret_arn" {
  value = aws_secretsmanager_secret.alpaca.arn
}

output "github_actions_role_arn" {
  value       = try(aws_iam_role.github_actions[0].arn, null)
  description = "Set this as GitHub secret AWS_ROLE_TO_ASSUME when github_owner/github_repo are configured."
}

output "railway_api_iam_user_name" {
  value       = try(aws_iam_user.railway_api[0].name, null)
  description = "Create an access key for this user and store it in Railway as AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY."
}
