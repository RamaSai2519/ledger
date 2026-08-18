resource "aws_lambda_function" "api" {
  function_name    = "ledger-api"
  role             = aws_iam_role.api_lambda.arn
  filename         = var.lambda_zip_path
  source_code_hash = filebase64sha256(var.lambda_zip_path)
  handler          = "index.handler"
  runtime          = "python3.13"

  # Just under API Gateway's 30s integration timeout.
  timeout     = 29
  memory_size = 256

  environment {
    variables = {
      ENV                       = var.env
      MONGO_URI                 = var.mongo_uri
      MONGO_DB_NAME             = var.mongo_db_name
      JWT_SECRET_KEY            = var.jwt_secret_key
      ACCESS_TOKEN_MINUTES      = tostring(var.access_token_minutes)
      REFRESH_TOKEN_DAYS        = tostring(var.refresh_token_days)
      FIREBASE_CREDENTIALS_JSON = var.firebase_credentials_json
      BILL_DUE_REMINDER_DAYS    = tostring(var.bill_due_reminder_days)
    }
  }

  depends_on = [aws_iam_role_policy_attachment.api_lambda_basic_execution]
}
