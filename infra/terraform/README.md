# infra/terraform

Terraform module for `services/api`'s AWS infrastructure: a zip-deployed
Lambda running the Flask app, and an HTTP API Gateway routing
`ANY /{proxy+}` to it. Pattern mirrors `journeymen`'s
`infra/terraform/` (see that repo for the fuller rationale) but every
resource here is named `ledger-*` and lives in its **own** Terraform state,
isolated from journeymen's — both projects happen to deploy into the same
AWS account (`135808951082`, `ap-south-1`) under the same IAM user, so
name/state isolation is what keeps them from colliding.

Deployed by `.github/workflows/deploy-api.yml` on every push to `master` that
touches `services/api/**` or `infra/terraform/**`. Nothing here should be
`terraform apply`'d by hand for routine deploys — only for the one-time
bootstrap below, or local debugging.

## Resources

| File | What it defines |
|---|---|
| `versions.tf` | Terraform/provider version pins, S3 backend block (key `ledger/terraform.tfstate`) |
| `providers.tf` | AWS provider, region `ap-south-1` |
| `variables.tf` | Inputs — `lambda_zip_path`, Mongo/JWT config |
| `iam.tf` | Lambda execution role `ledger-api-lambda` (CloudWatch Logs only) |
| `lambda.tf` | The zip-deployed Lambda `ledger-api`, built by `services/api/scripts/build_lambda_zip.sh` |
| `api_gateway.tf` | HTTP API, `payload_format_version = "1.0"` integration (**do not change** — `aws-wsgi` requires the v1.0 event shape), route, stage, invoke permission |
| `outputs.tf` | `api_url`, `region` |

## One-time bootstrap (run once, locally — not in CI)

### 1. Terraform state backend (S3 + DynamoDB lock table)

```sh
aws s3api create-bucket \
  --bucket ledger-terraform-state-135808951082 \
  --region ap-south-1 \
  --create-bucket-configuration LocationConstraint=ap-south-1

aws s3api put-bucket-versioning \
  --bucket ledger-terraform-state-135808951082 \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
  --bucket ledger-terraform-state-135808951082 \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

aws s3api put-public-access-block \
  --bucket ledger-terraform-state-135808951082 \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

aws dynamodb create-table \
  --table-name ledger-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region ap-south-1
```

Then create `infra/terraform/backend.hcl` (gitignored) locally:

```hcl
bucket         = "ledger-terraform-state-135808951082"
region         = "ap-south-1"
dynamodb_table = "ledger-terraform-locks"
```

### 2. GitHub Actions OIDC provider + deploy role

Reuses the account's existing GitHub OIDC provider (already created for
journeymen — only one is needed per account). Creates a **separate** deploy
role scoped only to `ledger-*` resources:

```sh
cat > /tmp/ledger-trust-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Federated": "arn:aws:iam::135808951082:oidc-provider/token.actions.githubusercontent.com" },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
        "token.actions.githubusercontent.com:repository": "RamaSai2519/ledger"
      },
      "StringLike": { "token.actions.githubusercontent.com:sub": "repo:RamaSai2519*/ledger*:ref:refs/heads/master" }
    }
  }]
}
EOF

aws iam create-role \
  --role-name ledger-api-deploy \
  --assume-role-policy-document file:///tmp/ledger-trust-policy.json
```

**Gotcha hit live (2026-08-18):** GitHub's actual OIDC `sub` claim is
`repo:<owner>@<owner-id>/<repo>@<repo-id>:ref:refs/heads/<branch>` — it
includes numeric owner/repo IDs the exact-match `repo:owner/repo:ref:...`
pattern from AWS's own docs doesn't account for. Confirmed via CloudTrail
(`aws cloudtrail lookup-events --lookup-attributes
AttributeKey=EventName,AttributeValue=AssumeRoleWithWebIdentity`) after the
first deploy failed with `Not authorized to perform
sts:AssumeRoleWithWebIdentity` despite an apparently-correct trust policy —
the `StringLike` pattern above with wildcards after the owner/repo names,
plus a `StringEquals` on the `repository` claim for tighter scoping, is
what actually works.

