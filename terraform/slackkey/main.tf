terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.16"
    }
  }

  backend "local" {
    path = "terraform.tfstate"
  }
  
  required_version = ">= 1.5.0"
}

provider "aws" {
  region  = "us-east-1"
}
