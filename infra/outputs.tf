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
