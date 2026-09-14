# ★ **크로스리전 추론 프로파일은 두 자리를 허용해야 한다.** `apac.amazon.nova-
#   lite-v1:0` 은 모델 ID 가 아니라 프로파일이고, 호출은 프로파일을 거쳐 각
#   리전의 기반 모델로 간다. 프로파일만 허용하면 `AccessDeniedException` 이
#   나는데 **로컬에서는 되던 것이 Lambda 에서만 안 되므로** 원인을 찾기 어렵다.
#
# ★ 기반 모델 ARN 의 리전을 `*` 로 둔다. 프로파일이 어느 리전으로 보낼지는
#   AWS 가 정하고, 그 목록은 시간이 지나면 바뀐다.

locals {
  # apac.amazon.nova-lite-v1:0 → amazon.nova-lite-v1:0
  foundation_model = replace(var.bedrock_model, "/^(apac|us|eu|global)\\./", "")
}

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "worker" {
  name               = "${local.name}-worker"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

data "aws_iam_policy_document" "worker" {
  # ★ 로그 그룹은 terraform 이 만든다. `CreateLogGroup` 을 주지 않는 이유는,
  #   주면 런타임이 보관 기간 없는 그룹을 스스로 만들 수 있기 때문이다.
  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.worker.arn}:*"]
  }

  # ★ 코드가 실제로 부르는 것만 적는다. `cache.py` 가 batch_get_item 과
  #   batch_writer(=BatchWriteItem), `guard.py` 가 update_item 과 get_item 이다.
  #   `DescribeTable` 은 부르지 않으므로 주지 않는다.
  statement {
    sid = "Table"

    actions = [
      "dynamodb:BatchGetItem",
      "dynamodb:BatchWriteItem",
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
    ]

    resources = [aws_dynamodb_table.translations.arn]
  }

  statement {
    sid     = "Bedrock"
    actions = ["bedrock:InvokeModel"]

    resources = [
      "arn:aws:bedrock:${local.bedrock_region}:${data.aws_caller_identity.me.account_id}:inference-profile/${var.bedrock_model}",
      "arn:aws:bedrock:*::foundation-model/${local.foundation_model}",
    ]
  }
}

resource "aws_iam_role_policy" "worker" {
  name   = "${local.name}-worker"
  role   = aws_iam_role.worker.id
  policy = data.aws_iam_policy_document.worker.json
}
