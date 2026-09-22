"""기획서의 차트. **숫자는 전부 산출물에서 읽는다** — 손으로 적은 수가 없다(DECISIONS §116)."""
import datetime as dt
import re

import numpy as np

from figlib import (AMBER, BASELINE, BLUE, GRAY, GREEN, LBLUE, LGRAY, RED, ROOT, decisions_ranges, load, plt, save)

B = load(BASELINE)
loc, bed = B["engines"]["local"], B["engines"]["bedrock"]
J = f"json:{BASELINE}#"

# ── 엔진 비교 ──────────────────────────────────────────
fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.5))
names = ["local\nexaone3.5:7.8b", "bedrock\nNova Lite"]
keys = [("speed.sec_per_question", "문항 하나 (초) — 낮을수록 좋다", "{:.1f}초"),
        ("speed.chars_per_sec", "처리율 (자/초) — 높을수록 좋다", "{:g}"),
        ("violations.units", "45유닛 위반 유닛 — 낮을수록 좋다", "{:d}")]
facts = []
for ax, (k, title, f) in zip(axs, keys):
    v = []
    for eng, blk in (("local", loc), ("bedrock", bed)):
        x = blk
        for p in k.split("."):
            x = x[p]
        v.append(x)
        facts.append(f"{J}engines.{eng}.{k}={x}")
    bars = ax.bar(names, v, color=[GRAY, BLUE], width=0.55)
    for b_, x in zip(bars, v):
        ax.text(b_.get_x() + b_.get_width() / 2, b_.get_height(), f.format(x), ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax.set_title(title, fontsize=8.5)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_ylim(0, max(v) * 1.22)
    ax.tick_params(labelsize=7.5)
facts += [f"{J}golden.units={B['golden']['units']}", f"{J}engines.local.stale=True"]
axs[2].text(0.5, -0.42, "local 은 옛 프롬프트 값(stale) — 위반은 같은 조건 비교가 아니다", transform=axs[2].transAxes, ha="center", fontsize=6.8, color=RED)
fig.tight_layout()
save(fig, "f_engine", facts)

# ── 배치 U자 (local) + bedrock 반복 ────────────────────
# ★ local 의 배치별 위반은 기준선의 주석에만 있다. 그 문자열을 그대로 읽는다.
note = loc["violations"]["_batch_note"]
m = re.search(r"배치 ([\d·]+) 에서 위반 유닛이 ([\d·]+)", note)
xs = [int(x) for x in m.group(1).split("·")]
ys = [int(y) for y in m.group(2).split("·")]
best = loc["batch"]
fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.6))
ax = axs[0]
ax.plot(xs, ys, "o-", color=GRAY, lw=1.8)
ax.plot([best], [ys[xs.index(best)]], "o", color=RED, ms=9, zorder=5)
for x, y in zip(xs, ys):
    ax.text(x, y + 0.45, str(y), ha="center", fontsize=8.5)
ax.set_xticks(xs); ax.set_ylim(0, max(ys) + 2)
ax.set_xlabel("배치 크기"); ax.set_ylabel(f"위반 유닛 ({B['golden']['units']}유닛)")
ax.set_title(f"local — 위반이 U자를 그린다 ({loc['date']})", fontsize=8.5)
ax.annotate(f"최적점 {best}\n(확장 MAX_BATCH)", (best, ys[xs.index(best)]), (5.2, 1.2), fontsize=7.5, color=RED, arrowprops=dict(arrowstyle="-|>", color=RED))
ax.spines[["top", "right"]].set_visible(False)
ax = axs[1]
sv = bed["batch_survey"]
facts = [f"file:{BASELINE}~{m.group(0)}", f"{J}engines.local.batch={best}", f"{J}engines.local.date={loc['date']}"]
for i, (k, col) in enumerate([("3", BLUE), ("9", AMBER)]):
    runs = sv[k]["violation_units"]
    ax.scatter(np.full(len(runs), i) + np.linspace(-0.12, 0.12, len(runs)), runs, s=60, color=col, zorder=3)
    ax.text(i, max(runs) + 0.6, " · ".join(map(str, runs)), ha="center", fontsize=8, color=col)
    facts.append(f"{J}engines.bedrock.batch_survey.{k}.violation_units={runs}")
ax.set_xticks([0, 1]); ax.set_xticklabels([f"배치 {bed['batch']}\n(채택)", "배치 9"])
ax.set_ylim(0, 7); ax.set_xlim(-0.6, 1.6)
ax.set_ylabel("위반 유닛 (같은 조건 네 판)")
ax.set_title("bedrock — 배치 9 는 판마다 갈린다 (2026-09-15)", fontsize=8.5)
ax.spines[["top", "right"]].set_visible(False)
facts += [f"{J}engines.bedrock.batch={bed['batch']}", f"file:{BASELINE}~2026-09-15 에 1·3·6·9·15 로 실측"]
fig.tight_layout()
save(fig, "f_batch", facts)

