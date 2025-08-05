terraform {
    required_providers {
        aws = {
            source = "hashicorp/aws"
            version = "6.4.0"
        }
    }
}

provider "aws" {
    region = "us-east-1"
}

resource "aws_instance" "tf-ec2" {
    ami = ""
    instance_type = "t2.micro"
    tags = {
        "Name" = "created-by-tf"
    }
}