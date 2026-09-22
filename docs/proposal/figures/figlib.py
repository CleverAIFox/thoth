"""기획서 그림 공통 — 도형 · 화살표 · 색 · 사실 선언(DECISIONS §116).

★ **그림마다 그 안의 숫자가 어디서 왔는지 선언한다.** `save(fig, 이름, facts)` 가 PNG 옆에
  `이름.facts.json` 을 쓰고, 생성기가 그것을 그림의 대체 텍스트(`descr`)에 싣는다.
  `tools/docx_check.py` 가 그 선언을 산출물과 다시 대조한다 — 그림 속 숫자가 검사 안으로 들어온다.

사실의 문법(한 줄에 하나)
  json:<경로>#<점.경로>=<값>     JSON 값이 같다
  file:<경로>~<부분 문자열>       파일에 그 문자열이 있다
  len:<경로>=<N>                 JSON 최상위 항목 수
  decisions:<날짜>=§a–§b         DECISIONS 에서 그 날짜의 절 범위
  none                           도식이다. 그린 숫자가 없다
  external:<무엇>                이 저장소 밖(seshat 비공개)이라 대조하지 못한다
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/proposal/.build/fig"
OUT.mkdir(parents=True, exist_ok=True)

# ★ 기계마다 한글 글꼴이 다르다. 있는 것을 쓴다.
for f in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
          "/mnt/c/Windows/Fonts/malgun.ttf", "/mnt/c/Windows/Fonts/malgunbd.ttf"]:
    if Path(f).exists():
        fm.fontManager.addfont(f)
_have = {x.name for x in fm.fontManager.ttflist}
_font = next((n for n in ["Noto Sans CJK JP", "Noto Sans CJK KR", "Malgun Gothic", "NanumGothic"] if n in _have), None)
if _font is None:
    raise SystemExit("한글 글꼴이 없다 — fonts-noto-cjk 를 설치하거나 윈도우 글꼴을 마운트한다")
plt.rcParams["font.family"] = _font
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.size"] = 9

NAVY = "#1F3864"
BLUE = "#2F5597"      # thoth
LBLUE = "#D9E2F3"
GREEN = "#2E7D5B"     # seshat
LGREEN = "#DCEFE5"
RED = "#C00000"
LRED = "#F8DEDE"
GRAY = "#595959"
LGRAY = "#F2F2F2"
AMBER = "#B7791F"
LAMBER = "#FBEFD5"

BASELINE = "docs/bench/baseline.json"


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def decisions_ranges():
    """DECISIONS 의 날짜 줄 → {날짜: (첫 절, 끝 절)}. docx_check 와 같은 규칙으로 센다."""
    import re
    out, cur = {}, None
    for line in (ROOT / "docs/DECISIONS.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^## §(\d+)\.", line)
        if m:
            cur = int(m.group(1))
            continue
        m = re.match(r"^\*\*(\d{4}-\d{2}-\d{2})\*\*$", line)
        if m and cur is not None:
            a, b = out.get(m.group(1), (cur, cur))
            out[m.group(1)] = (min(a, cur), max(b, cur))
            cur = None
    return out


def canvas(w, h, xmax=100, ymax=None):
    ymax = ymax or xmax * h / w
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, xmax)
    ax.set_ylim(0, ymax)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text, fc=LBLUE, ec=BLUE, fs=8.5, bold=False, tc="black", ls="-", lw=1.1, r=1.2, ha="center"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                                fc=fc, ec=ec, lw=lw, ls=ls))
    tx = x + w / 2 if ha == "center" else x + 1.2
    ax.text(tx, y + h / 2, text, ha=ha, va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", color=tc, linespacing=1.35)


def group(ax, x, y, w, h, title, ec=BLUE, fc="none", fs=9, ls="--"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.5",
                                fc=fc, ec=ec, lw=1.2, ls=ls))
    ax.text(x + 1.2, y + h - 1.0, title, ha="left", va="top", fontsize=fs, fontweight="bold", color=ec,
            bbox=dict(fc="white", ec="none", pad=0.5))


def arrow(ax, x1, y1, x2, y2, text=None, color=GRAY, ls="-", fs=7.5, off=(0, 1.2), cs="arc3", lw=1.1, both=False):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="<|-|>" if both else "-|>",
                                 mutation_scale=10, color=color, lw=lw, ls=ls, connectionstyle=cs,
                                 shrinkA=1, shrinkB=1))
    if text:
        ax.text((x1 + x2) / 2 + off[0], (y1 + y2) / 2 + off[1], text, ha="center", va="center",
                fontsize=fs, color=color, bbox=dict(fc="white", ec="none", pad=0.6))


def save(fig, name, facts):
    if not facts:
        raise SystemExit(f"{name}: 사실 선언이 없다 — 숫자가 없는 도식이면 ['none'] 이다")
    fig.savefig(OUT / f"{name}.png", dpi=200, bbox_inches="tight", pad_inches=0.08, facecolor="white")
    plt.close(fig)
    (OUT / f"{name}.facts.json").write_text(json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")
