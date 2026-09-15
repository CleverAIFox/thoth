"""워커 로그의 `usage` 줄을 모아 문자와 토큰을 나란히 놓는다.

  python3 tools/usage_report.py /tmp/w3.log                 한 판
  python3 tools/usage_report.py /tmp/w3.log /tmp/w9.log     판끼리 비교
  python3 tools/usage_report.py --drop-warmup /tmp/w3.log   첫 줄은 웜업이다

★ **세는 단위가 목적마다 다르다**(DECISIONS §78). `chars_used` 는 원문만 세고
  과금은 입력 토큰으로 매겨진다. 두 수를 한 표에 놓지 않으면 상한을 비용의
  대리 지표로 읽게 된다.

★ **배치별로 가른다.** 오버헤드는 요청 수에 비례하고 배치는 품질로도 값을
  매긴다(DECISIONS §80). 총합만 적으면 총액은 알아도 교환비를 모른다.

★ **웜업이 `n=1` 로 섞인다.** `bench_golden` 이 집계 밖에 두는 그 호출도
  Bedrock 을 때리므로 로그에는 남는다. 집계가 다른 두 수를 한 줄로 세면
  개별 폴백 건수가 실제보다 하나 많게 보인다 — `--drop-warmup` 이 그 한 줄을
  뺀다. **자동으로 빼지 않는다**: 프로덕션 로그에는 웜업이 없고, 무엇을 뺐는지
  모르는 집계가 가장 위험하다.

★ **개별 폴백이 `n=1` 로 드러난다.** 배치 파싱이 깨지면 호출 수가 n 배가 되고
  과금 엔진에서는 그대로 돈이다. 경고 로그로만 두면 빈도를 세지 않게 된다.

★ **못 잰 것을 0 으로 채우지 않는다**(DECISIONS §59). `usage` 가 없는 응답은
  `못 잼` 으로 세고, 하나라도 있으면 합계에 `부분` 을 붙인다. 채워 넣은 0 은
  합계를 조용히 낮춘다.

★ **단가를 곱하지 않는다**(DECISIONS §62). 이 도구는 토큰까지만 센다. 단가의
  정본은 결제 콘솔이고, 기억으로 적은 수를 곱하면 실측처럼 보이는 짐작이 된다.

★ **로그를 만들지 않는다.** 읽기만 한다. 워커를 띄우고 골든셋을 돌리는 것은
  부르는 쪽의 일이며 그 순서는 MASTER §11-13 에 있다.

  0  잰 것이 있다
  1  파일을 읽지 못했다
  3  `usage` 줄이 하나도 없다 — 못 잼이지 0 이 아니다
"""
import json
import pathlib
import re
import sys

MARK = re.compile(r"usage (\{.*\})\s*$")


def parse(text: str) -> list[dict]:
    """로그에서 `usage` 줄만 뽑는다. **줄 단위로 본다** — 로그 형식이 바뀌어도
    깨진 줄 하나가 판 전체를 버리지 않는다.
    """
    out = []
    for line in text.splitlines():
        m = MARK.search(line)
        if not m:
            continue
        try:
            u = json.loads(m.group(1))
        except ValueError:
            continue
        if isinstance(u, dict):
            out.append(u)
    return out


def group(rows: list[dict]) -> dict[int, dict]:
    """배치 크기별 합계. 못 잰 토큰은 더하지 않고 따로 센다."""
    g: dict[int, dict] = {}
    for r in rows:
        n = r.get("n") or 1
        b = g.setdefault(n, {"calls": 0, "units": 0, "body": 0, "head": 0,
                             "in_tok": 0, "out_tok": 0, "unmeasured": 0,
                             "measured": 0, "m_chars": 0})
        body = r.get("in_chars") or 0
        head = r.get("sys_chars") or 0
        b["calls"] += 1
        b["units"] += n
        b["body"] += body
        b["head"] += head
        if r.get("in_tok") is None or r.get("out_tok") is None:
            b["unmeasured"] += 1
        else:
            b["measured"] += 1
            # ★ 토큰을 잰 호출의 문자만 분모에 넣는다. 못 잰 호출의 문자를
            #   섞으면 문자당 토큰이 실제보다 낮게 나온다.
            b["m_chars"] += body + head
            b["in_tok"] += r["in_tok"]
            b["out_tok"] += r["out_tok"]
    return g


