provider "aws" {
  region = "us-east-1"
}

module "create-s3-bucket-with-prefix" {
  source = "./s3"
  for_each = toset(var.buckets_to_create)
  bucket_name = each.value
}

