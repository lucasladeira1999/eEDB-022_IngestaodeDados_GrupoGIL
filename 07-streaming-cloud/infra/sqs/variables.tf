variable "queue_name" {
  type        = string
  description = "name of the SQS queue"
}

variable "visibility_timeout_seconds" {
  type        = number
  description = "visibility timeout, must be >= the consumer Lambda timeout"
  default     = 180
}
