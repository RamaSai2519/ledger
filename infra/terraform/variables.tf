variable "env" {
  type    = string
  default = "prod"
}

variable "lambda_zip_path" {
  type        = string
  description = "Path to the built ledger-api.zip (services/api/scripts/build_lambda_zip.sh)"
}

variable "mongo_uri" {
  type      = string
  sensitive = true
  default   = ""
}

variable "mongo_db_name" {
  type    = string
  default = "ledger"
}

variable "jwt_secret_key" {
  type      = string
  sensitive = true
}

variable "access_token_minutes" {
  type    = number
  default = 15
}

variable "refresh_token_days" {
  type    = number
  default = 30
}
