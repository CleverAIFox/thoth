"""`tools/ci_status.py` — **CI 가 지금 커밋을 초록으로 봤는가**의 판정이 사는 자리.

★ **세샤트의 `tests/test_ci_status.py` 에서 왔다. 정본은 세샤트다**(DECISIONS §162).
  갈린 자리는 셋이고 **셋을 여기 적는다**(세샤트 §296).
    · 강제자가 `tools/doctor.sh` 다. 세샤트는 `tools/verify.sh`
    · 실물 워크플로 이름이 다르다 — 이쪽은 `ci` · `deploy` · `drift` · `기획서 배포`.
      합성 판에 **실재하는 이름**을 써야 「파일에 없는 워크플로」 가름이 실제로 돈다
    · 아래 `★` 들의 `§N` 은 **세샤트의 절 번호**다. 이쪽에서 그 번호는 딴 절이다
★ **같은 자리를 저쪽이 네 번 고쳤다** — 세샤트 §172(정렬) · §292(워크플로마다 하나) ·
  §293(창을 나눈다) · §295(§294 의 틀린 전제를 걷어냈다). **다음 층을 찾을 때 그
  목록부터 읽는다** — 그 네 층이 전부 「한 판만 봤다」 의 변종이었다.
"""
import json
import pathlib

ROOT = next(p for p in pathlib.Path(__file__).resolve().parents
          if (p / "tools/ci_status.py").exists())   # worker/tests 에서 두 칸 올라간다

def test_doctor_가_CI_판정을_본다():
    """★ **이 기계가 초록인 것과 CI 가 초록인 것은 다른 말이다**(세샤트 DECISIONS §170).
    훅은 이 기계에만 있다 — 남의 PR 도 새로 받은 저장소도 안 막는다. **강제자는 CI 다.**
    2026-10-05 에 이쪽 CI 가 빨간 것을 `doctor` 가 초록으로 넘겼다(DECISIONS §162)."""
    v = (ROOT / "tools/doctor.sh").read_text(encoding="utf-8")
    assert "tools/ci_status.py" in v
    assert v.index("ci_status.py") > v.index("check_counts.py"), "CI 판정은 마지막에 본다"


