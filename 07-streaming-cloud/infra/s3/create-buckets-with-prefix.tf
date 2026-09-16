# A service control policy do AWS Academy nega s3:GetBucketObjectLockConfiguration,
# e o provider faz essa chamada toda vez que lê um bucket - tanto depois de criar
# quanto em cada refresh. O bucket sobe, mas o apply quebra em seguida com
# AccessDenied, e o mesmo erro volta em todo plan/apply/destroy posterior.
#
# A criação fica então no AWS CLI, com a mesma interface de módulo (entra
# bucket_name, sai bucket_name) para o resto do Terraform não precisar saber disso.

locals {
  bucket = "eedb-022-2026-grupo03-${var.bucket_name}"
}

resource "terraform_data" "bucket" {
  triggers_replace = local.bucket

  # head-bucket antes de criar: idempotente, não falha se o bucket já existir
  provisioner "local-exec" {
    command = "aws s3api head-bucket --bucket ${local.bucket} 2>/dev/null || aws s3api create-bucket --bucket ${local.bucket}"
  }

  # equivalente ao force_destroy: esvazia e remove no terraform destroy
  provisioner "local-exec" {
    when       = destroy
    command    = "aws s3 rb s3://${self.triggers_replace} --force"
    on_failure = continue
  }
}

output "bucket_name" {
  value      = local.bucket
  depends_on = [terraform_data.bucket]
}
