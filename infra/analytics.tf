# 콜드패스(PLAN #23). 워커 로그의 쌍 줄 → Firehose → S3(Parquet) → Glue.
#
#   Lambda stdout ─ 로그 그룹 ─ 구독 필터 { $.k = "pair" }
#     ─ Firehose (GZIP 해제 · 메시지 추출 · JSON→Parquet)
#     ─ s3://thoth-pairs-<계정>/pairs/dt=YYYY-MM-DD/
#     ─ Glue thoth.pairs (파티션 투영) ─ Athena
#
# ★ **워커가 Firehose 를 부르지 않는다**(DECISIONS §97). 핫패스에 왕복 · 실패
#   처리 · IAM 이 붙고, 로컬 FastAPI 와 배포본이 다른 코드를 타게 된다. 로그 한
#   줄이면 두 경로가 같다. `usage` 계기와 같은 모양이다.
#
# ★ **Lambda 변환 함수가 없다.** Firehose 가 CloudWatch Logs 의 GZIP 을 풀고
#   메시지만 뽑는 처리기를 내장한다. 그래서 줄 자체가 JSON 이어야 한다 —
#   `worker/app/pairs.py` 가 접두사 없이 쓰는 이유다.
#
# ★ **시간당 과금이 없다.** Firehose · S3 · Glue 카탈로그 모두 쓴 만큼이다
#   (main.tf 의 원칙). 쌍 로그가 0 줄이면 0 원이다.
#
# ★ **Glue 크롤러를 두지 않는다.** 스키마는 코드가 정했고(`pairs.COLUMNS`)
#   파티션은 투영으로 잡는다. 크롤러는 실행마다 과금되고 스키마를 추측한다.
#
# ★ **이 파일은 IAM 을 만든다.** 배포 역할은 IAM 쓰기가 없으므로(oidc.tf) 첫
#   `apply` 는 CI 가 아니라 손으로 한다. 그 뒤 태그 배포는 읽기만 한다.

locals {
  pairs_bucket = "${local.name}-pairs-${data.aws_caller_identity.me.account_id}"

  # ★ **`worker/app/pairs.py` 의 COLUMNS 와 같아야 한다.** HCL 은 파이썬을 읽지
  #   못하므로 정본을 한 곳에 둘 수 없고, `test_pairs.py` 가 둘을 대조한다.
  #   순서까지 본다 — Parquet 는 이름으로 읽지만 사람은 순서로 읽는다.
  pairs_columns = [
    { name = "k", type = "string" },
    { name = "v", type = "int" },
    { name = "ts", type = "bigint" },
    { name = "h", type = "string" },
    { name = "src", type = "string" },
    { name = "raw", type = "string" },
    { name = "ko", type = "string" },
    { name = "engine", type = "string" },
    { name = "model", type = "string" },
    { name = "prompt", type = "string" },
    { name = "book", type = "string" },
    { name = "n", type = "int" },
    { name = "site", type = "string" },
    { name = "adapter", type = "string" },
    { name = "ver", type = "string" },
  ]
}

# ── 버킷 ─────────────────────────────────────────────────────────────────────
#
# ★ **`force_destroy` 를 켜지 않는다.** 여기 쌓이는 것은 다시 만들 수 없는 학습
#   데이터다. `tf.sh destroy` 는 이 버킷에서 멈추고, 그것이 의도다 — 캐시와
#   달리 지우면 재번역으로 복구되지 않는다(사이트가 그 문항을 다시 보여줄 때만).
#
# ★ **퍼블릭 차단 · SSE-S3 · 소유자 강제를 따로 적지 않는다.** 2023-04 이후 새
#   버킷의 기본값이다. 적으면 리소스가 넷 늘고 배포 역할의 읽기 권한도 는다.

resource "aws_s3_bucket" "pairs" {
  bucket = local.pairs_bucket
}

