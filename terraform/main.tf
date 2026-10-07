terraform {
  required_version = ">= 1.5.0"
  required_providers {
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region                      = var.aws_region
  skip_credentials_validation = var.target_platform == "local" ? true : false
  skip_requesting_account_id  = var.target_platform == "local" ? true : false
}

module "local_cluster" {
  count        = var.target_platform == "local" ? 1 : 0
  source       = "./modules/local_kind"
  cluster_name = var.cluster_name
}

module "aws_eks" {
  count        = var.target_platform == "aws" ? 1 : 0
  source       = "./modules/aws_eks"
  cluster_name = var.cluster_name
  aws_region   = var.aws_region
  node_count   = var.aws_node_count
}
