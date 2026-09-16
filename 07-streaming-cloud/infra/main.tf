# versão fixada para todo mundo do grupo aplicar com o mesmo provider - sem isso
# cada um pega a mais recente do dia e diferenças de comportamento viram caça ao
# fantasma (6.58.0 é a que a atividade 02 usou)
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.58.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

locals {
  buckets_to_create = [
    var.raw_bucket_suffix,
    var.trusted_bucket_suffix,
    var.delivery_bucket_suffix,
  ]
}

module "create-s3-bucket-with-prefix" {
  source      = "./s3"
  for_each    = toset(local.buckets_to_create)
  bucket_name = each.value
}

module "sqs" {
  source = "./sqs"

  queue_name                 = var.queue_name
  visibility_timeout_seconds = var.queue_visibility_timeout_seconds
}

module "rds" {
  source = "./rds"

  identifier     = var.rds_identifier
  database_name  = var.rds_database_name
  admin_username = var.rds_admin_username
  admin_password = var.rds_admin_password
}

module "lambda" {
  source = "./lambda"

  produtor_function_name   = var.produtor_function_name
  consumidor_function_name = var.consumidor_function_name
  produtor_zip             = var.produtor_zip
  consumidor_zip           = var.consumidor_zip
  consumidor_timeout       = var.consumidor_timeout

  raw_bucket      = module.create-s3-bucket-with-prefix[var.raw_bucket_suffix].bucket_name
  raw_prefix      = var.raw_prefix
  trusted_bucket  = module.create-s3-bucket-with-prefix[var.trusted_bucket_suffix].bucket_name
  delivery_bucket = module.create-s3-bucket-with-prefix[var.delivery_bucket_suffix].bucket_name

  queue_url = module.sqs.queue_url
  queue_arn = module.sqs.queue_arn

  db_host     = module.rds.host
  db_name     = var.rds_database_name
  db_user     = var.rds_admin_username
  db_password = var.rds_admin_password
}

# tudo que precisa ser colado no src/config.yaml depois do apply
output "raw_bucket" {
  value = module.create-s3-bucket-with-prefix[var.raw_bucket_suffix].bucket_name
}

output "trusted_bucket" {
  value = module.create-s3-bucket-with-prefix[var.trusted_bucket_suffix].bucket_name
}

output "delivery_bucket" {
  value = module.create-s3-bucket-with-prefix[var.delivery_bucket_suffix].bucket_name
}

output "rds_host" {
  value = module.rds.host
}

output "queue_url" {
  value = module.sqs.queue_url
}

output "dlq_url" {
  value = module.sqs.dlq_url
}

output "produtor_function_name" {
  value = module.lambda.produtor_function_name
}

output "consumidor_function_name" {
  value = module.lambda.consumidor_function_name
}