resource "aws_s3_bucket_lifecycle_configuration" "pairs" {
  bucket = aws_s3_bucket.pairs.id

  # ★ 오류 객체만 지운다. 변환에 실패한 원본이 여기 오고, 원인을 본 뒤에는
  #   쓸모가 없다. 쌍(`pairs/`)에는 만료를 걸지 않는다.
  rule {
    id     = "errors-expire"
    status = "Enabled"

    filter {
      prefix = "errors/"
    }

    expiration {
      days = var.pairs_error_retention_days
    }
  }

  rule {
    id     = "abort-multipart"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# ── 카탈로그 ─────────────────────────────────────────────────────────────────

resource "aws_glue_catalog_database" "thoth" {
  name = local.name
}

resource "aws_glue_catalog_table" "pairs" {
  name          = "pairs"
  database_name = aws_glue_catalog_database.thoth.name
  table_type    = "EXTERNAL_TABLE"

  # ★ **파티션 투영.** `MSCK REPAIR` 도 크롤러도 없이 Athena 가 `dt` 를 경로에서
  #   계산한다. 날짜 파티션을 등록하는 일을 사람이 기억하지 않아도 된다.
  parameters = {
    "classification"              = "parquet"
    "projection.enabled"          = "true"
    "projection.dt.type"          = "date"
    "projection.dt.format"        = "yyyy-MM-dd"
    "projection.dt.range"         = "2026-09-01,NOW"
    "projection.dt.interval"      = "1"
    "projection.dt.interval.unit" = "DAYS"
    "storage.location.template"   = "s3://${local.pairs_bucket}/pairs/dt=$${dt}/"
  }

  partition_keys {
    name = "dt"
    type = "string"
  }

  storage_descriptor {
    location      = "s3://${local.pairs_bucket}/pairs/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    dynamic "columns" {
      for_each = local.pairs_columns
      content {
        name = columns.value.name
        type = columns.value.type
      }
    }
  }
}

# ── Firehose ─────────────────────────────────────────────────────────────────

data "aws_iam_policy_document" "firehose_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["firehose.amazonaws.com"]
    }

    # ★ 혼동된 대리인 방지. 다른 계정의 스트림이 이 역할을 쓰지 못한다.
    condition {
      test     = "StringEquals"
      variable = "sts:ExternalId"
      values   = [data.aws_caller_identity.me.account_id]
    }
  }
}

resource "aws_iam_role" "firehose" {
  name               = "${local.name}-pairs-firehose"
  description        = "Firehose writes pairs to S3 as Parquet"
  assume_role_policy = data.aws_iam_policy_document.firehose_assume.json
}

data "aws_iam_policy_document" "firehose" {
  statement {
    sid = "Bucket"

    actions = [
      "s3:AbortMultipartUpload",
      "s3:GetBucketLocation",
      "s3:GetObject",
      "s3:ListBucket",
      "s3:ListBucketMultipartUploads",
      "s3:PutObject",
    ]

    resources = [aws_s3_bucket.pairs.arn, "${aws_s3_bucket.pairs.arn}/*"]
  }

  # ★ **변환이 스키마를 읽는다.** 이것이 빠지면 모든 레코드가 오류 버킷으로
  #   가고 스트림 자체는 정상으로 보인다. 오류 로그(아래)가 그것을 말해 준다.
  statement {
    sid     = "Schema"
    actions = ["glue:GetTable", "glue:GetTableVersion", "glue:GetTableVersions"]

    resources = [
      "arn:aws:glue:${var.region}:${data.aws_caller_identity.me.account_id}:catalog",
      "arn:aws:glue:${var.region}:${data.aws_caller_identity.me.account_id}:database/${aws_glue_catalog_database.thoth.name}",
      "arn:aws:glue:${var.region}:${data.aws_caller_identity.me.account_id}:table/${aws_glue_catalog_database.thoth.name}/${aws_glue_catalog_table.pairs.name}",
    ]
  }

  statement {
    sid       = "ErrorLog"
    actions   = ["logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.firehose.arn}:*"]
  }
}

resource "aws_iam_role_policy" "firehose" {
  name   = "${local.name}-pairs-firehose"
  role   = aws_iam_role.firehose.id
  policy = data.aws_iam_policy_document.firehose.json
}

# ★ **실패가 말하게 한다**(DECISIONS §70 · §87). 변환 실패는 스트림 상태를
#   바꾸지 않는다 — S3 `errors/` 에 조용히 쌓일 뿐이다. 이 로그가 없으면 원인을
#   객체를 열어 봐야 안다.
resource "aws_cloudwatch_log_group" "firehose" {
  name              = "/aws/kinesisfirehose/${local.name}-pairs"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_stream" "firehose" {
  name           = "DestinationDelivery"
  log_group_name = aws_cloudwatch_log_group.firehose.name
}

