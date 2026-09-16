# ★ 기본값은 `.env.example` 과 같은 값을 쓴다. 로컬과 배포본이 다른 설정으로
#   돌면 "로컬에서는 됐는데" 가 난다.

variable "region" {
  description = "리소스를 세울 리전"
  type        = string
  default     = "ap-northeast-2"
}

variable "bedrock_region" {
  description = "Bedrock 호출 리전. 비우면 region 을 쓴다"
  type        = string
  default     = ""
}

variable "bedrock_model" {
  description = "BEDROCK_MODEL. apac.* 는 크로스리전 추론 프로파일이다"
  type        = string
  default     = "apac.amazon.nova-lite-v1:0"
}

variable "bedrock_max_tokens" {
  description = "한 응답의 토큰 상한"
  type        = number
  default     = 2048
}

variable "worker_token" {
  description = <<-EOT
    X-Thoth-Token 값. **비우면 엔드포인트를 주운 누구나 월 상한을 태운다.**
    확장에 심는 값이라 비밀은 아니지만(MASTER §12) 배포에서는 반드시 채운다.
  EOT
  type        = string
  sensitive   = true

  validation {
    # ★ 빈 값으로 배포되는 길을 막는다. doctor 가 로컬에서 같은 것을 본다.
    condition     = length(var.worker_token) >= 16
    error_message = "worker_token 은 16자 이상이어야 한다. 비우면 상한이 유일한 방어가 된다."
  }
}

variable "max_chars_per_month" {
  description = "월 누적 문자 상한. 넘으면 429 다"
  type        = number
  default     = 2000000
}

variable "max_text_len" {
  description = "한 문장의 상한. 넘으면 413 이다"
  type        = number
  default     = 5000
}

variable "reserved_concurrency" {
  description = <<-EOT
    동시 실행 상한. `-1` 이면 고정하지 않는다.

    ★ **신규 계정은 총 동시성이 10 이다**(1000 이 아니다). 5 를 예약하면 미예약분이
      최소값 10 아래로 떨어져 `InvalidParameterValueException` 이 난다. 이 계정에서
      예약은 한도를 올린 뒤에야 가능하다(DECISIONS §75).

    ★ **그래서 지금은 예약하지 않아도 폭발 반경이 좁다.** 계정 전체가 10 이므로
      이 함수가 태울 수 있는 동시 실행도 10 이 천장이다. 한도를 올리는 순간
      그 천장이 사라지므로, 그때 이 값을 함께 올린다.
  EOT
  type        = number
  default     = -1
}

variable "log_retention_days" {
  description = "CloudWatch 로그 보관 기간. 무한 보관은 조용히 쌓인다"
  type        = number
  default     = 14
}

variable "pairs_buffer_seconds" {
  description = <<-EOT
    Firehose 가 파일을 끊는 간격(초). 60~900.

    ★ **짧게 잡으면 확인이 빨라지고 파일이 잘아진다.** Parquet 변환은 크기 하한이
      64MB 라 이 트래픽에서는 언제나 간격이 끊는다. 배포 직후 도는지 볼 때만
      낮추고 되돌린다.
  EOT
  type        = number
  default     = 900

  validation {
    condition     = var.pairs_buffer_seconds >= 60 && var.pairs_buffer_seconds <= 900
    error_message = "pairs_buffer_seconds 는 60~900 이다. Firehose 가 그 밖을 거절한다."
  }
}

variable "pairs_error_retention_days" {
  description = "변환 실패 객체(errors/) 보관 기간. 쌍 자체에는 만료가 없다"
  type        = number
  default     = 30
}
