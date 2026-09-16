output "worker_url" {
  description = "확장의 stEndpoint 에 넣는 값"
  value       = aws_lambda_function_url.worker.function_url
}

output "table_name" {
  value = aws_dynamodb_table.translations.name
}

# ★ 배포 직후 확인 절차를 출력에 적는다. 기억에 맡기면 안 한다.
output "verify" {
  description = "배포본을 실제로 때려 본다"
  value       = <<-EOT
    WORKER_URL=${trimsuffix(aws_lambda_function_url.worker.function_url, "/")} \
    WORKER_TOKEN=<토큰> bash tools/smoke.sh
  EOT
}

output "pairs_bucket" {
  description = "쌍이 쌓이는 버킷. pairs/dt=YYYY-MM-DD/ 아래 Parquet"
  value       = aws_s3_bucket.pairs.bucket
}

# ★ **쌓였는지는 로그가 아니라 버킷과 테이블을 본다**(DECISIONS §96). 명령을
#   여기에 적지 않는다 — 전에 적었던 `aws s3 ls` 는 프로파일 없이 돌아 `.env` 를
#   읽지 않은 셸에서 죽었다(DECISIONS §98). 도구가 `.env` 를 읽는다.
output "verify_pairs" {
  description = "쌍이 실제로 쌓였는지. 새 문장을 번역하고 pairs_buffer_seconds 가 지난 뒤"
  value       = "bash tools/pairs_check.sh"
}
