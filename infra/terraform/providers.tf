provider "aws" {
  region = "ap-south-1"
}

data "aws_region" "current" {}
