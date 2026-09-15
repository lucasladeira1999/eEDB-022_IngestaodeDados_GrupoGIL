variable "identifier" {
  type        = string
  description = "identifier of the RDS instance"
}

variable "database_name" {
  type        = string
  description = "name of the initial database"
}

variable "admin_username" {
  type        = string
  description = "admin username for the RDS instance"
}

variable "admin_password" {
  type        = string
  description = "admin password for the RDS instance"
  sensitive   = true
}

variable "instance_class" {
  type        = string
  description = "instance class of the RDS instance"
  default     = "db.t3.micro"
}

variable "engine_version" {
  type        = string
  description = "major version of Postgres"
  default     = "16"
}
