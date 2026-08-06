resource "aws_redshiftserverless_namespace" "this" {
  namespace_name      = var.namespace_name
  db_name             = var.database_name
  admin_username      = var.admin_username
  admin_user_password = var.admin_password
}

resource "aws_redshiftserverless_workgroup" "this" {
  namespace_name       = aws_redshiftserverless_namespace.this.namespace_name
  workgroup_name       = var.workgroup_name
  base_capacity        = var.base_capacity
  publicly_accessible  = false
}
