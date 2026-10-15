"""**배포는 태그에서만 도는데, 태그가 뒤처졌는지는 아무도 안 봤다**(DECISIONS §193).

★ **재니 3주였다.** 2026-10-14 기준 마지막 태그 `v0.1.8` 은 9월 22일 것이고 그 뒤로
  66 커밋이 쌓였다. 그 안에 `worker/app` 이 **+428 줄** — `particle.py`(신규 203줄) ·
  `glossary.py`(신규 110줄) · `cache.py` · `engine.py`. **올라가 있는 람다는 3주 전 코드**인데
  `doctor` 는 내내 초록이었다. 「가진 것과 도는 것은 다르다」(§186)의 배포판이다.

★ **AWS 를 안 부른다.** 람다에서 코드 해시를 읽으려면 `lambda:GetFunction` 이 들고 그 응답에
  `WORKER_TOKEN` 이 **평문으로** 들어 있다 — §186 이 CI 에 그 권한을 안 준 바로 그 까닭이다.
  그래서 묻는 말을 바꿨다 : 「올라간 것이 무엇인가」 → **「마지막 태그가 지금 배포 대상을
  담고 있나」**. 답이 `git` 안에 전부 있다.

★ **배포 대상의 정본은 꾸러미다**(`tools/lib/pkg.py`). 람다에 담기는 것은 `worker/app` 이고
  같은 워크플로가 `terraform apply` 로 `infra` 도 민다. **`extension` 은 태그가 안 싣는다** —
  사람이 크롬에 얹으므로 이 눈이 볼 자리가 아니다.
"""
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOCTOR = (ROOT / "tools/doctor.sh").read_text(encoding="utf-8")


def 배포절() -> str:
    """`doctor.sh` 의 `== 배포 ==` 토막 — **주석을 걷어낸 코드만.**

    ★ **글을 코드로 읽는 검사는 글부터 지운다.** 이 저장소에서 **열세 번째** 겪는 족속이다.
      이 절의 머리말은 `lambda` · `terraform` · `extension` 을 **설명으로** 든다 — 안 걷으면
      「AWS 를 안 부른다」 가 제 주석을 읽고 빨개진다. 실제로 첫 판이 그렇게 틀렸다.
    """
    i = DOCTOR.index('echo "== 배포 =="')
    j = DOCTOR.index('echo "== ', i + 10)
    return "\n".join(x for x in DOCTOR[i:j].splitlines() if not x.lstrip().startswith("#"))


def test_배포_절이_있다():
    assert 'echo "== 배포 =="' in DOCTOR


def test_태그로만_배포한다는_것이_실물과_맞는다():
    # ★ **이 검사의 전제가 참인지부터 본다**(§133). 배포가 `main` 푸시로도 돈다면
    #   「태그가 뒤처졌다」 는 말이 아무 뜻도 없다.
    글 = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")
    assert 'tags: ["v*"]' in 글, "배포 방아쇠가 태그가 아니다 — 이 검사의 전제가 깨졌다"
    assert re.search(r"^on:\s*$", 글, re.M)
    머리 = 글[글.index("\non:"):글.index("\npermissions:")]
    assert "branches:" not in 머리, f"가지로도 배포한다 : {머리}"


def test_배포_대상이_꾸러미와_같은_것을_든다():
    # ★ **두 곳에 적으면 한쪽만 늙는다**(§91). 꾸러미가 담는 것은 `worker/app` 이고
    #   워크플로가 미는 것은 거기에 `infra` 다. 이 눈도 **그 둘만** 봐야 한다.
    절 = 배포절()
    assert "worker/app infra" in 절, "배포 대상 목록이 꾸러미와 다르다"
    assert "extension" not in 절, "태그가 안 싣는 것을 본다 — 거짓 경고가 된다"
    pkg = (ROOT / "tools/lib/pkg.py").read_text(encoding="utf-8")
    assert '"app"' in pkg or "'app'" in pkg, "꾸러미가 app 을 안 든다 — 전제가 바뀌었다"


def test_AWS_를_안_부른다():
    # ★ **이 눈을 다는 데 권한이 필요 없다**(§186 과 같은 결론). 부르면 그 응답에
    #   `WORKER_TOKEN` 이 평문으로 들어 있다.
    절 = 배포절()
    for 금지 in ("aws ", "lambda", "get-function", "terraform "):
        assert 금지 not in 절, f"배포 절이 {금지!r} 를 부른다"


def test_판정이지_건너뜀이_아니다():
    # ★ **「재지 못했다」 로 흘려보내면 관문이 아니다**(§59 · §54). 뒤처졌을 때는
    #   반드시 `warn` 으로 말한다 — `skip` 은 **태그가 아예 없을 때**만이다.
    절 = 배포절()
    assert "warn " in 절, "뒤처짐을 말하는 자리가 없다"
    assert 절.count("skip ") <= 2, 절.count("skip ")
    assert "git describe --tags" in 절


def test_못_보는_것을_적는다():
    # ★ **태그를 밀었다고 배포가 성공한 것은 아니다.** `ci_status` 는 가지로 걸러 묻기
    #   때문에 태그가 띄운 판을 못 본다 — 그 경계를 안 적으면 다음 사람이
    #   「태그 밀었으니 올라갔다」 로 읽는다(§190 · §305 와 같은 결).
    assert "이 눈 밖" in 배포절()


