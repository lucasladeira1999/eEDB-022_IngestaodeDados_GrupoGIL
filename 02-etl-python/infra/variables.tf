variable "buckets_to_create" {
  type = list(string)
  description = "name of buckets to create"
}

variable "redshift_cluster_identifier" {
  type        = string
  description = "identifier of the Redshift cluster"
}

variable "redshift_database_name" {
  type        = string
  description = "name of the initial Redshift database"
}

variable "redshift_admin_username" {
  type        = string
  description = "admin username for the Redshift cluster"
}

variable "redshift_admin_password" {
  type        = string
  description = "admin password for the Redshift cluster"
  sensitive   = true
}
