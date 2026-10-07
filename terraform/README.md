# Infrastructure as Code (Terraform) Documentation

This directory provides dual-path provisioning:

1. **Local Path (Default / Free)**:
   - Provisions a local Kubernetes cluster using `Kind` (Kubernetes in Docker).
   - Cost: **$0.00**.
   - Configures a multi-node topology (1 control-plane, 1 worker node) and binds nodePort `30080` to localhost port `8000`.

2. **AWS Production Path (Modular)**:
   - Provisions a production VPC, dual-AZ public subnets, IAM Cluster & Node roles, EKS control plane (v1.30), and an EKS Managed Node Group (`t3.medium`).
   - Configured cleanly inside `modules/aws_eks`.

## Usage Instructions

### 1. Local Provisioning (Default)
```bash
cd terraform
terraform init
terraform plan -var="target_platform=local"
terraform apply -var="target_platform=local" -auto-approve
```

### 2. AWS Production Provisioning
```bash
cd terraform
terraform init
terraform plan -var="target_platform=aws" -var="aws_region=us-east-1"
terraform apply -var="target_platform=aws" -auto-approve
```

### 3. Cleanup
```bash
terraform destroy
```
