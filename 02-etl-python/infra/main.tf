provider "aws" {
  region = "us-east-1"
}

module "create-s3-bucket-with-prefix" {
  source = "./s3"
  for_each = toset(var.buckets_to_create)
  bucket_name = each.value
}

module "redshift" {
  source = "./redshift"

  namespace_name = var.redshift_namespace_name
  workgroup_name = var.redshift_workgroup_name
  database_name  = var.redshift_database_name
  admin_username = var.redshift_admin_username
  admin_password = var.redshift_admin_password
  base_capacity  = var.redshift_base_capacity
}

