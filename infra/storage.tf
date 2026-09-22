# ★ **스키마는 코드가 정했다.** `cache.py` 와 `guard.py` 를 읽으면 나온다.
#
#   캐시   {h: sha256(원문), ko: 번역}
#   카운터 {h: "quota#2026-09", chars: N, expires_at: N}
#
#   정렬 키가 없고 파티션 키 `h` 하나다. 두 종류가 한 테이블에 사는 이유는
#   테이블이 둘이면 IAM 도 둘, 백업 판단도 둘이 되기 때문이다.

resource "aws_dynamodb_table" "translations" {
  name         = "${local.name}-translations"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "h"

  attribute {
    name = "h"
    type = "S"
  }

  # ★ **TTL 속성이 `expires_at` 이고 캐시 항목에는 그것이 없다**.
  #   그래서 카운터만 다음 달 + 7일에 사라지고 번역은 영구히 남는다. 캐시를
  #   지우면 재번역이고 과금 엔진에서는 재과금이다(DECISIONS §5).
  #
  # ★ 이것을 빠뜨리면 지난 달 문자 카운터가 영원히 남는다.
  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  # ★ **PITR 을 켜지 않는다.** 캐시는 다시 만들 수 있고 카운터는 한 달짜리다.
  #   복구할 값이 없는 곳에 저장 비용을 얹지 않는다.
  point_in_time_recovery {
    enabled = false
  }
}
