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
  description = "path to the producer deployment package (built by build.sh)"
}

variable "consumidor_zip" {
  type        = string
  description = "path to the consumer deployment package (built by build.sh)"
}

variable "runtime" {
  type        = string
  description = "Lambda Python runtime"
  default     = "python3.12"
}

variable "consumidor_timeout" {
  type        = number
  description = "timeout of the consumer Lambda, must be <= the queue visibility timeout"
  default     = 60
}

variable "raw_bucket" {
  type        = string
  description = "bucket with the original reclamacoes files"
}

variable "raw_prefix" {
  type        = string
  description = "prefix scanned by the producer inside the raw bucket"
}

variable "trusted_bucket" {
  type        = string
  description = "bucket where the treated messages are written"
}

variable "delivery_bucket" {
  type        = string
  description = "bucket where the enriched messages are written"
}

variable "queue_url" {
  type        = string
  description = "URL of the SQS queue the producer writes to"
}

variable "queue_arn" {
  type        = string
  description = "ARN of the SQS queue the consumer is subscribed to"
}

variable "db_host" {
  type        = string
  description = "RDS endpoint used for the enrichment lookup"
}

variable "db_port" {
  type        = string
  description = "RDS port"
  default     = "5432"
}

variable "db_name" {
  type        = string
  description = "database holding the bancos table"
}

variable "db_user" {
  type        = string
  description = "database user"
}

variable "db_password" {
  type        = string
  description = "database password"
  sensitive   = true
}
