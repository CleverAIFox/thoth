from figlib import (AMBER, BLUE, GRAY, GREEN, LAMBER, LBLUE, LGRAY, LGREEN, LRED, NAVY, RED,
                    arrow, box, canvas, group, plt, save)
from matplotlib.patches import Ellipse, FancyBboxPatch

# ── 통합 아키텍처 ───────────────────────────────────────
fig, ax = canvas(7.4, 5.2, 100, 70)
group(ax, 1, 46, 33, 22, "브라우저 · 크롬 확장 (MV3)", BLUE)
box(ax, 3, 55, 14, 7, "어댑터\n3계층 수집", fs=7)
box(ax, 18.5, 55, 14, 7, "브로커\n배치 3 · 삽입", fs=7)
box(ax, 3, 47.5, 14, 6, "팝업\n켜기 · 토글", fs=7)
box(ax, 18.5, 47.5, 14, 6, "클라이언트\n5xx 만 재시도", fs=7)
arrow(ax, 17, 58.5, 18.5, 58.5)
arrow(ax, 25.5, 55, 25.5, 53.5)
group(ax, 37, 29, 36, 39, "워커 · Lambda (서울) — thoth", BLUE)
for i, (t, s_) in enumerate([("계약", "검증 · 토큰 · 응답 형태"), ("캐시", "sha256(원문) → DynamoDB"),
                            ("가드", "월 2,000,000자 · 조건부 ADD"), ("용어집", "원문에 맞은 항목만"),
                            ("엔진", "bedrock(배포) · http(빈 자리)"), ("후처리", "물음표 뒤 자름 · 합쇼체")]):
    box(ax, 39, 58.5 - i * 5, 32, 3.8, f"{i+1}. {t}  —  {s_}", fs=6.8, ha="left")
arrow(ax, 32.5, 50.5, 39, 60.4, color=BLUE)
ax.text(17.5, 42.5, "→ POST /translate + X-Thoth-Token", fontsize=6.5, color=BLUE, ha="center")
box(ax, 77, 55, 21, 8, "Bedrock Converse\nNova Lite (배포본)", fc=LGRAY, ec=GRAY, fs=7)
arrow(ax, 71, 40.4, 77, 57, color=GRAY)
ax.text(79, 47, "ENGINE=bedrock", fontsize=6.5, color=GRAY)
box(ax, 41, 20, 14, 6, "DynamoDB\n캐시 · 카운터", fc=LGRAY, ec=GRAY, fs=7)
arrow(ax, 48, 29, 48, 26)
group(ax, 58, 2, 41, 24, "seshat — 비공개 · 모델 공방", GREEN)
box(ax, 60, 12, 18, 7, "serve.py\n계약 서버", fc=LGREEN, ec=GREEN, fs=7)
box(ax, 79.5, 12, 18, 7, "backends.py\n모델 자리 (echo)", fc=LGREEN, ec=GREEN, fs=7)
box(ax, 60, 3.5, 18, 7, "evaluate.py\n평가 4지표", fc=LGREEN, ec=GREEN, fs=7)
box(ax, 79.5, 3.5, 18, 7, "licenses.py\n라이선스 대장", fc=LGREEN, ec=GREEN, fs=7)
arrow(ax, 78, 15.5, 79.5, 15.5)
arrow(ax, 67, 38.6, 69, 19, color=GREEN, ls="--")
ax.text(76, 32, "ENGINE=http\n/translate · /health", fontsize=6.5, color=GREEN)
group(ax, 1, 2, 52, 16, "콜드패스 — 학습 전용 · 공개하지 않는다", AMBER)
for i, t in enumerate(["stdout\nJSON 한 줄", "구독 필터\n$.k=pair", "Firehose\n→ Parquet", "S3 · Glue\nAthena"]):
    box(ax, 3 + i * 12.5, 4, 10.5, 8, t, fc=LAMBER, ec=AMBER, fs=6.5)
    if i:
        arrow(ax, 3 + i * 12.5 - 2, 8, 3 + i * 12.5, 8, color=AMBER)
