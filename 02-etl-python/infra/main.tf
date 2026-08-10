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

  cluster_identifier = var.redshift_cluster_identifier
  database_name      = var.redshift_database_name
  admin_username     = var.redshift_admin_username
  admin_password     = var.redshift_admin_password
}

output "redshift_iam_role_arn" {
  value = module.redshift.redshift_iam_role_arn
}