# ── 배치별 비용 ─────────────────────────────────────────
c = bed["cost"]
pin, pout = c["usd_per_1m_input"], c["usd_per_1m_output"]
ks = ["1", "3", "6", "9", "15"]
inc = [sv[k]["in_tok"] * pin / 1e6 * 1000 for k in ks]
outc = [sv[k]["out_tok"] * pout / 1e6 * 1000 for k in ks]
fig, ax = plt.subplots(figsize=(7.0, 2.7))
x = np.arange(len(ks))
ax.bar(x, outc, color=BLUE, label="출력 토큰", width=0.6)
ax.bar(x, inc, bottom=outc, color=LBLUE, edgecolor=BLUE, label="입력 토큰", width=0.6)
facts = [f"{J}engines.bedrock.cost.usd_per_1m_input={pin}", f"{J}engines.bedrock.cost.usd_per_1m_output={pout}",
         "file:docs/MASTER.md~출력이 비용의 83% 다", "file:docs/MASTER.md~금액으로는 7.9%"]
for i, k in enumerate(ks):
    tot = c["golden_run_usd"][k]
    ax.text(i, inc[i] + outc[i] + 0.08, f"${tot}", ha="center", fontsize=8, fontweight="bold" if k == "3" else "normal",
            color=RED if k == "3" else "black")
    facts += [f"{J}engines.bedrock.cost.golden_run_usd.{k}={tot}", f"{J}engines.bedrock.batch_survey.{k}.requests={sv[k]['requests']}"]
ax.set_xticks(x); ax.set_xticklabels([f"배치 {k}\n요청 {sv[k]['requests']}" for k in ks], fontsize=7.5)
ax.set_ylabel(f"{B['golden']['units']}유닛 한 판 비용 (1/1000 USD)")
ax.set_ylim(0, max(a + b for a, b in zip(inc, outc)) * 1.2)
ax.legend(fontsize=7.5, frameon=False, loc="upper left")
ax.text(4, max(a + b for a, b in zip(inc, outc)) * 1.12, "15 는 파싱 실패 → 개별 호출 폴백", ha="center", fontsize=7, color=RED)
ax.set_title("Nova Lite 배치별 비용 — 출력이 83% 라 배치를 키워도 7.9% 밖에 안 준다 (2026-09-15 실측 토큰 × 공개 단가)", fontsize=8.2)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
save(fig, "f_cost", facts)

# ── 어미 코퍼스 ─────────────────────────────────────────
# ★ 판정 수는 두 문서의 표에서 읽는다. 옛 판은 DECISIONS(추가만), 지금 판은 MASTER.
def row(path, head):
    for line in (ROOT / path).read_text(encoding="utf-8").splitlines():
        if line.startswith(head):
            cells = [x.strip().strip("*") for x in line.strip("|").split("|")]
            return line, [int(v.replace(",", "")) for v in cells[1:4]]
    raise SystemExit(f"{path} 에 '{head}' 줄이 없다")
old_line, old = row("docs/DECISIONS.md", "| 106 이전 |")
new_line, new = row("docs/MASTER.md", "| 106 (배포본")
fig, ax = plt.subplots(figsize=(7.0, 1.9))
rows = [("규칙 106 이전\n(생성기 1판)", *old), ("규칙 106\n(배포본 · 생성기 2판)", *new)]
for i, (n, ok, same, bad) in enumerate(rows):
    y = 1 - i
    ax.barh(y, ok, color=GREEN, height=0.55)
    ax.barh(y, same, left=ok, color=LGRAY, edgecolor=GRAY, height=0.55)
    ax.barh(y, bad, left=ok + same, color=RED, height=0.55)
    ax.text(ok / 2, y, f"맞음 {ok:,}", ha="center", va="center", color="white", fontsize=8)
    ax.text(ok + same / 2, y, f"그대로 {same:,}", ha="center", va="center", fontsize=8)
    ax.text(ok + same + bad + 25, y, f"틀림 {bad}", ha="left", va="center", color=RED, fontsize=8.5, fontweight="bold")
ax.set_yticks([1, 0]); ax.set_yticklabels([r[0] for r in rows], fontsize=8)
ax.set_xlim(0, 3000); ax.set_xlabel("줄 (코퍼스 + 손 43줄)")
ax.set_title(f"후처리 어미 변환 — 틀림만 게이트다. 톱니가 {new[2]} 이하로 막는다", fontsize=8.5)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
save(fig, "f_endings", [f"file:docs/DECISIONS.md~{old_line}", f"file:docs/MASTER.md~{new_line}",
                        f"file:worker/tests/test_endings_corpus.py~WRONG_CEILING = {new[2]}"])

