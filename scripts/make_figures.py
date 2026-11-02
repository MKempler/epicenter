"""Draw the README's results chart from the recorded runs.

    python scripts/make_figures.py        # writes media/results.svg and media/glimmer.svg

Left: top-1 accuracy on the held-out test outages with the investigation started
at the fault time, for hosted Spark's agent (all sources a suite has), N-Sigma
(the best published method re-run here) and the no-AI control. Right: hosted
Spark end to end on RE3, with our detector choosing where to look, watching
metrics only (eval-spec-v1) and metrics plus error logs (eval-spec-v1.4).
A second chart compares the Glimmer 30B agent before and after fine-tuning:
top-1 per suite and the investigations that never submitted a ranking.
Values come from the latest clean run per ranker in runs/explain_summary.jsonl,
the same rule the console's Evidence page uses. The SVGs follow the viewer's
light or dark theme, and use no orange, which the console keeps for faults,
alarms and actions.
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


CSS = """
  .t1 { fill: #0b0b0b; } .t2 { fill: #52514e; } .grid { stroke: #e4e3df; } .axis { stroke: #b9b7b0; }
  .s1 { fill: #2a78d6; } .s2 { fill: #1baf7a; } .s3 { fill: #6250d6; }
  @media (prefers-color-scheme: dark) {
    .t1 { fill: #f0efec; } .t2 { fill: #c3c2b7; } .grid { stroke: #30363d; } .axis { stroke: #57606a; }
    .s1 { fill: #3987e5; } .s2 { fill: #199e70; } .s3 { fill: #9085e9; }
  }
  text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }
  .title { font-size: 15px; font-weight: 600; } .sub { font-size: 12px; } .lab { font-size: 13px; }
  .val { font-size: 11.5px; font-variant-numeric: tabular-nums; } .leg { font-size: 12.5px; }"""


def bar(x, y0, h, w, cls):
    """A bar with 4 px rounded data end, anchored square on the baseline."""
    r = min(4, w / 2, h)
    return (f'<path class="{cls}" d="M{x},{y0} V{y0 - h + r} Q{x},{y0 - h} {x + r},{y0 - h} H{x + w - r} '
            f'Q{x + w},{y0 - h} {x + w},{y0 - h + r} V{y0} Z"/>')


def svg(acc: dict, e2e: dict) -> str:
    W, H, css = 900, 392, CSS
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
             'aria-label="Top-1 accuracy on held-out outages: Epicenter 0.951 to 0.975 against N-Sigma 0.667 to 0.778; '
             f'end to end on RE3, 0.346 with metrics only and 0.617 with error logs"><style>{css}</style>']

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
                         f'text-anchor="middle"{" font-weight=\"600\"" if j == 0 else ""}>{v:.3f}</text>')
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
        parts.append(f'<text class="t1 val" x="{x + w / 2}" y="{B - h - 6:.1f}" text-anchor="middle" font-weight="600">{v:.3f}</text>')
        parts.append(f'<text class="t1 lab" x="{x + w / 2}" y="{B + 22}" text-anchor="middle">{label}</text>')
    parts.append(f'<text class="t2 sub" x="{RX}" y="{B + 46}">23 outages gained, 1 lost</text>')
    parts.append(f'<text class="t2 sub" x="{RX}" y="{B + 62}">(exact McNemar, p = 3e-6)</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def glimmer_svg(base: dict, tuned: dict, failed: dict) -> str:
    """Top-1 per suite, base vs fine-tuned Glimmer, and how many investigations failed to submit a ranking."""
    W, H, L, B, T, PW = 640, 330, 64, 262, 70, 520
    series = [("base", "Glimmer 30B, base", "s2"), ("tuned", "Glimmer 30B, fine-tuned on Spark's verified investigations", "s1")]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
             'aria-label="Top-1 accuracy of the Glimmer 30B agent on the held-out outages: base 0.653, 0.586 and 0.580 on RE1, RE2 and RE3; '
             f'fine-tuned 0.911, 0.944 and 0.815. Investigations that failed to submit a ranking: {failed["base"]} of 468 base, '
             f'{failed["tuned"]} of 468 fine-tuned."><style>{CSS}</style>']
    parts.append(f'<text class="t1 title" x="{L - 44}" y="24">Glimmer 30B agent, top-1 on the held-out outages</text>')
    lx = L
    for _, name, cls in series:
        parts.append(f'<rect class="{cls}" x="{lx}" y="40" width="12" height="12" rx="3"/>')
        parts.append(f'<text class="t1 leg" x="{lx + 18}" y="50.5">{name}</text>')
        lx += 18 + len(name) * 6.6 + 22
    for v in (0, 0.25, 0.5, 0.75, 1.0):
        y = B - v * (B - T)
        parts.append(f'<line class="{"axis" if v == 0 else "grid"}" x1="{L}" x2="{L + PW}" y1="{y:.1f}" y2="{y:.1f}" stroke-width="1"/>')
        parts.append(f'<text class="t2 val" x="{L - 8}" y="{y + 4:.1f}" text-anchor="end">{v:.2f}</text>')
    group, bw, gap = PW / 3, 44, 2
    for i, suite in enumerate(SUITES):
        cx = L + group * i + group / 2
        x0 = cx - (2 * bw + gap) / 2
        for j, (key, _, cls) in enumerate(series):
            v = (base, tuned)[j][suite]
            x, h = x0 + j * (bw + gap), v * (B - T)
            parts.append(bar(round(x, 1), B, round(h, 1), bw, cls))
            parts.append(f'<text class="{"t1" if key == "tuned" else "t2"} val" x="{x + bw / 2:.1f}" y="{B - h - 6:.1f}" '
                         f'text-anchor="middle"{" font-weight=\"600\"" if key == "tuned" else ""}>{v:.3f}</text>')
        parts.append(f'<text class="t1 lab" x="{cx:.1f}" y="{B + 22}" text-anchor="middle">{suite}</text>')
    parts.append(f'<text class="t2 sub" x="{L - 44}" y="{B + 50}">Investigations that never submitted a ranking: '
                 f'{failed["base"]} of 468 before fine-tuning, {failed["tuned"]} of 468 after.</text>')
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
    summaries = {}
    for line in open(ROOT / "runs" / "explain_summary.jsonl"):
        r = json.loads(line)
        if r["part"] == "test" and not r["git_dirty"] and r["anchor"] == "inject_time":
            summaries[(r["suite"], r["ranker"])] = r["summary"]
    base = {s: summaries[(s, "glimmer-agent-all")]["ac1"] for s in SUITES}
    tuned = {s: summaries[(s, "glimmer-tuned-agent-all")]["ac1"] for s in SUITES}
    failed = {"base": sum(summaries[(s, "glimmer-agent-all")]["failed"] for s in SUITES),
              "tuned": sum(summaries[(s, "glimmer-tuned-agent-all")]["failed"] for s in SUITES)}
    (ROOT / "media" / "glimmer.svg").write_text(glimmer_svg(base, tuned, failed))
    print("glimmer", {s: (round(base[s], 3), round(tuned[s], 3)) for s in SUITES}, failed)
    print("wrote", out.relative_to(ROOT), {f"{s}/{k}": round(v, 3) for (s, k), v in acc.items()}, {k: round(v, 3) for k, v in e2e.items()})


if __name__ == "__main__":
    main()
