# GitHub Actions 가 AWS 에 키 없이 인증한다.
#
# ★ **장기 액세스 키를 시크릿에 넣지 않는다.** 저장소가 공개이고 시크릿은
#   워크플로 수정 한 번으로 찍어 볼 수 있다. OIDC 는 실행마다 짧은 토큰을
#   받으므로 저장소에 남는 비밀이 0 이다.
#
# ★ **읽기 역할만 세운다.** 배포 역할은 `terraform apply` 에 필요한 권한이
#   IAM 쓰기까지 닿고, 그것은 자기 역할을 고칠 수 있다는 뜻이다. 실제 `apply`
#   로그에서 필요한 액션을 뽑아 좁힌 뒤 #21 에서 세운다.
#
# ★ **지문을 손으로 적지 않는다.** `tls_certificate` 가 현재 인증서에서 읽는다.
#   적어 두면 갱신되는 날 늙고, 그때 실패는 "인증이 안 된다" 로만 보인다(§62).

variable "github_repo" {
  description = "OIDC 를 허용할 저장소. owner/repo"
  type        = string
  default     = "CleverAIFox/thoth"
}

variable "github_repo_sub" {
  description = <<-EOT
    OIDC 토큰의 `sub` 가 주장하는 저장소 식별자. `owner@<id>/repo@<id>` 다.

    ★ **`owner/repo` 가 아니다.** GitHub 이 이름 변경으로 정책이 뚫리는 것을
      막으려고 불변 숫자 ID 를 박아 보낸다. 옛 형식으로 쓴 문서가 많아 그대로
      따르면 `Not authorized to perform sts:AssumeRoleWithWebIdentity` 가 나고,
      **그 문구는 조건 불일치와 지문 오류를 구별해 주지 않는다.**

    ★ **이 값은 실측이다**(2026-09-15). 워크플로에서 토큰을 받아 클레임을 찍어
      읽었다. 다시 재는 법은 DECISIONS §87 에 있다.
  EOT
  type        = string
  default     = "CleverAIFox@314908905/thoth@1366448765"
}

variable "github_oidc_provider_arn" {
  description = <<-EOT
    이미 있는 GitHub OIDC 프로바이더의 ARN. 비우면 새로 만든다.

    ★ **계정에 하나만 존재할 수 있다.** 이웃 저장소가 이미 만들어 뒀다면
      `apply` 가 EntityAlreadyExists 로 멈춘다. 그때 그 ARN 을 여기 넣는다.
  EOT
  type        = string
  default     = ""
}

locals {
  create_oidc = var.github_oidc_provider_arn == ""
  oidc_arn    = local.create_oidc ? aws_iam_openid_connect_provider.github[0].arn : var.github_oidc_provider_arn
  github_host = "token.actions.githubusercontent.com"
}

data "tls_certificate" "github" {
  count = local.create_oidc ? 1 : 0
  url   = "https://${local.github_host}"
}

resource "aws_iam_openid_connect_provider" "github" {
  count           = local.create_oidc ? 1 : 0
  url             = "https://${local.github_host}"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.github[0].certificates[length(data.tls_certificate.github[0].certificates) - 1].sha1_fingerprint]
}

data "aws_iam_policy_document" "ci_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [local.oidc_arn]
    }

    # ★ **`aud` 를 반드시 건다.** 빼면 다른 곳에서 발급된 토큰도 받는다.
    condition {
      test     = "StringEquals"
      variable = "${local.github_host}:aud"
      values   = ["sts.amazonaws.com"]
    }

    # ★ **저장소를 못 박는다.** `repo:*` 로 두면 GitHub 의 아무 저장소나
    #   이 역할을 가져간다. 브랜치까지 좁히지 않는 것은 이 역할이 읽기
    #   전용이고 PR 에서도 돌아야 하기 때문이다.
    condition {
      test     = "StringLike"
      variable = "${local.github_host}:sub"
      values   = ["repo:${var.github_repo_sub}:*"]
    }
  }
}

resource "aws_iam_role" "ci" {
  name               = "${local.name}-ci"
  description        = "GitHub Actions read-only. deploy drift check"
  assume_role_policy = data.aws_iam_policy_document.ci_assume.json
}

# ★ 코드가 실제로 부르는 것만 적는다. `deploy_drift.py` 는 `get-function` 하나다.
data "aws_iam_policy_document" "ci" {
  statement {
    sid       = "ReadFunction"
    actions   = ["lambda:GetFunction"]
    resources = [aws_lambda_function.worker.arn]
  }
}

resource "aws_iam_role_policy" "ci" {
  name   = "${local.name}-ci"
  role   = aws_iam_role.ci.id
  policy = data.aws_iam_policy_document.ci.json
}

output "ci_role_arn" {
  description = "워크플로의 role-to-assume 에 넣는 값"
  value       = aws_iam_role.ci.arn
}

