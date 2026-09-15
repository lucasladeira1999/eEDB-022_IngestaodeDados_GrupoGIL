variable "raw_bucket_suffix" {
  type        = string
  description = "suffix of the raw bucket (the module prepends the group prefix)"
}

variable "trusted_bucket_suffix" {
  type        = string
  description = "suffix of the trusted bucket"
}

variable "delivery_bucket_suffix" {
  type        = string
  description = "suffix of the delivery bucket"
}

variable "raw_prefix" {
  type        = string
  description = "prefix scanned by the producer inside the raw bucket"
  default     = "Reclamacoes/"
}

variable "queue_name" {
  type        = string
  description = "name of the SQS queue"
}

variable "queue_visibility_timeout_seconds" {
  type        = number
  description = "queue visibility timeout, must be >= the consumer Lambda timeout"
  default     = 180
}

variable "rds_identifier" {
  type        = string
  description = "identifier of the RDS instance"
}

variable "rds_database_name" {
  type        = string
  description = "name of the initial database"
}

variable "rds_admin_username" {
  type        = string
  description = "admin username for the RDS instance"
}

variable "rds_admin_password" {
  type        = string
  description = "admin password for the RDS instance"
  sensitive   = true
}

variable "produtor_function_name" {
  type        = string
  description = "name of the producer Lambda"
}

variable "consumidor_function_name" {
  type        = string
  description = "name of the consumer Lambda"
}

variable "produtor_zip" {
  type        = string
  description = "path to the producer deployment package"
  default     = "../build/produtor.zip"
}

variable "consumidor_zip" {
  type        = string
  description = "path to the consumer deployment package"
  default     = "../build/consumidor.zip"
}

variable "consumidor_timeout" {
  type        = number
  description = "timeout of the consumer Lambda"
  default     = 60
}