arrow(ax, 39, 38, 8, 12, color=AMBER, ls="--", cs="arc3,rad=0.2")
ax.text(12, 31, "캐시 미스 한 건 = 쌍 한 줄", fontsize=6.8, color=AMBER)
arrow(ax, 50.5, 8, 60, 7, color=AMBER, ls="--")
ax.text(55.5, 10.5, "추출\n#6", fontsize=6, color=AMBER, ha="center")
save(fig, "f_arch", ["file:worker/app/guard.py~\"MAX_CHARS_PER_MONTH\", \"2000000\"", "json:docs/bench/baseline.json#engines.bedrock.batch=3", "json:docs/bench/baseline.json#engines.bedrock.model=apac.amazon.nova-lite-v1:0"])

# ── 유스케이스 ─────────────────────────────────────────
fig, ax = canvas(7.2, 4.4, 100, 61)
def actor(x, y, name, col):
    ax.add_patch(plt.Circle((x, y + 5), 1.6, fc="white", ec=col, lw=1.3))
    ax.plot([x, x], [y + 3.4, y - 0.5], color=col, lw=1.3)
    ax.plot([x - 2.5, x + 2.5], [y + 2, y + 2], color=col, lw=1.3)
    ax.plot([x, x - 2], [y - 0.5, y - 3.5], color=col, lw=1.3); ax.plot([x, x + 2], [y - 0.5, y - 3.5], color=col, lw=1.3)
    ax.text(x, y - 8.5, name, ha="center", fontsize=7.5, color=col, fontweight="bold")
actor(8, 44, "학습자\n(작성자 본인)", BLUE)
actor(8, 16, "배포자\n(작성자 본인)", NAVY)
actor(92, 30, "모델 개발자\n(작성자 본인)", GREEN)
group(ax, 18, 2, 64, 57, "thoth + seshat", GRAY, ls="-")
uc = [
    (32, 52, "UC-01 사이트에서 번역 켜기", BLUE), (32, 45, "UC-02 문항 번역 보기", BLUE), (32, 38, "UC-03 번역 표시 끄기 Alt+K", BLUE),
    (32, 31, "UC-04 연결 확인", BLUE), (32, 22, "UC-05 태그로 배포 · 승인", NAVY), (32, 15, "UC-06 상한 · 비용 · 드리프트 점검", NAVY),
    (32, 8, "UC-07 쌍 적재 확인", NAVY),
    (68, 50, "UC-08 평가셋으로 재기", GREEN), (68, 42, "UC-09 후보 모델 기준선", GREEN), (68, 34, "UC-10 쌍 추출 · 튜닝", GREEN),
    (68, 26, "UC-11 적합성 검사 통과", GREEN), (68, 18, "UC-12 엔진 한 줄로 끼우기", NAVY), (68, 10, "UC-13 라이선스 대장 기록", GREEN),
]
for x, y, t, c in uc:
    ax.add_patch(Ellipse((x, y), 29, 5.4, fc="white", ec=c, lw=1.1))
    ax.text(x, y, t, ha="center", va="center", fontsize=7)
for _, y, _, c in uc[:4]:
    ax.plot([11, 18.5], [46, y], color=BLUE, lw=0.7)
for _, y, _, c in uc[4:7]:
    ax.plot([11, 18.5], [18, y], color=NAVY, lw=0.7)
for _, y, _, c in uc[7:]:
    ax.plot([89, 81.5], [32, y], color=GREEN, lw=0.7)
ax.plot([11, 54.5], [18, 18], color=NAVY, lw=0.7, ls=":")
save(fig, "f_usecase", ["none"])

# ── 요청 시퀀스 ─────────────────────────────────────────
fig, ax = canvas(7.4, 5.2, 100, 70)
lanes = [("브로커", 7), ("클라이언트", 21), ("계약", 36), ("캐시", 51), ("가드", 65), ("엔진", 79), ("쌍 로그", 93)]
for n, x in lanes:
    box(ax, x - 5.5, 64, 11, 4.5, n, fs=7.5, bold=True)
    ax.plot([x, x], [2, 64], color=GRAY, lw=0.7, ls=":")
