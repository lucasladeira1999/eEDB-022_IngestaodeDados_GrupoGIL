variable "namespace_name" {
  type        = string
  description = "name of the Redshift Serverless namespace"
}

variable "workgroup_name" {
  type        = string
  description = "name of the Redshift Serverless workgroup"
}

variable "database_name" {
  type        = string
  description = "name of the initial database"
  default     = "dev"
}

variable "admin_username" {
  type        = string
  description = "admin username for the namespace"
  default     = "admin"
}

variable "admin_password" {
  type        = string
  description = "admin password for the namespace"
  sensitive   = true
}

variable "base_capacity" {
  type        = number
  description = "base RPU capacity for the workgroup"
  default     = 8
}
