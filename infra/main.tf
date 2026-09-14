# thoth 배포. Lambda · Function URL · DynamoDB · IAM 넷뿐이다.
#
# ★ **시간당 과금 리소스를 두지 않는다.** ALB · NAT Gateway · ECS · Fargate ·
#   GPU 인스턴스는 범위 밖이다(PLAN §4). 요청이 간헐적이라 상시 기동 고정비가
#   맞지 않고, 유휴에도 나가는 돈은 크레딧을 태운다.
#
# ★ **VPC 에 넣지 않는다.** Bedrock 과 DynamoDB 는 퍼블릭 엔드포인트로 닿는다.
#   VPC 에 넣는 순간 아웃바운드를 위해 NAT 가 필요해지고, 그것이 이 저장소가
#   피하기로 한 바로 그 고정비다.
#
# ★ **상태를 로컬에 둔다.** S3 백엔드가 정석이나 부트스트랩 버킷이 또 필요하다.
#   리소스가 넷이고 전부 재생성 가능하며 유휴 비용이 0 이라, 상태를 잃어도
#   고아 리소스가 돈을 태우지 않는다. `.gitignore` 가 `*.tfstate` 를 막는다.

terraform {
  required_version = "~> 1.16"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = "thoth"
      ManagedBy = "terraform"
    }
  }
}

data "aws_caller_identity" "me" {}

locals {
  name = "thoth"

  # ★ **Bedrock 리전을 따로 둔다.** 모델마다 제공 리전이 다르고, 모델 하나
  #   때문에 캐시 · 카운터까지 옮기지 않는다(MASTER §7).
  bedrock_region = var.bedrock_region != "" ? var.bedrock_region : var.region
}