# ── 배포 역할 ───────────────────────────────────────────────────────────────
#
# ★ **IAM 쓰기를 주지 않는다.** `terraform apply` 전체를 CI 에 주면 그 역할이
#   자기 신뢰 정책을 고칠 수 있다. 읽기만 준다 — refresh 에 필요한 것은 읽기다.
#   IAM 을 바꾸는 변경은 CI 에서 `AccessDenied` 로 멈추고 손으로 `apply` 한다.
#   **그것이 결함이 아니라 경계다.**
#
# ★ **`production` Environment 로 좁힌다.** `sub` 가
#   `...:environment:production` 일 때만 받는다. 읽기 역할(`:*`)보다 좁고,
#   승인 없이는 그 `sub` 가 발급되지 않는다.
#
# ★ **상태 버킷을 여기 적지 않는다.** 이름이 저장소에 없기 때문이다
#   (MASTER §11-16). 변수로 받는다.

variable "state_bucket" {
  description = "terraform 상태 버킷. bootstrap_backend.sh 가 만든 이름"
  type        = string
  default     = ""
}

locals {
  state_bucket = var.state_bucket != "" ? var.state_bucket : "thoth-tfstate-${data.aws_caller_identity.me.account_id}"
}

data "aws_iam_policy_document" "deploy_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [local.oidc_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.github_host}:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.github_host}:sub"
      values   = ["repo:${var.github_repo_sub}:environment:production"]
    }
  }
}

resource "aws_iam_role" "deploy" {
  name               = "${local.name}-deploy"
  description        = "GitHub Actions deploy. terraform apply without IAM writes"
  assume_role_policy = data.aws_iam_policy_document.deploy_assume.json
}

data "aws_iam_policy_document" "deploy" {
  # 상태. 잠금 파일도 같은 접두사 아래 있다.
  statement {
    sid       = "StateObjects"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["arn:aws:s3:::${local.state_bucket}/thoth/*"]
  }

  statement {
    sid       = "StateBucket"
    actions   = ["s3:ListBucket"]
    resources = ["arn:aws:s3:::${local.state_bucket}"]
  }

  statement {
    sid = "Function"

    actions = [
      "lambda:GetFunction",
      "lambda:GetFunctionConfiguration",
      "lambda:GetFunctionCodeSigningConfig",
      "lambda:GetFunctionUrlConfig",
      "lambda:GetPolicy",
      "lambda:ListVersionsByFunction",
      "lambda:UpdateFunctionCode",
      "lambda:UpdateFunctionConfiguration",
      "lambda:UpdateFunctionUrlConfig",
      "lambda:TagResource",
      "lambda:UntagResource",
      "lambda:ListTags",
    ]

    resources = [aws_lambda_function.worker.arn]
  }

  statement {
    sid = "Table"

    actions = [
      "dynamodb:DescribeTable",
      "dynamodb:DescribeTimeToLive",
      "dynamodb:DescribeContinuousBackups",
      "dynamodb:ListTagsOfResource",
      "dynamodb:UpdateTable",
      "dynamodb:UpdateTimeToLive",
      "dynamodb:TagResource",
      "dynamodb:UntagResource",
    ]

    resources = [aws_dynamodb_table.translations.arn]
  }

  statement {
    sid = "LogGroup"

    actions = [
      "logs:ListTagsForResource",
      "logs:PutRetentionPolicy",
      "logs:TagResource",
      "logs:UntagResource",
    ]

    resources = ["${aws_cloudwatch_log_group.worker.arn}:*", aws_cloudwatch_log_group.worker.arn]
  }

  # ★ **읽기만이다.** refresh 가 역할과 정책을 읽어야 계획이 선다. 쓰기는
  #   주지 않으므로 IAM 변경은 CI 에서 멈춘다.
  statement {
    sid = "IamRead"

    actions = [
      "iam:GetRole",
      "iam:GetRolePolicy",
      "iam:ListRolePolicies",
      "iam:ListAttachedRolePolicies",
      "iam:ListInstanceProfilesForRole",
      "iam:GetOpenIDConnectProvider",
    ]

    resources = [
      "arn:aws:iam::${data.aws_caller_identity.me.account_id}:role/${local.name}-*",
      local.oidc_arn,
    ]
  }

  # 목록 API 는 리소스 수준 권한을 받지 않는다. 특정 그룹에 걸면
  # "log-group::log-stream:" 으로 평가돼 거절된다.
  statement {
    sid       = "LogGroupList"
    actions   = ["logs:DescribeLogGroups"]
    resources = ["*"]
  }

  statement {
    sid       = "Whoami"
    actions   = ["sts:GetCallerIdentity"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "deploy" {
  name   = "${local.name}-deploy"
  role   = aws_iam_role.deploy.id
  policy = data.aws_iam_policy_document.deploy.json
}

output "deploy_role_arn" {
  description = "deploy 워크플로의 role-to-assume 에 넣는 값"
  value       = aws_iam_role.deploy.arn
}