```sh

cat > /tmp/ledger-deploy-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Lambda",
      "Effect": "Allow",
      "Action": [
        "lambda:CreateFunction", "lambda:GetFunction", "lambda:GetFunctionConfiguration",
        "lambda:GetFunctionCodeSigningConfig", "lambda:UpdateFunctionCode",
        "lambda:UpdateFunctionConfiguration", "lambda:DeleteFunction",
        "lambda:AddPermission", "lambda:RemovePermission", "lambda:GetPolicy",
        "lambda:TagResource", "lambda:UntagResource", "lambda:ListTags",
        "lambda:ListVersionsByFunction"
      ],
      "Resource": "arn:aws:lambda:ap-south-1:135808951082:function:ledger-api"
    },
    {
      "Sid": "ApiGatewayV2",
      "Effect": "Allow",
      "Action": ["apigateway:GET", "apigateway:POST", "apigateway:PUT", "apigateway:PATCH", "apigateway:DELETE"],
      "Resource": ["arn:aws:apigateway:ap-south-1::/apis*"]
    },
    {
      "Sid": "LambdaExecutionRole",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole", "iam:GetRole", "iam:DeleteRole",
        "iam:AttachRolePolicy", "iam:DetachRolePolicy",
        "iam:ListAttachedRolePolicies", "iam:ListRolePolicies",
        "iam:TagRole", "iam:PassRole"
      ],
      "Resource": "arn:aws:iam::135808951082:role/ledger-api-lambda"
    },
    {
      "Sid": "TerraformState",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::ledger-terraform-state-135808951082",
        "arn:aws:s3:::ledger-terraform-state-135808951082/*"
      ]
    },
    {
      "Sid": "TerraformLock",
      "Effect": "Allow",
      "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem"],
      "Resource": "arn:aws:dynamodb:ap-south-1:135808951082:table/ledger-terraform-locks"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name ledger-api-deploy \
  --policy-name ledger-api-deploy-policy \
  --policy-document file:///tmp/ledger-deploy-policy.json
```

Put the resulting role ARN in the GitHub Actions repo secret
`AWS_DEPLOY_ROLE_ARN` (see workflow).

**Extended (2026-08-18, LED-5):** `scheduler.tf` introduced a new resource
type (EventBridge Scheduler + its own execution role `ledger-scheduler`),
so the deploy role's policy was extended incrementally, per this doc's own
rule, rather than widened — a second inline policy,
`ledger-api-deploy-scheduler-policy`, scoped to `iam:*Role*`/`PassRole` on
`arn:aws:iam::135808951082:role/ledger-scheduler` and
`scheduler:*Schedule*` on `arn:aws:scheduler:ap-south-1:135808951082:schedule/default/ledger-*`
only. The existing `Lambda` statement already covered `AddPermission`/
`GetPolicy` for the new `aws_lambda_permission` resource, so it needed no
change.

**Gotcha hit live (2026-08-18):** the first `ledger-api-deploy-scheduler-policy`
version omitted `iam:ListAttachedRolePolicies` on the `ledger-scheduler`
role — the AWS provider reads that during `terraform plan` for any IAM role
resource (to detect drift from attached managed policies), not just at
create time, so the plan step itself failed with `AccessDenied` even though
nothing tried to attach a managed policy. Added it alongside the inline-policy
actions already in that statement.

### 3. GitHub Actions repository secrets

| Secret | Notes |
|---|---|
| `AWS_DEPLOY_ROLE_ARN` | From step 2 |
| `TF_STATE_BUCKET` | `ledger-terraform-state-135808951082` |
| `TF_STATE_LOCK_TABLE` | `ledger-terraform-locks` |
| `MONGO_URI` | MongoDB Atlas connection string — until this is set, the Lambda deploys with an empty value; `/actions/health` still comes up live but Mongo-touching routes fail |
| `JWT_SECRET_KEY` | Generate a real random value, e.g. `openssl rand -hex 32` |

## Local usage

```sh
cd infra/terraform
terraform init -backend-config=backend.hcl
terraform plan   # review before apply, always
terraform apply
```

## Status

**Deployed and live (2026-08-18).** Bootstrap (state bucket, lock table,
OIDC deploy role) done, all four secrets set, `.github/workflows/deploy-api.yml`
has applied cleanly on push and via manual dispatch. `terraform output
api_url` → `https://w7ychchtd1.execute-api.ap-south-1.amazonaws.com/` —
curl-verified live, including a full signup → login → household create →
join → invite-code flow against a real MongoDB Atlas cluster, not just
`/actions/health`.