steps = [
    (7, 21, "유닛 3개 (group 단위)"), (21, 36, "POST texts[3] · source{site,adapter}"), (36, 36, "validate · 토큰 compare_digest"),
    (36, 51, "batch_get(sha256)"), (51, 36, "히트 1 · 미스 2"), (36, 65, "reserve(미스 문자 수)"), (65, 36, "OK  (넘으면 429 / 히트 있으면 200 partial)"),
    (36, 79, "미스 2 + 맞은 용어"), (79, 36, "raw → 후처리 → ko   (길이 틀리면 502)"), (36, 51, "put — 영구 · TTL 없음"), (36, 93, "쌍 2줄 — .local 은 빼고"),
    (36, 21, "translations[3] · cached[t,f,f]"), (21, 7, "박스 삽입 · 길이 불변식 검사"),
]
y = 60
for a, b, t in steps:
    if a == b:
        ax.text(a + 1.2, y, "(내부) " + t, fontsize=6.8, va="center", ha="left", color=BLUE)
        y -= 4.4
        continue
    col = BLUE if b > a else GREEN
    arrow(ax, a, y, b, y, color=col, lw=1.0)
    ax.text((a + b) / 2, y + 1.1, t, ha="center", fontsize=6.8, bbox=dict(fc="white", ec="none", pad=0.2))
    y -= 4.4
save(fig, "f_seq", ["json:docs/bench/baseline.json#engines.bedrock.batch=3", "file:infra/storage.tf~캐시 항목에는 그것이 없다"])

# ── 어댑터 선택 ─────────────────────────────────────────
fig, ax = canvas(7.2, 3.0, 100, 42)
box(ax, 2, 16, 16, 10, "페이지\nlocation · root", fc=LGRAY, ec=GRAY)
arrow(ax, 18, 21, 24, 21)
box(ax, 24, 16, 16, 10, "priority 내림차순\nmatch() 가 참인\n첫 어댑터", fs=7.5)
for i, (n, p, d, c) in enumerate([("udemy  ·  10", "사이트 지식 있음", ".quiz-page-content 안만 — 선언된 예외", RED),
                                  ("standard  ·  5", "ARIA · 폼 표준", "자기 몫 뒤 나머지를 generic 에 위임", BLUE),
                                  ("generic  ·  0", "match 항상 참", "요소 순회. 어댑터 없어도 번역된다", GRAY)]):
    yy = 30 - i * 11
    box(ax, 48, yy, 20, 8, f"{n}\n{p}", fc="white", ec=c, fs=7.5)
    ax.text(70, yy + 4, d, fontsize=7.2, va="center", color=c)
    arrow(ax, 40, 21, 48, yy + 4, color=c)
ax.text(2, 4, "선택은 배타적이다 — 이긴 하나만 돈다. 그래서 상위 계층은 하위 계층의 상위집합이어야 한다(DECISIONS §11 · §39).", fontsize=7.5, color=NAVY)
save(fig, "f_adapter", ["file:extension/src/adapters/udemy.js~priority: 10", "file:extension/src/adapters/standard.js~priority: 5", "file:extension/src/adapters/generic.js~priority: 0"])

# ── thoth ↔ seshat 계약 ────────────────────────────────
fig, ax = canvas(7.4, 4.4, 100, 60)
for n, x, c, fc in [("배포자", 8, NAVY, LBLUE), ("thoth 전검사\npreflight", 30, BLUE, LBLUE), ("thoth 워커\nengine.py", 54, BLUE, LBLUE), ("seshat\nserve.py", 82, GREEN, LGREEN)]:
    box(ax, x - 8, 52, 16, 6.5, n, fc=fc, ec=c, fs=7.5, bold=True)
    ax.plot([x, x], [2, 52], color=GRAY, lw=0.7, ls=":")