# ── 추진 일정 ───────────────────────────────────────────
# ★ 절 범위는 DECISIONS 의 날짜 줄에서 센다. 이름표만 손으로 적는다.
LABEL = {
    "2026-09-12": "정찰 · 수집 계약 · 캐시 · 엔진 3분기",
    "2026-09-13": "골든셋 · 프롬프트 · 부분 응답 · 토큰",
    "2026-09-14": "배치 최적점 · 계약 분리 · Lambda 배포",
    "2026-09-15": "토큰 · 비용 실측 · 배치 9 기각",
    "2026-09-16": "S3 상태 · OIDC · 콜드패스 · 승인 게이트",
    "2026-09-19": "픽스처 자기 채점 · 관측 행",
    "2026-09-22": "어미 코퍼스 · HTTP 슬롯 · 강제자 · 닫기 · 기획서",
}
START = "2026-07-18"
rng = decisions_ranges()
missing = sorted(set(rng) - set(LABEL))
if missing:
    raise SystemExit(f"DECISIONS 에 이름표 없는 날짜가 있다: {missing} — LABEL 에 더한다")
D = dt.date.fromisoformat
fig, (a0, a1) = plt.subplots(2, 1, figsize=(7.2, 4.6), gridspec_kw={"height_ratios": [1, 2.6]})
# 위 — 전 기간
first = min(rng)
spans = [("선행 저장소 — 스크래핑 · AWS Translate · 폐기", START, (D(first) - dt.timedelta(1)).isoformat(), GRAY),
         ("thoth — 확장 · 워커 · 배포 · 쌍 로그 · 닫음", first, max(rng), BLUE),
         ("seshat — 자 · 후보 · 쌍 · 튜닝 · 서빙 (진행)", max(rng), "2026-09-30", GREEN)]
for i, (n, s, e, col) in enumerate(spans):
    y = len(spans) - i
    a0.barh(y, (D(e) - D(s)).days + 1, left=D(s).toordinal(), color=col, height=0.6, alpha=0.9 if i < 2 else 0.45,
            hatch=None if i < 2 else "///")
    a0.text(D(s).toordinal() + 0.5 if i == 0 else D(s).toordinal() - 1, y, n, ha="left" if i == 0 else "right", va="center",
            fontsize=7.2, color="white" if i == 0 else col, fontweight="bold")
ticks = [D(START)] + [D(f"2026-{m:02d}-01") for m in (8, 9)] + [D(first), D(max(rng))]
a0.set_xticks([d.toordinal() for d in ticks]); a0.set_xticklabels([d.strftime("%m-%d") for d in ticks], fontsize=7)
a0.set_yticks([]); a0.spines[["top", "right", "left"]].set_visible(False)
a0.set_xlim(D(START).toordinal() - 1, D("2026-09-30").toordinal() + 1)
a0.set_title(f"전 기간 — {START} 시작. 선행 저장소의 기록은 thoth 밖에 있다", fontsize=8.2)
# 아래 — thoth 일별
days = sorted(rng)
for i, d in enumerate(days):
    y = len(days) - i
    a, b = rng[d]
    a1.barh(y, 0.8, left=D(d).toordinal() - 0.4, color=BLUE, height=0.6)
    a1.text(D(d).toordinal() + 0.5, y, f"§{a}–§{b}" if a != b else f"§{a}", ha="left", va="center", fontsize=7, color=GRAY)
a1.set_yticks([len(days) - i for i in range(len(days))]); a1.set_yticklabels([LABEL[d] for d in days], fontsize=7.4, color=BLUE)
a1.tick_params(axis="y", length=0)
span = [D(days[0]) + dt.timedelta(k) for k in range((D(days[-1]) - D(days[0])).days + 1)]
a1.set_xticks([d.toordinal() for d in span]); a1.set_xticklabels([d.strftime("%m-%d") for d in span], fontsize=7)
a1.set_xlim(D(days[0]).toordinal() - 0.6, D(days[-1]).toordinal() + 1.8)
a1.spines[["top", "right", "left"]].set_visible(False)
a1.set_ylim(0.3, len(days) + 0.8)
a1.set_title("thoth 일별 — DECISIONS 절의 날짜 줄에서 센 범위 (기록 없는 날은 비어 있다)", fontsize=8.2)
fig.tight_layout()
save(fig, "f_gantt", [f"file:docs/MASTER.md~{START} 에 선행 저장소로 시작했다"] + [f"decisions:{d}=" + (f"§{a}–§{b}" if a != b else f"§{a}") for d, (a, b) in sorted(rng.items())])
print("charts ok")