def test_고치는_길을_명령으로_적는다():
    # ★ **잡는 것과 고치는 것은 다른 일이다**(§180). 무엇을 쳐야 하는지 적어 둔다.
    assert "git tag" in 배포절() and "git push origin" in 배포절()


def test_실물_저장소에서_돌려_본다():
    # ★ **순수한 글 검사만 하면 배선을 안 잰다**(§173). 실제로 `git` 에 물어본다.
    r = subprocess.run(["git", "describe", "--tags", "--abbrev=0"],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        return                                  # 태그 없는 사본 — `skip` 가지가 맡는다
    태그 = r.stdout.strip()
    n = subprocess.run(["git", "diff", "--name-only", f"{태그}..HEAD", "--", "worker/app", "infra"],
                       cwd=ROOT, capture_output=True, text=True)
    assert n.returncode == 0, n.stderr
    # 「몇이냐」 는 안 묻는다 — 0 이든 10 이든 **셀 수 있다**는 것이 이 시험이 묻는 것이다
    assert all("/" in x for x in n.stdout.split())


def test_CI_가_워커_건너뜀도_센다():
    # ★ **확장만 보던 자를 워커에도 둔다**(DECISIONS §192). 2026-10-14 에
    #   `.build/fig` 에 매달린 pytest 하나가 **CI 에서만** 건너뛰어졌고, 그 사실은
    #   「문서 건수가 다르다」 라는 **엉뚱한 자리**에서만 새어 나왔다.
    글 = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "워커 시험이 건너뛰이지 않았는지" in 글, "워커 건너뜀을 세는 단계가 없다"
    # ★ **토막을 끊어서 본다.** 첫 판은 그 이름 뒤 **전부**를 토막으로 삼았고, 그래서
    #   **뒷 단계의 `exit 1` 을 읽고** 통과했다 — 막는 줄을 지워도 안 울었다(돌연변이가 잡았다).
    #   한 단계는 다음 `- name:` 앞까지다.
    머리 = 글.index("워커 시험이 건너뛰이지 않았는지")
    끝 = 글.find("\n      - name:", 머리)
    토막 = 글[머리:끝 if 끝 != -1 else len(글)]
    assert "skipped" in 토막, 토막[:300]
    assert 'exit 1' in 토막, "건너뛰어도 안 막는다"
    assert "working-directory: worker" in 토막, 토막[:400]


def test_확장_쪽_자도_그대로_있다():
    # ★ **더하면서 지우지 않았는지 본다**(§152 와 같은 결). 둘 다 있어야 한다.
    글 = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "확장 검사가 건너뛰이지 않았는지" in 글


# ── PLAN 번호 재사용 ─────────────────────────────────────────────────────


def _plan() -> str:
    return (ROOT / "docs/PLAN.md").read_text(encoding="utf-8")


def _적힌_번호들() -> set[int]:
    """문서가 `PLAN #N` 으로 부른 번호 전부 — **닫힌 것까지.**"""
    글 = _plan() + (ROOT / "docs/DECISIONS.md").read_text(encoding="utf-8") \
        + (ROOT / "docs/MASTER.md").read_text(encoding="utf-8")
    return {int(m) for m in re.findall(r"PLAN #(\d+)", 글)}


def _산_행들() -> list[int]:
    return [int(m) for m in re.findall(r"^\| (\d+) \|", _plan(), re.M)]


def test_다음_번호가_적혀_있다():
    # ★ **닫힌 행은 지운다.** 그래서 살아 있는 표만 보면 빈 번호가 **비어 보인다** —
    #   2026-10-14 에 그렇게 `#69` 를 다시 썼다(DECISIONS §193). 다음 번호를 **적어 둔다.**
    m = re.search(r"<!--plan:다음-->(\d+)", _plan())
    assert m, "PLAN 이 다음 행 번호를 안 적는다"
    assert int(m.group(1)) >= 1


def test_다음_번호가_과거에_적힌_어떤_번호보다_크다():
    # ★ **이것이 재사용을 막는 유일한 기계적 자리다.** `#69` 를 다시 쓰려면 이 수가
    #   70 이하여야 하는데, 과거가 70 을 들고 있으므로 거짓이 된다.
    다음 = int(re.search(r"<!--plan:다음-->(\d+)", _plan()).group(1))
    적힌 = _적힌_번호들()
    assert 적힌, "PLAN #N 을 부르는 글이 하나도 없다 — 이 검사가 아무것도 안 묻는다"
    assert 다음 > max(적힌), f"다음 번호 {다음} 가 이미 쓰인 {max(적힌)} 이하다"


def test_살아_있는_행이_다음_번호보다_작다():
    다음 = int(re.search(r"<!--plan:다음-->(\d+)", _plan()).group(1))
    산것 = _산_행들()
    assert 산것, "살아 있는 행이 없다 — 표를 못 읽었다"
    assert max(산것) < 다음, (max(산것), 다음)


def test_행_번호가_안_겹친다():
    산것 = _산_행들()
    assert len(산것) == len(set(산것)), sorted(산것)


def test_표의_행수와_제목이_맞는다():
    # ★ **같은 수를 두 곳에 적으면 한쪽만 늙는다**(§57). 제목이 그 수를 든다.
    글 = _plan()
    m = re.search(r"^## 1\. 남은 일 — (\d+)행", 글, re.M)
    assert m, "제목이 행수를 안 든다"
    assert int(m.group(1)) == len(_산_행들()), (m.group(1), len(_산_행들()))
