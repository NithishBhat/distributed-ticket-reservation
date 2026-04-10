variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "db_username" {
  type    = string
  default = "postgres"
}

variable "ticket_service_count" {
  type    = number
  default = 2
}

variable "order_service_count" {
  type    = number
  default = 2
}

variable "lock_strategy" {
  type    = string
  default = "pessimistic"
}

variable "enable_cache" {
  type    = bool
  default = false
}

variable "cache_ttl_seconds" {
  type    = number
  default = 10
}
