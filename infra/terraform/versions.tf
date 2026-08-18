terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    # bucket / region / dynamodb_table supplied via -backend-config
    # (backend.hcl locally, GitHub Actions repo secrets in CI)
    key = "ledger/terraform.tfstate"
  }
}
