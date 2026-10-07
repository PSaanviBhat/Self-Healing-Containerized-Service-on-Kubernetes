variable "target_platform" {
  type        = string
  default     = "local"
  description = "Target provisioning platform: 'local' (Kind/Docker) or 'aws' (Production EKS)"
  validation {
    condition     = contains(["local", "aws"], var.target_platform)
    error_message = "target_platform must be either 'local' or 'aws'."
  }
}

variable "cluster_name" {
  type        = string
  default     = "self-healing-cluster"
  description = "Name of the Kubernetes cluster"
}

variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS Region for cloud deployment"
}

variable "aws_node_count" {
  type        = number
  default     = 2
  description = "Desired number of worker nodes for AWS EKS"
}
