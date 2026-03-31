terraform {
  required_version = ">= 1.5"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 5.0" }
  }
  # Uncomment to use remote state:
  # backend "gcs" {
  #   bucket = "your-tfstate-bucket"
  #   prefix = "ecommerce/dev"
  # }
}

module "gke_cluster" {
  source       = "../../modules/gke-cluster"
  project_id   = var.project_id
  region       = var.region
  zone         = var.zone
  cluster_name = "ecommerce"
  env          = "dev"
}