rows = [
    (8, 82, "① engine_conformance.py — health·한 건·아홉 건·순서·terms·개행·토큰 거절", NAVY),
    (82, 8, "전부 OK", GREEN),
    (8, 30, "② ENGINE=http · HTTP_URL · HTTP_MODEL", NAVY),
    (30, 82, "GET /health", BLUE),
    (82, 30, '{"model": "…"} — HTTP_MODEL 과 다르면 model_mismatch 로 기동을 막는다', GREEN),
    (8, 54, "③ tfvars engine=\"http\" → 손 plan(/tmp) → apply", NAVY),
    (54, 82, 'POST /translate {"texts", "source":"en", "target":"ko", "terms"} + Bearer', BLUE),
    (82, 54, '{"translations": [...]} — 같은 길이 · 같은 순서 · 문자열', GREEN),
    (54, 54, "어긋나면 EngineContractError → 502 engine_failed (개별 폴백 없음)", RED),
    (8, 54, "④ 되돌리기 — engine = \"bedrock\" 한 줄. 캐시는 엔진을 가리지 않는다", NAVY),
]
y = 47
for a, b, t, c in rows:
    if a == b:
        ax.text(a + 1.5, y, t, fontsize=6.8, color=c, va="center")
    else:
        arrow(ax, a, y, b, y, color=c)
        ax.text((a + b) / 2, y + 1.3, t, ha="center", fontsize=6.6, color="black", bbox=dict(fc="white", ec="none", pad=0.2))
    y -= 4.7
save(fig, "f_slot", ["file:tools/engine_conformance.py~terms", "file:worker/app/preflight.py~model_mismatch"])

# ── 콜드패스 ───────────────────────────────────────────
fig, ax = canvas(7.4, 2.9, 100, 38)
st = [("Lambda\nstdout", "thoth.pair 로거\n접두사 없음"), ("로그 그룹", "구독 필터\n{ $.k = \"pair\" }"), ("Firehose", "GZIP 해제·추출\nJSON → Parquet"),
      ("S3", "pairs/dt=날짜/\nforce_destroy 끔"), ("Glue", "thoth.pairs\n파티션 투영"), ("Athena", "읽을 때 거른다\nsite NOT IN 로컬")]
for i, (a, b) in enumerate(st):
    x = 1 + i * 16.5
    box(ax, x, 20, 14, 8, a, fc=LAMBER, ec=AMBER, bold=True, fs=8)
    ax.text(x + 7, 15, b, ha="center", va="center", fontsize=6.8, color=GRAY)
    if i:
        arrow(ax, x - 2.5, 24, x, 24, color=AMBER)
box(ax, 62, 1, 37, 7, "seshat #6 쌍 추출 → data/private/ (git 무시)", fc=LGREEN, ec=GREEN, fs=6.8)
arrow(ax, 97.5, 20, 95, 8, color=GREEN, ls="--")
ax.text(1, 34, "쓰지 않는 것 — 캐시 히트 · 로컬 출처(.local · 127.0.0.1 · localhost) · 검사 축 판정(읽을 때 bench_golden 함수로 한다)", fontsize=7.2, color=RED)
ax.text(1, 3.5, "첫 실측 2026-09-16 — probe 한 건이 Parquet 3,440바이트가 되고 Athena 가 읽었다", fontsize=7, color=GRAY)
save(fig, "f_coldpath", ["file:docs/MASTER.md~Parquet 3,440바이트", "file:worker/app/pairs.py~.local"])

# ── ERD 풍 스키마 ──────────────────────────────────────
fig, ax = canvas(7.4, 4.6, 100, 62)
def ent(x, y, w, title, cols, ec=BLUE, fc=LBLUE):
    h = 3.4 + len(cols) * 2.55
    ax.add_patch(FancyBboxPatch((x, y - h), w, h, boxstyle="round,pad=0,rounding_size=0.8", fc="white", ec=ec, lw=1.1))
    ax.add_patch(FancyBboxPatch((x, y - 3.4), w, 3.4, boxstyle="round,pad=0,rounding_size=0.8", fc=fc, ec=ec, lw=1.1))
    ax.text(x + w / 2, y - 1.7, title, ha="center", va="center", fontsize=7.6, fontweight="bold")
    for i, c in enumerate(cols):
        ax.text(x + 1, y - 4.9 - i * 2.55, c, fontsize=6.5, va="center", family="monospace" if False else None)
    return y - h
