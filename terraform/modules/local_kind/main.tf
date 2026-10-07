variable "cluster_name" {
  type        = string
  description = "Name of the local Kind cluster"
}

resource "local_file" "kind_config" {
  content = <<-EOT
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: ${var.cluster_name}
nodes:
- role: control-plane
  extraPortMappings:
  - containerPort: 30080
    hostPort: 8000
    protocol: TCP
- role: worker
EOT
  filename = "${path.module}/kind-cluster-config.yaml"
}

resource "null_resource" "kind_cluster" {
  depends_on = [local_file.kind_config]

  provisioner "local-exec" {
    command = "kind create cluster --config ${local_file.kind_config.filename} --name ${var.cluster_name} || true"
  }

  provisioner "local-exec" {
    when    = destroy
    command = "kind delete cluster --name self-healing-cluster || true"
  }
}

output "endpoint" {
  value = "https://127.0.0.1:6443"
}
