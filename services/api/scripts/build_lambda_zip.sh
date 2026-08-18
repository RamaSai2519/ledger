#!/usr/bin/env bash
# Builds infra/terraform's Lambda deployment zip for services/api.
# Installs only Pipfile's [packages] (not [dev-packages] — pytest/mongomock
# are test-only) and pins to manylinux2014_x86_64 wheels so the package
# matches Lambda's python3.13 x86_64 runtime regardless of what OS/arch this
# is built on. boto3/botocore are deliberately excluded — the Lambda managed
# python3.13 runtime already bundles them.
#
# firebase-admin (LED-5, FCM push) pulls in google-api-core/google-auth/
# grpcio/protobuf transitively, which noticeably grows package size — if the
# zip ever approaches Lambda's 250MB unzipped limit, moving firebase-admin
# to a Lambda layer is the first thing to try before splitting the function.
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src_dir="${root_dir}/src"
build_dir="${root_dir}/build"
package_dir="${build_dir}/package"
zip_path="${build_dir}/ledger-api.zip"

rm -rf "${build_dir}"
mkdir -p "${package_dir}"

# Kept in sync by hand with Pipfile's [packages].
pip install \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.13 \
  --only-binary=:all: \
  --target "${package_dir}" \
  flask==3.0.3 flask-restful==0.3.10 flask-cors==4.0.1 flask-jwt-extended==4.6.0 \
  aws-wsgi==0.2.7 pymongo==4.9.2 bcrypt==4.2.0 python-dotenv==1.0.1 firebase-admin==6.5.0

find "${package_dir}" -maxdepth 1 -name "*.dist-info" -exec rm -rf {} +
find "${package_dir}" -name "__pycache__" -exec rm -rf {} +

cp "${src_dir}/index.py" "${package_dir}/"
cp -r "${src_dir}/shared" "${src_dir}/services" "${src_dir}/models" "${src_dir}/jobs" "${package_dir}/"

cd "${package_dir}"
zip -r -q "${zip_path}" .

echo "Built ${zip_path}"
