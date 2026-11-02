"""Draw the README's results chart from the recorded runs.

    python scripts/make_figures.py        # writes media/results.svg

Left: top-1 accuracy on the held-out test outages with the investigation started
at the fault time, for hosted Spark's agent (all sources a suite has), N-Sigma
(the best published method re-run here) and the no-AI control. Right: hosted
Spark end to end on RE3, with our detector choosing where to look, watching
metrics only (eval-spec-v1) and metrics plus error logs (eval-spec-v1.4).
Values come from the latest clean run per ranker in runs/explain_summary.jsonl,
the same rule the console's Evidence page uses. The SVG follows the viewer's
light or dark theme.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SUITES = ("RE1", "RE2", "RE3")
EPICENTER = {"RE1": "spark-agent", "RE2": "spark-agent-all", "RE3": "spark-agent-all"}   # RE1 has metrics only
SERIES = [("epicenter", "Epicenter: hosted Muse Spark agent"), ("nsigma", "N-Sigma, best published method"),
          ("no-ai", "No-AI control: rank by deviation")]


def latest() -> dict:
    """(suite, ranker, anchor) -> AC@1 from the latest clean test run."""
    out = {}
    for line in open(ROOT / "runs" / "explain_summary.jsonl"):
        r = json.loads(line)
        if r["part"] == "test" and not r["git_dirty"]:
            out[(r["suite"], r["ranker"], r["anchor"])] = r["summary"]["ac1"]   # later runs replace earlier ones
    return out


def svg(acc: dict, e2e: dict) -> str:
    W, H = 900, 392
    css = """
  .t1 { fill: #0b0b0b; } .t2 { fill: #52514e; } .grid { stroke: #e4e3df; } .axis { stroke: #b9b7b0; }
  .s1 { fill: #2a78d6; } .s2 { fill: #eb6834; } .s3 { fill: #1baf7a; }
  @media (prefers-color-scheme: dark) {
    .t1 { fill: #f0efec; } .t2 { fill: #c3c2b7; } .grid { stroke: #30363d; } .axis { stroke: #57606a; }
    .s1 { fill: #3987e5; } .s2 { fill: #d95926; } .s3 { fill: #199e70; }
  }
  text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }
  .title { font-size: 15px; font-weight: 600; } .sub { font-size: 12px; } .lab { font-size: 13px; }
  .val { font-size: 11.5px; font-variant-numeric: tabular-nums; } .leg { font-size: 12.5px; }"""
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
             'aria-label="Top-1 accuracy on held-out outages: Epicenter 0.95 to 0.98 against N-Sigma 0.67 to 0.78; '
             f'end to end on RE3, 0.35 with metrics only and 0.62 with error logs"><style>{css}</style>']

    def bar(x, y0, h, w, cls):
        """A bar with 4 px rounded data end, anchored square on the baseline."""
        r = min(4, w / 2, h)
        return (f'<path class="{cls}" d="M{x},{y0} V{y0 - h + r} Q{x},{y0 - h} {x + r},{y0 - h} H{x + w - r} '
                f'Q{x + w},{y0 - h} {x + w},{y0 - h + r} V{y0} Z"/>')

    # left panel: grouped bars per suite
    L, B, T, PW = 64, 318, 92, 520
    parts.append(f'<text class="t1 title" x="{L - 44}" y="28">Top-1 accuracy on 468 held-out benchmark outages</text>')
    parts.append(f'<text class="t2 sub" x="{L - 44}" y="47">Investigation starts at the fault time, as RCAEval gives it to every method</text>')
    for v in (0, 0.25, 0.5, 0.75, 1.0):
        y = B - v * (B - T)
        parts.append(f'<line class="{"axis" if v == 0 else "grid"}" x1="{L}" x2="{L + PW}" y1="{y:.1f}" y2="{y:.1f}" stroke-width="1"/>')
        parts.append(f'<text class="t2 val" x="{L - 8}" y="{y + 4:.1f}" text-anchor="end">{v:.2f}</text>')
    group, bw, gap = PW / 3, 38, 2
    for i, suite in enumerate(SUITES):
        cx = L + group * i + group / 2
        x0 = cx - (3 * bw + 2 * gap) / 2
        for j, (key, _) in enumerate(SERIES):
            v = acc[(suite, key)]
            x, h = x0 + j * (bw + gap), v * (B - T)
            parts.append(bar(round(x, 1), B, round(h, 1), bw, f"s{j + 1}"))
            parts.append(f'<text class="{"t1" if j == 0 else "t2"} val" x="{x + bw / 2:.1f}" y="{B - h - 6:.1f}" '
                         f'text-anchor="middle"{" font-weight=\"600\"" if j == 0 else ""}>{v:.2f}</text>')
        parts.append(f'<text class="t1 lab" x="{cx:.1f}" y="{B + 22}" text-anchor="middle">{suite}</text>')
    # legend, one row above the plot
    lx = L
    for j, (_, name) in enumerate(SERIES):
        parts.append(f'<rect class="s{j + 1}" x="{lx}" y="62" width="12" height="12" rx="3"/>')
        parts.append(f'<text class="t1 leg" x="{lx + 18}" y="72.5">{name}</text>')
        lx += 18 + len(name) * 6.6 + 22

    # right panel: RE3 end to end, before and after the error-log signal
    RX, RW = 660, 200   # same vertical scale as the left panel, so bar heights compare across both
    parts.append(f'<text class="t1 lab" x="{RX}" y="28" font-weight="600">RE3 code faults, end to end</text>')
    parts.append(f'<text class="t2 sub" x="{RX}" y="47">Our own detector picks where to look</text>')
    for v in (0, 0.25, 0.5, 0.75, 1.0):
        y = B - v * (B - T)
        parts.append(f'<line class="{"axis" if v == 0 else "grid"}" x1="{RX}" x2="{RX + RW}" y1="{y:.1f}" y2="{y:.1f}" stroke-width="1"/>')
    for k, (key, label) in enumerate((("v1", "metrics only"), ("v1.4", "+ error logs"))):
        v, w = e2e[key], 56
        x, h = RX + 30 + k * (w + 44), e2e[key] * (B - T)
        parts.append(bar(x, B, round(h, 1), w, "s1"))
        parts.append(f'<text class="t1 val" x="{x + w / 2}" y="{B - h - 6:.1f}" text-anchor="middle" font-weight="600">{v:.2f}</text>')
        parts.append(f'<text class="t1 lab" x="{x + w / 2}" y="{B + 22}" text-anchor="middle">{label}</text>')
    parts.append(f'<text class="t2 sub" x="{RX}" y="{B + 46}">23 outages gained, 1 lost</text>')
    parts.append(f'<text class="t2 sub" x="{RX}" y="{B + 62}">(exact McNemar, p = 3e-6)</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def main():
    runs = latest()
    acc = {}
    for s in SUITES:
        acc[(s, "epicenter")] = runs[(s, EPICENTER[s], "inject_time")]
        acc[(s, "nsigma")] = runs[(s, "nsigma", "inject_time")]
        acc[(s, "no-ai")] = runs[(s, "no-ai", "inject_time")]
    e2e = {"v1": runs[("RE3", "spark-agent-all", "detector")], "v1.4": runs[("RE3", "spark-agent-all", "detector+logs")]}
    out = ROOT / "media" / "results.svg"
    out.parent.mkdir(exist_ok=True)
    out.write_text(svg(acc, e2e))
    print("wrote", out.relative_to(ROOT), {f"{s}/{k}": round(v, 3) for (s, k), v in acc.items()}, {k: round(v, 3) for k, v in e2e.items()})


if __name__ == "__main__":
    main()
