output "deployment_platform" {
  value       = var.target_platform
  description = "Active provisioning platform"
}

output "cluster_name" {
  value       = var.cluster_name
  description = "Target Kubernetes cluster identifier"
}

output "cluster_endpoint" {
  value       = var.target_platform == "local" ? (length(module.local_cluster) > 0 ? module.local_cluster[0].endpoint : "n/a") : (length(module.aws_eks) > 0 ? module.aws_eks[0].cluster_endpoint : "n/a")
  description = "Kubernetes control plane API endpoint"
}

output "kubeconfig_command" {
  value       = var.target_platform == "local" ? "kind export kubeconfig --name ${var.cluster_name}" : "aws eks update-kubeconfig --region ${var.aws_region} --name ${var.cluster_name}"
  description = "Command to configure kubectl credentials"
}
