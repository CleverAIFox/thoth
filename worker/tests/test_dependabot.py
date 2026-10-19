"""**Dependabot 이 지금 무엇을 들고 있는가**(DECISIONS §194).

★ **`code_scanning` 도 `ci_status` 도 이것을 영영 못 본다.** 앞엣것은 CodeQL 경보만 묻고,
  뒤엣것은 `.github/workflows/*.yml` 에서 목록을 꺼내는데 **Dependabot 은 파일이 없다.**
  2026-10-15 에 `doctor` 가 「코드 스캐닝에 열린 경보 없음」 을 찍는 동안 **High 한 건이
  떠 있었다** — `source-map-js` 의 이벤트 루프 DoS. **참말이었고 모자랐다**(§171 과 같은
  자리, 다른 눈).

★ **아래 합성 경보는 실물에서 베꼈다.** 2026-10-15 에 `gh api .../dependabot/alerts` 를
  찍어 꼴을 재고 그 칸 이름을 그대로 쓴다 — **추측한 꼴로 가드를 세우지 않는다.**
"""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _DB():
    s = importlib.util.spec_from_file_location("dependabot", ROOT / "tools/dependabot.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def _경보(**덮기):
    """2026-10-15 의 실물 경보 — 칸 이름이 실측이다."""
    것 = {
        "state": "open", "number": 4,
        "security_advisory": {
            "summary": "source-map-js allows event-loop denial of service "
                       "through indexed source-map section offsets",
            "severity": "high"},
        "security_vulnerability": {"first_patched_version": {"identifier": "1.2.2"}},
        "dependency": {"scope": "development",
                       "manifest_path": "extension/package-lock.json",
                       "package": {"name": "source-map-js"}},
    }
    for k, v in 덮기.items():
        if k == "scope":
            것["dependency"]["scope"] = v
        elif k == "patched":
            것["security_vulnerability"]["first_patched_version"] = (
                {"identifier": v} if v else None)
        else:
            것[k] = v
    return 것


def test_dev_범위는_막지_않고_적는다():
    # ★ **그날 것이 바로 이 경우다.** `sync_ext.sh` 가 `node_modules/` 를 빼므로
    #   브라우저에 안 실린다 — 막을 값이 없다. 그렇다고 숨기면 그 판단이 **매번 사람
    #   머릿속에서만** 일어난다.
    막, 알 = _DB().판정([_경보()])
    assert 막 == [], 막
    assert len(알) == 1 and "source-map-js" in 알[0]


def test_runtime_범위는_막는다():
    막, 알 = _DB().판정([_경보(scope="runtime", number=9)])
    assert len(막) == 1 and 알 == []


def test_범위를_모르면_막는_쪽이다():
    # ★ **「모르겠으니 넘어간다」 가 §171 을 만들었다**(§59).
    것 = _경보()
    것["dependency"].pop("scope")
    막, 알 = _DB().판정([것])
    assert len(막) == 1 and 알 == []


def test_닫힌_경보는_안_센다():
    막, 알 = _DB().판정([_경보(state="fixed", scope="runtime")])
    assert (막, 알) == ([], [])


def test_고친_판이_없으면_그렇게_적는다():
    # ★ **「고치는 길이 한 줄인데 안 고치는 것」 과 「막을 길이 없는 것」 은 다른 말이다.**
    막, _ = _DB().판정([_경보(scope="runtime", patched=None)])
    assert "고친 판이 아직 없다" in 막[0], 막


def test_고친_판이_있으면_수를_싣는다():
    막, _ = _DB().판정([_경보(scope="runtime")])
    assert "1.2.2" in 막[0], 막


def test_면제는_이름으로_적는다():
    # ★ **번호로 적으면 같은 취약점이 새 번호로 그냥 통과한다.** 비어 있는 것이 정상이다.
    m = _DB()
    assert m.면제 == {}, m.면제
    m.면제["source-map-js"] = "시험"
    try:
        assert _DB_판정_빈가(m)
    finally:
        m.면제.clear()


def _DB_판정_빈가(m) -> bool:
    막, 알 = m.판정([_경보(scope="runtime")])
    return (막, 알) == ([], [])


def test_못_물으면_2_다_0_이_아니다():
    # ★ **경보가 없는 것과 못 묻는 것은 다른 말이다**(§59).
    m = _DB()
    것 = m.묻는다("x/y", 부른다=lambda a: type("R", (), {"returncode": 1, "stderr": "403", "stdout": ""}))
    assert isinstance(것, str) and "못 읽었다" in 것, 것


def test_JSON_이_아니면_못_쟀다():
    m = _DB()
    것 = m.묻는다("x/y", 부른다=lambda a: type("R", (), {"returncode": 0, "stderr": "", "stdout": "<html>"}))
    assert isinstance(것, str), 것


def test_doctor_가_이_도구를_부른다():
    글 = (ROOT / "tools/doctor.sh").read_text(encoding="utf-8")
    assert "tools/dependabot.py" in 글
    토막 = 글[글.index("tools/dependabot.py"):]
    assert "DB_RC" in 토막[:600], 토막[:300]
    # ★ **셋으로 가른다**(§59) — 0 초록 · 1 막는다 · 그 밖 **건너뜀**
    assert 'skip "Dependabot 경보를 묻지 못했다"' in 토막[:900], 토막[:900]


def test_저장소_이름을_두_벌로_안_든다():
    # ★ **정본을 두 벌로 두지 않는다**(§91). `code_scanning` 의 것을 읽어 쓴다.
    # ★ **글을 코드로 읽는 검사는 글부터 지운다** — 열다섯 번째다. 첫 판은
    #   「`github.com` 이 없어야 한다」 로 썼는데, **안내 명령의 `gh auth refresh -h
    #   github.com`** 을 읽고 빨개졌다. 묻는 것은 **원격 주소를 제 손으로 파싱하나**다.
    글 = (ROOT / "tools/dependabot.py").read_text(encoding="utf-8")
    assert "code_scanning.py" in 글, "저장소 이름의 정본을 안 읽어 쓴다"
    코드 = "\n".join(x for x in 글.splitlines() if not x.lstrip().startswith("#"))
    assert "re.compile" not in 코드, "원격 정규식을 또 적는다"
    assert "remote" not in 코드, "git remote 를 또 부른다"


def test_카나리아가_산다():
    # ★ **판별식이 죽으면 「경보 0 건」 이 되고 검사는 꺼진 채 초록이다** — §171 의 모양.
    _DB()._canary()


def test_카나리아가_가름이_죽으면_운다(monkeypatch):
    # ★ **「검사를 더했다」 와 「검사가 문다」 는 다른 말이다**(§152).
    import pytest
    m = _DB()
    monkeypatch.setattr(m, "판정", lambda 것: ([], []))
    with pytest.raises(SystemExit) as e:
        m._canary()
    assert e.value.code == 2
