terraform {
  required_version = ">= 1.5.0"
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "api_replicas" {
  type    = number
  default = 1
}

provider "docker" {}

resource "docker_network" "smartbancs" {
  name = "smartbancs-${var.environment}"
}

resource "docker_image" "redis" {
  name         = "redis:7-alpine"
  keep_locally = true
}

resource "docker_container" "redis" {
  name  = "smartbancs-redis-${var.environment}"
  image = docker_image.redis.image_id
  networks_advanced {
    name = docker_network.smartbancs.name
  }
  ports {
    internal = 6379
    external = 6379
  }
}

output "network" {
  value = docker_network.smartbancs.name
}

output "api_replicas" {
  value = var.api_replicas
}
