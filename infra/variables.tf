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
    동시 실행 상한(PLAN §2-3 #19). **고정하지 않으면 폭주가 상한까지 간다** —
    월 문자 상한이 비용을 막지만 그 사이 동시 호출이 Bedrock 쓰로틀을 부른다.
  EOT
  type        = number
  default     = 5
}

variable "log_retention_days" {
  description = "CloudWatch 로그 보관 기간. 무한 보관은 조용히 쌓인다"
  type        = number
  default     = 14
}
