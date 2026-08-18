# EventBridge Scheduler wiring for LED-5's background jobs (budget threshold
# checks, daily digest, bill-due reminders) — see
# docs/decisions/0005-eventbridge-scheduler-for-jobs.md for why this
# replaces plan.md's literal "APScheduler" wording: the backend is a
# zip-deployed Lambda behind API Gateway with no persistent process for an
# in-process scheduler to run in, so a managed scheduler invokes the
# existing `ledger-api` Lambda directly instead.

data "aws_iam_policy_document" "scheduler_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ledger_scheduler" {
  name               = "ledger-scheduler"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume_role.json
}

data "aws_iam_policy_document" "scheduler_invoke_lambda" {
  statement {
    effect    = "Allow"
    actions   = ["lambda:InvokeFunction"]
    resources = [aws_lambda_function.api.arn]
  }
}

resource "aws_iam_role_policy" "ledger_scheduler_invoke_lambda" {
  name   = "ledger-scheduler-invoke-lambda"
  role   = aws_iam_role.ledger_scheduler.id
  policy = data.aws_iam_policy_document.scheduler_invoke_lambda.json
}

resource "aws_lambda_permission" "scheduler_invoke" {
  statement_id  = "AllowEventBridgeSchedulerInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "scheduler.amazonaws.com"
  source_arn    = "arn:aws:scheduler:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:schedule/default/ledger-*"
}

data "aws_caller_identity" "current" {}

# Threshold crossing needs to be checked frequently enough that a household
# gets notified soon after crossing 80%/100%, without checking so often it's
# wasteful — hourly is the MVP cadence (plan.md doesn't specify one).
resource "aws_scheduler_schedule" "budget_threshold_check" {
  name                = "ledger-budget-threshold-check"
  schedule_expression = "rate(1 hour)"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.api.arn
    role_arn = aws_iam_role.ledger_scheduler.arn
    input    = jsonencode({ job = "budget_threshold_check" })
  }
}

# Daily digest — once a day, mid-morning IST.
resource "aws_scheduler_schedule" "digest_notifications" {
  name                         = "ledger-digest-notifications"
  schedule_expression          = "cron(30 3 * * ? *)" # 03:30 UTC = 09:00 IST
  schedule_expression_timezone = "UTC"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.api.arn
    role_arn = aws_iam_role.ledger_scheduler.arn
    input    = jsonencode({ job = "digest_notifications" })
  }
}

# Bill-due reminders — once a day is sufficient since the job's own window
# (BILL_DUE_REMINDER_DAYS) and re-notify guard tolerate a daily cadence.
resource "aws_scheduler_schedule" "bill_due_reminders" {
  name                         = "ledger-bill-due-reminders"
  schedule_expression          = "cron(0 3 * * ? *)" # 03:00 UTC = 08:30 IST
  schedule_expression_timezone = "UTC"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.api.arn
    role_arn = aws_iam_role.ledger_scheduler.arn
    input    = jsonencode({ job = "bill_due_reminders" })
  }
}