ent(1, 60, 30, "DynamoDB · 캐시 항목", ["PK  h = sha256(원문)", "ko         번역 결과", "TTL 없음 — 영구 (재과금 방지)", "", "같은 테이블 · 카운터 항목", "PK  h = quota#YYYY-MM", "chars      조건부 ADD", "expires_at 다음 달 + 7일"])
ent(35, 60, 30, "pairs (Parquet · Glue)", ["k · v        판별자 · 스키마", "ts · h       ms · sha256(src)", "src          원문", "raw          모델 출력", "ko           후처리 결과", "engine · model · prompt", "book · n     용어집 · 미스 수", "site · adapter · ver", "dt           파티션"], AMBER, LAMBER)
ent(69, 60, 30, "golden case (thoth)", ["id           q1 … q5", "units[]      45유닛 · 13,954자", "terms · keep 기대", "창작 지문 · 원문 아님"])
ent(69, 38, 30, "eval row (seshat)", ["id · src · ref · keep", "seed 12줄 · CC0", "ref 는 검수 전"], GREEN, LGREEN)
ent(1, 30, 30, "glossary/aws.json", ["en(소문자) → ko", "항등 항목 = 영어 유지", "37 항목"])
ent(69, 22, 30, "licenses.py 대장", ["model · source", "license · commercial", "yes / no / unknown"], GREEN, LGREEN)
arrow(ax, 31, 55, 35, 55, "h = h", color=GRAY, off=(0, 1.4))
arrow(ax, 16, 30, 40, 36, "book", color=GRAY, off=(0, 1.2), cs="arc3,rad=-0.2")
arrow(ax, 65, 40, 69, 36, "추출(#6)", color=GREEN, ls="--", off=(-2, -1.8))
ax.text(35, 8, "★ 사용자 식별자가 어느 표에도 없다.\n   키는 원문 해시와 달이다.", fontsize=7.4, color=NAVY)
save(fig, "f_erd", ["len:worker/app/glossary/aws.json=37", "json:docs/bench/baseline.json#golden.units=45", "json:docs/bench/baseline.json#golden.chars=13954", "file:infra/storage.tf~quota#2026-09"])

# ── seshat 계획 DAG ────────────────────────────────────
fig, ax = canvas(7.4, 3.8, 100, 50)
N = {1: (4, 36, "#1 평가셋 1판\n12 → 100줄"), 3: (4, 20, "#3 신경망 지표\nCOMET · QE"), 2: (4, 4, "#2 ⚠ Bedrock 출력\n학습 사용 조건"),
     4: (26, 36, "#4 Nova Lite\n기준선"), 5: (48, 36, "#5 후보 기준선\n학습 없이 서넛"), 10: (70, 40, "#10 (미결정) seq2seq\nvs 디코더 LLM"),
     6: (26, 12, "#6 쌍 추출\nAthena → private"), 11: (48, 4, "#11 쌍 집계\n히트율 · 미등재 용어"),
     7: (68, 22, "#7 LoRA · QLoRA\nT4 · 스팟"), 8: (88, 22, "#8 서빙\n양자화·적합성"), 9: (48, 20, "#9 주 1회\n연구 폴링")}
for k, (x, y, t) in N.items():
    fc, ec = (LAMBER, AMBER) if k in (2, 10) else (LGREEN, GREEN)
    box(ax, x, y, 18 if k != 8 else 11.5, 8, t, fc=fc, ec=ec, fs=6.8 if k != 8 else 6.2)
E = [(1, 4), (4, 5), (5, 10), (5, 7), (2, 6), (3, 6), (6, 7), (6, 11), (7, 8), (9, 5)]
def c(k, side):
    x, y, _ = N[k]; w = 18 if k != 8 else 11
    return {"r": (x + w, y + 4), "l": (x, y + 4), "t": (x + w / 2, y + 8), "b": (x + w / 2, y)}[side]
