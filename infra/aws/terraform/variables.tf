variable "aws_region" {
  description = "AWS region for the market data persistence stack."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Prefix used for AWS resource names."
  type        = string
  default     = "be5g-stock-picker"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "prod"
}

variable "max_symbols_per_refresh" {
  description = "Maximum active symbols processed by each market refresh Lambda run."
  type        = number
  default     = 300
}

variable "max_symbols_catalog" {
  description = "Maximum symbols kept in the DynamoDB symbol catalog."
  type        = number
  default     = 6000
}

variable "symbol_refresh_schedule" {
  description = "EventBridge schedule for symbol catalog refresh."
  type        = string
  default     = "cron(0 8 * * ? *)"
}

variable "market_refresh_schedule" {
  description = "EventBridge schedule for latest market metrics refresh."
  type        = string
  default     = "rate(15 minutes)"
}

variable "score_refresh_schedule" {
  description = "EventBridge schedule for ranked-pick scoring."
  type        = string
  default     = "rate(15 minutes)"
}

variable "alpaca_data_feed" {
  description = "Alpaca market data feed used by scheduled jobs."
  type        = string
  default     = "iex"
}

variable "github_owner" {
  description = "GitHub org/user that owns the repository. Leave empty to skip OIDC role creation."
  type        = string
  default     = ""
}

variable "github_repo" {
  description = "GitHub repository name. Leave empty to skip OIDC role creation."
  type        = string
  default     = ""
}

variable "github_branch" {
  description = "GitHub branch allowed to apply Terraform."
  type        = string
  default     = "main"
}

variable "create_railway_api_user" {
  description = "Create a least-privilege IAM user for the Railway API to access DynamoDB."
  type        = bool
  default     = true
}
