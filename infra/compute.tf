# ★ **zip 은 `tools/package_lambda.sh` 가 만든다.** terraform 이 만들지 않는
#   이유는 그 스크립트가 "의존성 없이 도는가" 를 함께 확인하기 때문이다 —
#   만드는 것과 확인하는 것이 갈리면 확인 없이 배포하는 길이 생긴다.
#
# ★ **zip 이 결정적이다.** 타임스탬프를 고정해 두었으므로 내용이 같으면
#   `source_code_hash` 도 같다. 고친 것이 없으면 `plan` 이 비어 있고, 그래서
#   진짜 변경을 가릴 수 있다(DECISIONS §72).

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/aws/lambda/${local.name}-worker"
  retention_in_days = var.log_retention_days
}

resource "aws_lambda_function" "worker" {
  function_name = "${local.name}-worker"
  role          = aws_iam_role.worker.arn
  handler       = "app.lambda_handler.handler"
  runtime       = "python3.13"

  filename         = "${path.module}/../dist/worker.zip"
  source_code_hash = filebase64sha256("${path.module}/../dist/worker.zip")

  # ★ 한 요청에 최대 50문장이 오고 배치로 한 번에 나간다. Bedrock 왕복이 길어질
  #   수 있으므로 넉넉히 둔다 — 타임아웃이 결과가 되면 사용자는 이유를 모른다.
  timeout     = 60
  memory_size = 512

  # ★ **동시 실행을 고정한다**(PLAN §2-3 #19). 월 문자 상한이 비용을 막지만
  #   그 사이의 동시 호출은 Bedrock 쓰로틀을 부른다.
  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    # ★ **`AWS_REGION` 을 넣지 않는다.** Lambda 예약 키라 설정하면 배포가
    #   거부된다. 런타임이 채워 주고 `engine.py` 가 그것을 읽는다.
    variables = {
      ENGINE              = "bedrock"
      CACHE               = "ddb"
      CACHE_TABLE         = aws_dynamodb_table.translations.name
      WORKER_TOKEN        = var.worker_token
      MAX_CHARS_PER_MONTH = tostring(var.max_chars_per_month)
      MAX_TEXT_LEN        = tostring(var.max_text_len)
      BEDROCK_REGION      = local.bedrock_region
      BEDROCK_MODEL       = var.bedrock_model
      BEDROCK_MAX_TOKENS  = tostring(var.bedrock_max_tokens)
    }
  }

  depends_on = [aws_cloudwatch_log_group.worker]
}

# ★ **인증은 `NONE` 뿐이다.** `AWS_IAM` 은 확장이 SigV4 서명을 못 한다. 방어는
#   `WORKER_TOKEN` 이고, 그것이 비밀이 아니라 '엔드포인트를 주운 사람' 을 거르는
#   장치라는 것은 MASTER §12 에 적혀 있다.
#
# ★ **CORS 를 코드가 아니라 여기서 정한다.** 프리플라이트(OPTIONS)까지 Function
#   URL 이 답하므로 핸들러가 볼 일이 없다(DECISIONS §68).
resource "aws_lambda_function_url" "worker" {
  function_name      = aws_lambda_function.worker.function_name
  authorization_type = "NONE"

  cors {
    allow_origins = ["*"]
    allow_methods = ["POST", "GET"]
    allow_headers = ["content-type", "x-thoth-token"]
    max_age       = 86400
  }
}