for a, b in E:
    xa, ya = c(a, "r"); xb, yb = c(b, "l")
    if a == 9: xa, ya = c(9, "t"); xb, yb = c(5, "b")
    arrow(ax, xa, ya, xb, yb, color=GREEN)
box(ax, 84, 3, 15, 10, "thoth PLAN #59\nengine = \"http\"", fc=LBLUE, ec=BLUE, fs=7, bold=True)
arrow(ax, 93.5, 22, 92, 13, color=BLUE)
ax.text(68, 32.5, "끼우는 기준 넷 — 위반 · 어미 틀림 · 지연 · 비용이\nNova Lite 와 같거나 나아야 한다", fontsize=6.2, color=BLUE)
save(fig, "f_seshat", ["external:seshat PLAN #1–#11 · 비공개 저장소라 이 저장소에서 대조하지 못한다", "file:docs/PLAN.md~| 59 |"])

# ── 배포 ───────────────────────────────────────────────
fig, ax = canvas(7.4, 3.6, 100, 48)
flow = [("git tag v*", LGRAY, GRAY), ("deploy.yml\nubuntu-24.04", LBLUE, BLUE), ("production\n승인 · v* 만", LRED, RED), ("OIDC\nenv:production", LBLUE, BLUE), ("terraform\napply", LBLUE, BLUE), ("deploy_drift\n배포본 대조", LBLUE, BLUE)]
for i, (t, fc, ec) in enumerate(flow):
    x = 1 + i * 16.5
    box(ax, x, 34, 14, 9, t, fc=fc, ec=ec, fs=7.2)
    if i: arrow(ax, x - 2.5, 38.5, x, 38.5)
