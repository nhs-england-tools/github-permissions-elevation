terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source = "hashicorp/archive"
    }
    null = {
      source = "hashicorp/null"
    }
  }

  required_version = ">= 1.3.7"
}

provider "aws" {
  region = "eu-west-2"

  default_tags {
    tags = {
      project             = "github_permission_manager"
      TagVersion          = "1.0"
      Programme           = "Engineering Technical Authority"
      Product             = "GitHub Permission Manager"
      Owner               = "Chris Walters"
      CostCentre          = "101375"
      data_classification = "1"
      DataType            = "UserAccount"
      Environment         = terraform.workspace
      ProjectType         = "PoC"
      PublicFacing        = "Y"
    }
  }
}
