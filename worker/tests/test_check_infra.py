"""인프라 선언 겹침 — `tools/check_infra.py`.

★ **무는 것과 안 무는 것을 둘 다 잰다.** 겹침 검사는 쉽게 모든 것에 운다 — 한 역할에
  붙는 인라인 정책 여럿, 부모가 없는 윗자리 자원들. **울기만 하는 규칙은 아무 말도
  안 하는 규칙과 같다**(DECISIONS §134).
"""
import importlib.util
import pathlib

_spec = importlib.util.spec_from_file_location(
    "check_infra", pathlib.Path(__file__).resolve().parents[2] / "tools/check_infra.py")
ci = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ci)


def test_같은_부모에_같은_종류가_둘이면_문다():
    글 = '''
resource "aws_s3_bucket_lifecycle_configuration" "a" {
  bucket = aws_s3_bucket.pairs.id
}

resource "aws_s3_bucket_lifecycle_configuration" "b" {
  bucket = aws_s3_bucket.pairs.id
}
'''
    fails = ci.duplicate_parents({"x.tf": 글})
    assert len(fails) == 1
    assert "aws_s3_bucket_lifecycle_configuration" in fails[0]
    assert "x.tf:a" in fails[0] and "x.tf:b" in fails[0]


def test_부모가_다르면_안_문다():
    # ★ 음성 대조. 버킷이 둘이면 설정도 둘인 것이 맞다.
    글 = '''
resource "aws_s3_bucket_lifecycle_configuration" "a" {
  bucket = aws_s3_bucket.pairs.id
}

resource "aws_s3_bucket_lifecycle_configuration" "b" {
  bucket = aws_s3_bucket.logs.id
}
'''
    assert ci.duplicate_parents({"x.tf": 글}) == []


def test_겹쳐도_되는_자리는_선언으로_연다():
    # ★ 한 역할에 인라인 정책 여럿은 AWS 가 허락한다 — 이름이 다르면 따로 산다.
    글 = '''
resource "aws_iam_role_policy" "a" {
  # 겹침 허용 : 인라인 정책은 이름마다 따로 산다
  role = aws_iam_role.worker.id
}

resource "aws_iam_role_policy" "b" {
  # 겹침 허용 : 인라인 정책은 이름마다 따로 산다
  role = aws_iam_role.worker.id
}
'''
    assert ci.duplicate_parents({"x.tf": 글}) == []


def test_한쪽만_선언하면_여전히_문다():
    # ★ **선언은 짝 전체에 걸려야 한다.** 하나만 적고 넘어가면 그것이 빠져나가는 문이다.
    글 = '''
resource "aws_iam_role_policy" "a" {
  # 겹침 허용 : 까닭
  role = aws_iam_role.worker.id
}

resource "aws_iam_role_policy" "b" {
  role = aws_iam_role.worker.id
}
'''
    assert len(ci.duplicate_parents({"x.tf": 글})) == 1


def test_사이에_낀_data_블록이_몸에_섞이지_않는다():
    # ★ **처음 판이 여기서 틀렸다.** 몸을 「다음 `resource` 까지」 로 잘랐더니 사이의
    #   `data` 블록이 앞 자원의 몸이 되어, 부모 없는 역할들이 전부 「다른 자원을
    #   가리킨다」 로 읽혔다. **답은 맞았는데 몸이 틀렸다**(DECISIONS §134).
    글 = '''
resource "aws_iam_role" "worker" {
  name = "thoth-worker"
}

data "aws_iam_policy_document" "worker" {
  statement {
    resources = [aws_dynamodb_table.translations.arn]
  }
}

resource "aws_iam_role" "ci" {
  name = "thoth-ci"
}
'''
    # 둘 다 부모가 없고 **가리키는 자원도 없다** — 윗자리 자원이므로 조용해야 한다.
    assert ci.duplicate_parents({"x.tf": 글}) == []


def test_꼬리_주석이_부모를_갈라놓지_않는다():
    # ★ **처음 시험은 줄머리 주석(`  # bucket = ...`)으로 썼는데 그것은 정규식이
    #   이미 안 읽는다** — 주석을 안 지우게 망가뜨려도 통과했다. 진짜 위험한 꼴은
    #   **꼬리 주석**이다. 값에 주석이 딸려 들어가면 같은 부모가 **다른 부모로 갈려**
    #   겹침이 조용히 빠져나간다. 음성이 아니라 **거짓 음성**을 재는 자리다(§134).
    글 = '''
resource "aws_s3_bucket_lifecycle_configuration" "a" {
  bucket = aws_s3_bucket.pairs.id  # 옛 판 만료
}

resource "aws_s3_bucket_lifecycle_configuration" "b" {
  bucket = aws_s3_bucket.pairs.id
}
'''
    fails = ci.duplicate_parents({"x.tf": 글})
    assert len(fails) == 1, "꼬리 주석이 같은 부모를 둘로 갈랐다"


def test_가리키는데_부모_이름을_모르면_말한다():
    # ★ 안 보이는 것을 통과로 세지 않는다(§59). 「조용하다」 와 「못 봤다」 는 다르다.
    글 = '''
resource "aws_zzz_attachment" "a" {
  엉뚱한이름 = aws_s3_bucket.pairs.id
}

resource "aws_zzz_attachment" "b" {
  엉뚱한이름 = aws_s3_bucket.pairs.id
}
'''
    fails = ci.duplicate_parents({"x.tf": 글})
    assert len(fails) == 1
    assert "부모 인자를 못 찾았다" in fails[0]


def test_부모도_참조도_없는_윗자리_자원은_조용하다():
    # ★ 음성 대조. `aws_iam_role` 다섯이 우는 검사는 아무도 안 읽는다.
    글 = '''
resource "aws_iam_role" "a" {
  name = "a"
}

resource "aws_iam_role" "b" {
  name = "b"
}

resource "aws_cloudwatch_log_group" "c" {
  name = "/aws/lambda/x"
}

resource "aws_cloudwatch_log_group" "d" {
  name = "/aws/lambda/y"
}
'''
    assert ci.duplicate_parents({"x.tf": 글}) == []


def test_지금_저장소가_조용하다():
    # ★ 합성 글만 재면 **진짜 선언이 어긋나도 초록**이다. 실물을 함께 본다.
    assert ci.duplicate_parents(ci.읽기()) == []
