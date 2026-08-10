variable "cluster_identifier" {
  type        = string
  description = "identifier of the Redshift cluster"
}

variable "database_name" {
  type        = string
  description = "name of the initial database"
  default     = "dev"
}

variable "admin_username" {
  type        = string
  description = "admin username for the cluster"
  default     = "admin"
}

variable "admin_password" {
  type        = string
  description = "admin password for the cluster"
  sensitive   = true
}