def total(g: dict[int, dict]) -> dict:
    t = {"calls": 0, "units": 0, "body": 0, "head": 0, "in_tok": 0,
         "out_tok": 0, "unmeasured": 0, "measured": 0, "m_chars": 0}
    for b in g.values():
        for k in t:
            t[k] += b[k]
    return t


def _ratio(a: int, b: int) -> str:
    """**못 잰 자리에 수를 적지 않는다.** 분모가 0 이면 비를 내지 않는다."""
    return f"{a / b:.2f}" if b else "—"


def _tok(b: dict, key: str) -> str:
    """**한 건도 재지 못한 칸은 0 이 아니라 `—` 다**(DECISIONS §59). 0 으로
    찍으면 '토큰을 쓰지 않았다' 로 읽힌다.
    """
    return f"{b[key]:,}" if b["measured"] else "—"


def render(name: str, rows: list[dict], dropped: int = 0) -> list[str]:
    g = group(rows)
    t = total(g)
    out = [f"== {name} ==",
           f"  요청 {t['calls']}회 · 유닛 {t['units']}개"]
    if dropped:
        # ★ 말없이 빠진 수는 다음에 읽는 사람에게 없던 수가 된다.
        out.append(f"  ★ 웜업 {dropped}건을 뺐다 (첫 usage 줄)")
    if t["unmeasured"]:
        out.append(f"  ★ 토큰을 못 잰 응답 {t['unmeasured']}건 — 아래 합계는 부분이다")

    out.append(f"  {'배치':>4} {'요청':>5} {'본문':>9} {'머리':>9} "
               f"{'입력토큰':>9} {'출력토큰':>9} {'머리/본문':>9} {'토큰/문자':>9}")
    for n in sorted(g):
        b = g[n]
        out.append(f"  {n:>4} {b['calls']:>5} {b['body']:>8,}자 {b['head']:>8,}자 "
                   f"{_tok(b, 'in_tok'):>9} {_tok(b, 'out_tok'):>9} "
                   f"{_ratio(b['head'], b['body']):>9} "
                   f"{_ratio(b['in_tok'], b['m_chars']):>9}")
    if len(g) > 1:
        out.append(f"  {'계':>4} {t['calls']:>5} {t['body']:>8,}자 {t['head']:>8,}자 "
                   f"{_tok(t, 'in_tok'):>9} {_tok(t, 'out_tok'):>9} "
                   f"{_ratio(t['head'], t['body']):>9} "
                   f"{_ratio(t['in_tok'], t['m_chars']):>9}")

    # ★ 개별 폴백은 배치가 깨졌다는 뜻이고 과금 엔진에서는 호출 수가 그대로
    #   돈이다. 표 안의 한 행으로 두면 지나친다.
    if 1 in g and len(g) > 1:
        tail = "" if dropped else " — 웜업을 빼지 않았다면 그중 한 건은 웜업이다"
        out.append(f"  ★ n=1 이 {g[1]['calls']}회. 개별 폴백이다{tail}")
    return out


def main(argv: list[str]) -> int:
    drop = "--drop-warmup" in argv
    paths = [pathlib.Path(a) for a in argv if not a.startswith("--")]
    if not paths:
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 1

    blocks, found = [], 0
    for p in paths:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"읽지 못했다 : {p} — {e}", file=sys.stderr)
            return 1
        rows = parse(text)
        dropped = 0
        if drop and rows:
            rows, dropped = rows[1:], 1   # 웜업은 언제나 첫 호출이다
        found += len(rows)
        if rows:
            blocks.append("\n".join(render(p.name, rows, dropped)))
        else:
            blocks.append(f"== {p.name} ==\n  usage 줄이 없다")

    print("\n\n".join(blocks))
    if not found:
        print("\n잰 것이 없다 — 엔진이 bedrock 이었는가. 캐시 히트는 호출하지 않는다",
              file=sys.stderr)
        return 3
    print("\n단가는 곱하지 않는다. 정본은 결제 콘솔이다(DECISIONS §62)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
