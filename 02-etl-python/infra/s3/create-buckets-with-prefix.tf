resource "aws_s3_bucket" "my_bucket" {
  bucket = "eedb-022-2026-grupo03-${var.bucket_name}"
  force_destroy = true
}

# Block Public Access (Security Best Practice)
resource "aws_s3_bucket_public_access_block" "public_block" {
  bucket = aws_s3_bucket.my_bucket.id

  block_public_acls = true
  block_public_policy = true
  ignore_public_acls = true
  restrict_public_buckets = true
}