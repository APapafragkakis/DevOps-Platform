output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "eks_cluster_name" {
  description = "EKS cluster name — use with: aws eks update-kubeconfig --name <value>"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "EKS API server endpoint"
  value       = module.eks.cluster_endpoint
}

output "rds_endpoint" {
  description = "RDS connection endpoint (host:port)"
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}

output "rds_database_url" {
  description = "Full DATABASE_URL — store this in K8s secret or AWS Secrets Manager"
  value       = "postgresql://devops:${var.db_password}@${aws_db_instance.main.endpoint}/devopsdb"
  sensitive   = true
}