group(ax, 50, 3, 49, 26, "AWS · ap-northeast-2", GRAY, ls="-")
for i, t in enumerate(["Lambda py3.13\nzip · 의존성 0", "Function URL\nNONE + 토큰", "DynamoDB\n온디맨드", "Firehose · S3\nGlue · Athena", "S3 상태 버킷\ntf backend", "Budgets\nthoth-5usd"]):
    box(ax, 52 + (i % 3) * 15.5, 16 - (i // 3) * 11, 14, 8.5, t, fc=LGRAY, ec=GRAY, fs=6.6)
arrow(ax, 74, 34, 74, 25.5, color=BLUE)
box(ax, 1, 16, 46, 13, "손으로 하는 것 — IAM 변경 · 콜드패스 첫 apply\n배포 역할에 IAM 쓰기가 없다\n순서: 손 plan -out /tmp → 손 apply → 태그\nplan 파일에 변수 평문 — 저장소 밖(§115)", fc=LAMBER, ec=AMBER, fs=6.4)
box(ax, 1, 3, 46, 10, "proposal.yml — docx_check 통과 뒤 Pages\ncleveraifox.github.io/thoth/proposal.html", fc=LGREEN, ec=GREEN, fs=6.4)
save(fig, "f_deploy", ["file:.github/workflows/deploy.yml~runs-on: ubuntu-24.04", "file:infra/compute.tf~python3.13", "file:docs/MASTER.md~thoth-5usd"])

# ── 문서 체계 ──────────────────────────────────────────
fig, ax = canvas(7.4, 3.6, 100, 48)
for i, (n, t, c) in enumerate([("PLAN", "미래 · §1 표 하나\n영구 행 번호", AMBER), ("MASTER", "현재 · 계약 · 운영\n정본", BLUE), ("DECISIONS", "과거 · append-only\n강제자 · 배운 것", GRAY), ("proposal.docx", "밖에 내는 제출본\n숫자는 산출물이 정본", GREEN)]):
    box(ax, 2 + i * 24.5, 32, 21, 12, f"{n}\n{t}", fc="white", ec=c, fs=7.4, bold=False)
arrow(ax, 23, 38, 26.5, 38, "닫히면\n결과", color=GRAY, off=(0, 4.6))
arrow(ax, 47.5, 38, 51, 38, "왜", color=GRAY, off=(0, 3.4))
for i, (n, t) in enumerate([("check_docs.py", "문체 · 절 · PLAN 표\n참조 · DECISIONS"), ("doc_fsck.py", "경로 · 테스트\n죽은 도구"), ("check_counts.py", "문서의 수 ↔ 실측"), ("docx_check.py", "PRESENT · RETIRED")]):
    box(ax, 2 + i * 24.5, 12, 21, 11, f"{n}\n{t}", fc=LGRAY, ec=NAVY, fs=7)
    arrow(ax, 12.5 + i * 24.5, 23, 12.5 + i * 24.5, 32, color=NAVY)
ax.text(2, 5, "모든 정규식 검사는 카나리아를 든다 — 합성 문자열에서 못 찾으면 2 로 끝난다. 위반은 1 · 고장은 2 · doctor 가 넷을 부른다.", fontsize=7.4, color=NAVY)
ax.text(2, 1, "seshat 은 check_docs · doc_fsck 를 사본으로 쓰고(머리에 「사본이다」) check_model_licenses 를 더한다.", fontsize=7.4, color=GREEN)
save(fig, "f_docs", ["none"])

# ── 서비스 구성도 ──────────────────────────────────────
fig, ax = canvas(7.4, 3.5, 100, 47)
box(ax, 38, 38, 24, 7, "thoth + seshat", fc=NAVY, ec=NAVY, tc="white", bold=True, fs=9)
cols = [("1. 확장", ["1.1 이 사이트에서 켜기", "1.2 문항·보기·해설", "1.3 번역 표시 Alt+K", "1.4 연결 확인 · 설정"], BLUE, LBLUE),
        ("2. 워커", ["2.1 POST /translate", "2.2 GET /health", "2.3 캐시 · 상한 · 토큰", "2.4 부분 응답"], BLUE, LBLUE),
        ("3. 운영", ["3.1 doctor · ship", "3.2 태그 배포 · 승인", "3.3 쌍 로그 확인", "3.4 기획서 Pages"], NAVY, LGRAY),
        ("4. seshat", ["4.1 계약 서버", "4.2 평가 · 기준선", "4.3 쌍 추출 · 튜닝", "4.4 라이선스 대장"], GREEN, LGREEN)]
for i, (h, items, ec, fc) in enumerate(cols):
    x = 2 + i * 24.5
    box(ax, x, 27, 21, 6, h, fc=fc, ec=ec, bold=True, fs=8)
    ax.plot([50, x + 10.5], [38, 33], color=GRAY, lw=0.8)
    for j, t in enumerate(items):
        box(ax, x + 1.5, 20 - j * 5.6, 19.5, 4.6, t, fc="white", ec=ec, fs=6.8, ha="left")
    ax.plot([x + 0.8, x + 0.8], [27, 20 - 3 * 5.6 + 2.3], color=ec, lw=0.8)
save(fig, "f_menu", ["none"])

# ── 차별성 개념도 ──────────────────────────────────────
fig, ax = canvas(7.4, 3.1, 100, 42)
group(ax, 1, 2, 47, 38, "흔한 방식 — 스크래핑 · 전량 번역", GRAY, ls="-")
for i, t in enumerate(["사이트 긁기 (봇 · ToS)", "문항 전량 번역 · 사전 배포", "원문 사전이 배포물", "재실행마다 재과금"]):
    box(ax, 5, 30 - i * 7.5, 39, 5.5, t, fc=LGRAY, ec=GRAY, fs=7.5)
group(ax, 52, 2, 47, 38, "thoth + seshat", BLUE, ls="-")
for i, (t, c, f) in enumerate([("사용자 화면의 DOM 만 읽는다", BLUE, LBLUE), ("본 것만 · 한 번만 (sha256 캐시)", BLUE, LBLUE), ("배포물 없음 · 쌍은 학습 전용", AMBER, LAMBER), ("엔진은 한 줄로 교체 → 자체 모델", GREEN, LGREEN)]):
    box(ax, 56, 30 - i * 7.5, 39, 5.5, t, fc=f, ec=c, fs=7.5)
save(fig, "f_concept", ["none"])
print("ok")
