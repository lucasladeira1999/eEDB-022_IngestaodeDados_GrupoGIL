#!/usr/bin/env bash
# Empacota as duas Lambdas em build/*.zip. Rode antes do terraform apply
# (e de novo sempre que mexer em src/, pra mudança subir no próximo apply).
set -euo pipefail

cd "$(dirname "$0")"

BUILD=build
rm -rf "$BUILD"
mkdir -p "$BUILD/produtor" "$BUILD/consumidor"

# produtor: só usa boto3, que já vem no runtime da Lambda
cp -r src/produtor "$BUILD/produtor/"
cp src/utils.py "$BUILD/produtor/"

# consumidor: leva as camadas trusted e delivery, o de-para de siglas e o driver
# do Postgres (o acronyms.yaml precisa ficar ao lado do utils.py, que o resolve)
cp -r src/consumidor src/to_trusted src/to_delivery "$BUILD/consumidor/"
cp src/utils.py src/sql_schema.py src/acronyms.yaml "$BUILD/consumidor/"
pip install --quiet --target "$BUILD/consumidor" -r requirements-lambda.txt

(cd "$BUILD/produtor" && zip -qr ../produtor.zip . -x '*__pycache__*')
(cd "$BUILD/consumidor" && zip -qr ../consumidor.zip . -x '*__pycache__*')

echo "ok:"
ls -lh "$BUILD"/*.zip
