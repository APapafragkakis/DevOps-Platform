terraform {
  required_version = ">= 1.8"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.50"
    }
  }

  # Remote state — keep this in S3 so the team shares state
  backend "s3" {
    bucket         = "devops-platform-tfstate"
    key            = "prod/terraform.tfstate"
    region         = "eu-west-1"
    encrypt        = true
    dynamodb_table = "devops-platform-tfstate-lock"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "devops-platform"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# -------------------------------------------------------
# VPC
# -------------------------------------------------------
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.8"

  name = "${var.project_name}-vpc"
  cidr = var.vpc_cidr

  azs             = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
  private_subnets = var.private_subnet_cidrs
  public_subnets  = var.public_subnet_cidrs

  enable_nat_gateway   = true
  single_nat_gateway   = var.environment != "production" # save cost in staging
  enable_dns_hostnames = true
  enable_dns_support   = true

  # Required tags for EKS to discover subnets
  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
  }
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
  }
}

# -------------------------------------------------------
# EKS Cluster
# -------------------------------------------------------
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.14"

  cluster_name    = "${var.project_name}-${var.environment}"
  cluster_version = "1.30"

  vpc_id                         = module.vpc.vpc_id
  subnet_ids                     = module.vpc.private_subnets
  cluster_endpoint_public_access = true

  # Managed node group
  eks_managed_node_groups = {
    main = {
      instance_types = [var.node_instance_type]
      min_size       = 2
      max_size       = 4
      desired_size   = 2

      labels = {
        role = "worker"
      }
    }
  }
}

# -------------------------------------------------------
# RDS PostgreSQL
# -------------------------------------------------------
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = module.vpc.private_subnets
}

resource "aws_security_group" "rds" {
  name        = "${var.project_name}-rds-sg"
  description = "Allow Postgres access from EKS nodes only"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "main" {
  identifier        = "${var.project_name}-${var.environment}"
  engine            = "postgres"
  engine_version    = "16.3"
  instance_class    = var.db_instance_class
  allocated_storage = 20
  storage_encrypted = true

  db_name  = "devopsdb"
  username = "devops"
  password = var.db_password # set via TF_VAR_db_password env var

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  backup_retention_period = 7
  deletion_protection     = var.environment == "production"
  skip_final_snapshot     = var.environment != "production"

  multi_az = var.environment == "production" # HA only in prod
}

