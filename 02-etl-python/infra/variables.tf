variable "buckets_to_create" {
  type = list(string)
  description = "name of buckets to create"
}

variable "redshift_namespace_name" {
  type        = string
  description = "name of the Redshift Serverless namespace"
}

variable "redshift_workgroup_name" {
  type        = string
  description = "name of the Redshift Serverless workgroup"
}

variable "redshift_database_name" {
  type        = string
  description = "name of the initial Redshift database"
}

variable "redshift_admin_username" {
  type        = string
  description = "admin username for the Redshift namespace"
}

variable "redshift_admin_password" {
  type        = string
  description = "admin password for the Redshift namespace"
  sensitive   = true
}

variable "redshift_base_capacity" {
  type        = number
  description = "base RPU capacity for the Redshift workgroup"
}
