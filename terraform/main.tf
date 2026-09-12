terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

variable "project_id" {
  description = "Your GCP project ID (find it in the GCP Console dashboard)"
  type        = string
}

variable "region" {
  description = "Must be a GCP Always Free eligible region for e2-micro"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  type    = string
  default = "us-central1-a"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_compute_instance" "bot_vm" {
  name         = "game-price-bot"
  machine_type = "e2-micro"  # Always Free eligible in us-west1/us-central1/us-east1
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
      size  = 30  # GB — within the Always Free 30GB standard persistent disk limit
      type  = "pd-standard"  # must be standard (not SSD) to stay in the free tier
    }
  }

  network_interface {
    network = "default"
    access_config {}  # ephemeral external IP — needed for outbound internet access
  }

  # Installs Docker on first boot so the VM is ready for the container
  # the moment it comes up, without a manual SSH step.
  metadata_startup_script = <<-EOF
    #!/bin/bash
    apt-get update
    apt-get install -y docker.io
    systemctl enable docker
    systemctl start docker
  EOF

  tags = ["game-price-bot"]
}

output "vm_external_ip" {
  value = google_compute_instance.bot_vm.network_interface[0].access_config[0].nat_ip
}