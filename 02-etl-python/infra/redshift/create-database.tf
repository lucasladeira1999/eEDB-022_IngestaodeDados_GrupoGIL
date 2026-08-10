data "aws_vpc" "default" {
  default = true
}

resource "aws_security_group" "redshift" {
  name        = "${var.cluster_identifier}-redshift"
  description = "Allow inbound Redshift access from trusted IPs"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "Redshift access"
    from_port   = 5439
    to_port     = 5439
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_redshift_cluster" "this" {
  cluster_identifier     = var.cluster_identifier
  database_name          = var.database_name
  master_username        = var.admin_username
  master_password        = var.admin_password
  node_type              = "ra3.large"
  cluster_type           = "single-node"
  publicly_accessible    = true
  skip_final_snapshot    = true
  vpc_security_group_ids = [aws_security_group.redshift.id]
}
