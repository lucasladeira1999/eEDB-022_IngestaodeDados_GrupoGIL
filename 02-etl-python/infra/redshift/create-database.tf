resource "aws_redshift_cluster" "this" {
  cluster_identifier  = var.cluster_identifier
  database_name       = var.database_name
  master_username     = var.admin_username
  master_password     = var.admin_password
  node_type           = "ra3.large"
  cluster_type        = "single-node"
  publicly_accessible = true
  skip_final_snapshot = true
}