resource "aws_kinesis_firehose_delivery_stream" "pairs" {
  name        = "${local.name}-pairs"
  destination = "extended_s3"

  extended_s3_configuration {
    role_arn   = aws_iam_role.firehose.arn
    bucket_arn = aws_s3_bucket.pairs.arn

    prefix              = "pairs/dt=!{timestamp:yyyy-MM-dd}/"
    error_output_prefix = "errors/!{firehose:error-output-type}/dt=!{timestamp:yyyy-MM-dd}/"

    # ★ **64MB 가 Parquet 변환의 하한이다.** 이 트래픽으로는 크기에 먼저 닿지
    #   않으므로 실제로는 간격이 파일을 끊는다. 15분마다 작은 파일이 생기고,
    #   분량이 작아 Athena 스캔 비용으로는 문제가 되지 않는다.
    buffering_size     = 64
    buffering_interval = var.pairs_buffer_seconds

    # 변환이 켜지면 압축은 Parquet 가 한다(SNAPPY). 여기서 또 걸면 거절된다.
    compression_format = "UNCOMPRESSED"

    processing_configuration {
      enabled = true

      processors {
        type = "Decompression"

        parameters {
          parameter_name  = "CompressionFormat"
          parameter_value = "GZIP"
        }
      }

      # ★ 로그 그룹 · 스트림 같은 봉투를 벗기고 메시지만 남긴다. 메시지가 곧
      #   `pairs.py` 가 쓴 JSON 한 줄이다.
      processors {
        type = "CloudWatchLogProcessing"

        parameters {
          parameter_name  = "DataMessageExtraction"
          parameter_value = "true"
        }
      }
    }

    data_format_conversion_configuration {
      input_format_configuration {
        deserializer {
          open_x_json_ser_de {}
        }
      }

      output_format_configuration {
        serializer {
          parquet_ser_de {}
        }
      }

      schema_configuration {
        database_name = aws_glue_catalog_database.thoth.name
        table_name    = aws_glue_catalog_table.pairs.name
        role_arn      = aws_iam_role.firehose.arn
        region        = var.region
      }
    }

    cloudwatch_logging_options {
      enabled         = true
      log_group_name  = aws_cloudwatch_log_group.firehose.name
      log_stream_name = aws_cloudwatch_log_stream.firehose.name
    }
  }

  depends_on = [aws_iam_role_policy.firehose]
}

# ── 구독 필터 ────────────────────────────────────────────────────────────────

data "aws_iam_policy_document" "logs_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["logs.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:logs:${var.region}:${data.aws_caller_identity.me.account_id}:*"]
    }
  }
}

resource "aws_iam_role" "logs_to_firehose" {
  name               = "${local.name}-pairs-logs"
  description        = "CloudWatch Logs subscription puts pair lines to Firehose"
  assume_role_policy = data.aws_iam_policy_document.logs_assume.json
}

data "aws_iam_policy_document" "logs_to_firehose" {
  statement {
    actions   = ["firehose:PutRecord", "firehose:PutRecordBatch"]
    resources = [aws_kinesis_firehose_delivery_stream.pairs.arn]
  }
}

resource "aws_iam_role_policy" "logs_to_firehose" {
  name   = "${local.name}-pairs-logs"
  role   = aws_iam_role.logs_to_firehose.id
  policy = data.aws_iam_policy_document.logs_to_firehose.json
}

# ★ **필터가 `k` 를 본다.** `usage` · 경고 · 예외 줄은 JSON 이 아니거나 `k` 가
#   없어 걸리지 않는다. `pairs.KIND` 를 바꾸면 이 필터가 조용히 0 건이 되므로
#   `test_pairs.py` 가 이 문자열을 읽어 대조한다.
resource "aws_cloudwatch_log_subscription_filter" "pairs" {
  name            = "${local.name}-pairs"
  log_group_name  = aws_cloudwatch_log_group.worker.name
  filter_pattern  = "{ $.k = \"pair\" }"
  destination_arn = aws_kinesis_firehose_delivery_stream.pairs.arn
  role_arn        = aws_iam_role.logs_to_firehose.arn

  depends_on = [aws_iam_role_policy.logs_to_firehose]
}