def _CI():
    import importlib.util
    s = importlib.util.spec_from_file_location("ci_status", ROOT / "tools/ci_status.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def test_가장_최근_판을_직접_고른다():
    """★ **`gh run list -L 1` 이 「가장 최근」 을 준다고 믿었는데 아니었다**(세샤트 DECISIONS §172).
    열한 판 묵은 것을 주고 문은 그것을 「초록」 으로 찍었다 — **거짓 초록**이다."""
    C = _CI()
    판 = [{"headSha": "옛", "conclusion": "success", "createdAt": "2026-09-28T07:16:51Z"},
          {"headSha": "새", "conclusion": "failure", "createdAt": "2026-09-28T10:02:26Z"}]
    코드, 말 = C.고른다(판, "딴것")
    assert 코드 == 1 and "failure" in 말, "온 순서를 믿으면 옛 초록을 집는다"
    assert C.창 > 1, "창이 1 이면 목록이 빠뜨린 판을 영영 못 본다"


def test_아직_안_본_커밋을_초록으로_안_찍는다():
    """★ **「모른다」 는 통과가 아니다**(세샤트 DECISIONS §172 · §110). 밀기 전 HEAD 는 CI 가 본 적이 없다."""
    C = _CI()
    판 = [{"headSha": "옛", "conclusion": "success", "createdAt": "2026-09-28T07:00:00Z"}]
    코드, 말 = C.고른다(판, "아직")
    assert 코드 == 0 and "아직 안 봤다" in 말, "밀기 전이면 막지 않는다"
    assert "초록으로 봤다" not in 말, "안 본 것을 봤다고 적지 않는다"


def test_이_커밋의_판이_있으면_그것으로_판정한다():
    C = _CI()
    판 = [{"headSha": "여기", "conclusion": "failure", "createdAt": "2026-09-28T10:00:00Z"},
          {"headSha": "옛", "conclusion": "success", "createdAt": "2026-09-28T07:00:00Z"}]
    assert C.고른다(판, "여기")[0] == 1
    판[0]["conclusion"] = "success"
    assert C.고른다(판, "여기")[0] == 0
    판[0]["conclusion"] = ""        # 도는 중
    assert C.고른다(판, "여기")[0] == 0


# ---------- 작업 시간 상한 (파이어레인 tools/actionpin.py · 세샤트 DECISIONS §283) ----------



# ── 판정은 워크플로마다 하나씩 본다(세샤트 DECISIONS §292) ──────────────────────────
#
# ★ **2026-10-05 에 19분 사이에 판정이 실패 → 통과로 뒤집혔다.** 같은 sha `c950d4d` 인데
#   한 번은 `drift`(실패)를, 한 번은 `ci`(초록)를 집었다 — **그 사이에 고친 커밋이 없었다.**
#   §172 가 「`-L 1` 을 믿지 말라」 를 고쳤는데 **고친 뒤에도 판을 하나만 봤다.**
#   정렬은 「어느 판이 최신인가」 를 고쳤을 뿐이고 **「몇 판을 봐야 하는가」 는 안 고쳤다.**

def _판(wf, sha, 끝, 때):
    return {"workflowName": wf, "headSha": sha, "conclusion": 끝,
            "createdAt": 때, "displayTitle": f"{wf} {sha}", "url": "u"}


def test_초록인_워크플로가_빨간_것을_못_가린다():
    C = _CI()
    판 = [_판("ci", "여기", "success", "2026-10-05T07:30:00Z"),
          _판("drift", "여기", "failure", "2026-10-05T00:17:00Z")]
    코드, 말 = C.고른다(판, "여기")
    assert 코드 == 1, "더 최근인 초록이 옛 빨강을 가리면 §292 가 재발한다"
    assert "drift" in 말


def test_빨간_것이_더_최근이어도_같은_판정이다():
    # ★ **순서로 판정이 흔들리지 않는 것**이 이 고침의 뜻이다. 둘 다 빨강이어야 한다.
    C = _CI()
    판 = [_판("drift", "여기", "failure", "2026-10-05T07:30:00Z"),
          _판("ci", "여기", "success", "2026-10-05T00:17:00Z")]
    assert C.고른다(판, "여기")[0] == 1


def test_워크플로마다_제_최신을_본다():
    C = _CI()
    판 = [_판("ci", "여기", "success", "2026-10-05T07:00:00Z"),
          _판("ci", "옛", "failure", "2026-10-01T07:00:00Z"),
          _판("drift", "옛", "success", "2026-09-28T00:17:00Z")]
    코드, 말 = C.고른다(판, "여기")
    assert 코드 == 0, 말
    # `ci` 의 옛 빨강은 이 커밋의 초록에 지고, `drift` 는 **아직 안 본 것으로 적힌다** —
    # 하나라도 안 본 워크플로가 있으면 「모른다」 다. 그것을 초록으로 적으면 §172 가 재발한다.
    assert "ci 가 초록" in 말 and "아직 안 본 워크플로 : drift" in 말, 말


def test_이_커밋의_판이_그_워크플로의_옛_판을_이긴다():
    C = _CI()
    판 = [_판("ci", "옛", "failure", "2026-10-05T09:00:00Z"),
          _판("ci", "여기", "success", "2026-10-05T08:00:00Z")]
    assert C.고른다(판, "여기")[0] == 0, "이 커밋의 초록이 다른 커밋의 빨강에 져서는 안 된다"


def test_전부_이_커밋을_봤으면_그렇게_적는다():
    C = _CI()
    판 = [_판("ci", "여기", "success", "2026-10-05T09:00:00Z"),
          _판("drift", "여기", "success", "2026-10-05T08:00:00Z")]
    코드, 말 = C.고른다(판, "여기")
    assert 코드 == 0 and "워크플로 2 전부" in 말, 말


def test_막을_자격을_방아쇠에서_꺼낸다():
    """★ **손 목록을 안 만든다**(세샤트 DECISIONS §43 · §292). 「`gpu-eval` 은 빼자」 를 코드에 적으면
    워크플로가 하나 늘 때 그 목록이 늙는다. 저절로 도는 방아쇠가 있는지로 가른다."""
    C = _CI()
    표 = {"ci": {"push", "pull_request"}, "drift": {"schedule", "workflow_dispatch"},
          "손판": {"workflow_dispatch"}}
    assert C.막을자격("ci", 표) and C.막을자격("drift", 표)
    assert not C.막을자격("손판", 표), "손으로만 도는 실험은 코드의 판정이 아니다"
    assert not C.막을자격("지운것", 표), "파일을 못 찾은 워크플로의 옛 빨강이 영영 막아서는 안 된다"
    assert C.막을자격("", 표), "`gh` 가 이름을 안 준 것은 **못 잼**이다 — 못 잼은 통과가 아니다"


def test_실물_워크플로의_자격이_방아쇠와_맞는다():
    # ★ **실물에 돌린다**(§21). 합성만 보면 `name:` 을 못 읽는 정규식도 통과한다.
    C = _CI()
    표 = C.방아쇠(ROOT)
    assert len(표) == len(list((ROOT / ".github/workflows").glob("*.yml")))
    assert any(C.막을자격(k, 표) for k in 표), "막을 자격이 하나도 없으면 관문이 죽었다"
    assert all(v for v in 표.values()), "방아쇠를 못 읽은 워크플로가 있다 — 정규식이 늙었다"


def test_손으로만_도는_빨강은_막지_않고_적는다():
    C = _CI()
    판 = [_판("손판", "여기", "failure", "2026-10-05T09:00:00Z"),
          _판("ci", "여기", "success", "2026-10-05T08:00:00Z")]
    코드, 말 = C.고른다(판, "여기")
    assert 코드 == 0, 말
    assert "손판" in 말 and "안 막는 빨강" in 말, "삼키지 않고 적어야 한다"


def test_워크플로_이름이_없는_옛_꼴도_읽는다():
    # ★ `gh` 가 그 칸을 안 주던 때의 목록도 판정이 돌아야 한다 — 한 뭉치로 본다.
    C = _CI()
    판 = [{"headSha": "여기", "conclusion": "failure", "createdAt": "2026-10-05T09:00:00Z"}]
    assert C.고른다(판, "여기")[0] == 1


def test_판_칸에_워크플로_이름이_들어_있다():
    # ★ **안 받아 오면 전부 한 뭉치가 되고 §292 가 조용히 되살아난다.**
    C = _CI()
    assert "workflowName" in C._FIELDS


# ── 묻는 창도 워크플로마다다(세샤트 DECISIONS §293) ─────────────────────────────────
#
# ★ **2026-10-05 에 세샤트에서 `papers` 가 목록에서 사라졌다.** 빨간지 초록인지가 아니라 **아예 안
#   보였다.** `창 = 30` 은 **판의 수**이고 워크플로의 수가 아니다 — `ci` 와 GitHub 이 저절로
#   만드는 판(`Dependabot Updates` · `Dependency Graph`)이 창을 먹으니 **주 1회짜리가
#   밀려났다.** §292 가 「판을 하나만 봤다」 를 고쳤는데 **그 판들이 오는 창은 안 고쳤다.**

def test_워크플로마다_따로_묻는다():
    C = _CI()
    물은것 = []

    def 가짜(args):
        물은것.append(args[args.index("--workflow") + 1])
        return 0, "[]", ""

    C.판들(부른다=가짜, 파일들=["ci.yml", "drift.yml", "deploy.yml"])
    assert 물은것 == ["ci.yml", "drift.yml", "deploy.yml"], 물은것


def test_자주_도는_것이_주_1회짜리의_창을_안_먹는다():
    """★ **§293 의 실물 꼴이다.** 평평한 창 하나면 `ci` 판 서른이 `drift` 를 밀어낸다."""
    C = _CI()
    많음 = [_판("ci", f"c{i}", "success", f"2026-10-05T{i:02d}:00:00Z") for i in range(20)]
    주1회 = [_판("drift", "옛", "failure", "2026-09-29T00:17:00Z")]

    def 가짜(args):
        상한 = int(args[args.index("-L") + 1])
        이름 = args[args.index("--workflow") + 1]
        몫 = 많음 if 이름 == "ci.yml" else 주1회 if 이름 == "drift.yml" else []
        return 0, json.dumps(몫[:상한]), ""

    판 = C.판들(부른다=가짜, 파일들=["ci.yml", "drift.yml"])
    이름들 = {x["workflowName"] for x in 판}
    assert 이름들 == {"ci", "drift"}, f"창이 하나면 drift 가 사라진다 — {이름들}"


def test_묻는_목록을_파일에서_꺼낸다():
    C = _CI()
    실물 = C.워크플로파일(ROOT)
    있는것 = sorted(f.name for f in (ROOT / ".github/workflows").glob("*.yml"))
    assert 실물 == 있는것 and 실물, "묻는 목록이 손 목록이면 워크플로가 늘 때 늙는다"


def test_판을_못_읽으면_초록으로_안_찍는다():
    C = _CI()
    assert isinstance(C.판들(부른다=lambda a: (1, "", "죽었다"), 파일들=["ci.yml"]), str)
    assert isinstance(C.판들(부른다=lambda a: (0, "JSON 아님", ""), 파일들=["ci.yml"]), str)
    assert isinstance(C.판들(부른다=lambda a: (0, "[]", ""), 파일들=[]), str)


def test_판이_하나도_없는_워크플로를_적는다():
    # ★ 안 적으면 「물었는데 없었다」 와 「안 물었다」 가 같은 침묵이 된다 — §293 이 그 침묵이었다.
    C = _CI()
    코드, 말 = C.고른다([_판("ci", "여기", "success", "2026-10-05T09:00:00Z")], "여기")
    assert 코드 == 0 and "판이 하나도 없는 워크플로" in 말, 말


def test_창이_워크플로마다의_수다():
    C = _CI()
    assert 1 < C.창 <= 20, f"창 {C.창} — 워크플로마다의 판 수다. 크면 느리고 1 이면 §172 다"


# ── §294 에서 **고정자리가 잡아 준 것**만 남긴다(세샤트 DECISIONS §295) ──────────────
#
# ★ §294 의 평평한 질의는 **틀린 전제**였고 §295 가 걷어냈다. 다만 그 판에서 `url` 하나로
#   겹침을 가르다 **스물한 판이 한 판으로 뭉개진** 것은 실물 결함이었다 — 그 가름은 남긴다.

def _판u(wf, sha, 끝, 때, url):
    것 = _판(wf, sha, 끝, 때)
    것["url"] = url
    return 것


def _좁게(좁은: dict[str, list]):
    def 가짜(args):
        상한 = int(args[args.index("-L") + 1])
        return 0, json.dumps(좁은.get(args[args.index("--workflow") + 1], [])[:상한]), ""
    return 가짜


def test_가름이_한_칸이_아니다():
    """★ **한 칸으로 가르면 그 칸이 같을 때 서로 다른 판이 뭉개진다.** 고정자리에서 실제로
    스물한 판이 하나가 됐다 — `url` 을 다 `u` 로 둔 흉내였다."""
    C = _CI()
    많음 = [_판u("ci", f"c{i}", "success", f"2026-10-05T{i:02d}:00:00Z", "같은url")
            for i in range(5)]
    판 = C.판들(부른다=_좁게({"ci.yml": 많음}), 파일들=["ci.yml"])
    assert len(판) == 5, f"url 하나로 가르면 {len(판)} 이 된다"


def test_파일에_없는_워크플로는_빨갈_때만_든다():
    """★ **§293 이 치운 것을 §294 가 도로 끌어왔다**(세샤트 DECISIONS §295). GitHub 이 저절로
    만드는 초록 판이 「아직 안 본 워크플로」 를 소음으로 만든다. 빨강은 남긴다."""
    C = _CI()
    초록 = _판("Dependency Graph", "여기", "success", "2026-10-05T09:00:00Z")
    내것 = _판("ci", "여기", "success", "2026-10-05T08:00:00Z")
    코드, 말 = C.고른다([초록, 내것], "여기")
    assert 코드 == 0 and "Dependency Graph" not in 말, 말
    빨강 = _판("지운워크플로", "여기", "failure", "2026-10-05T09:00:00Z")
    코드2, 말2 = C.고른다([빨강, 내것], "여기")
    assert "지운워크플로" in 말2, "지워진 워크플로의 빨강은 적어야 한다"
def test_카나리아가_살아_있다():
    """★ **0 건이 목표인 검사는 0 건을 성공으로만 읽으면 안 된다**(MASTER §0-8 · 세샤트 DECISIONS §297).
    `_이름줄` 이 죽으면 `방아쇠` 가 파일 이름을 표시 이름으로 주고, 그러면 실물 워크플로
    전부가 「파일을 못 찾은 것」 이 되어 **빨강이 하나도 막지 않는다.**"""
    C = _CI()
    assert C.main(["--selftest"]) == 0


def test_카나리아가_정규식의_죽음을_본다(monkeypatch):
    """★ **카나리아가 제 죽음을 못 보면 카나리아가 아니다**(세샤트 DECISIONS §255)."""
    import re as _re
    import pytest
    C = _CI()
    monkeypatch.setattr(C, "_이름줄", _re.compile(r"^안맞는것:\s*(.+?)\s*$", _re.M))
    with pytest.raises(SystemExit) as e:
        C._canary()
    assert e.value.code == 2
