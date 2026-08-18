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

variable "firebase_credentials_json" {
  description = <<-EOT
    Firebase Admin SDK service-account JSON (FCM push). Empty until the user
    completes the one-time Firebase console project setup (LED-5) — the FCM
    send path (shared/fcm.py) logs a warning and no-ops when this is unset,
    so the rest of the notification pipeline (in-app `notifications` writes)
    still works standalone.
  EOT
  type        = string
  sensitive   = true
  default     = ""
}

variable "bill_due_reminder_days" {
  description = "How many days ahead of a wallet's due_day the bill_due_reminders job fires a reminder."
  type        = number
  default     = 3
}
