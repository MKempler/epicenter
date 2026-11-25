"""Build the console as a static site: replay and evidence, no server.

    python scripts/build_static.py              # writes site/
    python -m http.server -d site 8000          # http://127.0.0.1:8000

Every JSON response the replay and evidence views read is written to a file
under site/api/, using the API's own handlers on the committed records under
runs/, so the static site shows exactly what the server would. The console
is marked static, which hides the live lab and the user study (both need a
server) and makes it read those files instead of calling /api/.

The benchmark's answer is never inside a replay bundle: it sits in a
separate <case>.answer.json that the console fetches only on Reveal.
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ANCHORS = {"": "inject", "detector": "detector", "detector+logs": "detector-logs"}
STATIC_MARK = '<meta name="epicenter-static" content="1">'


def write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, separators=(",", ":"), default=str))


def build(out: Path) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{Path(tmp) / 'static.db'}"
        from src import api
        from src.db import setup
        api.app.state.engine = setup()

        if out.exists():
            shutil.rmtree(out)
        api_dir = out / "api"
        counts = {"results": 0, "replays": 0}
        for suite in api.SUITES:
            for anchor, name in ANCHORS.items():
                write(api_dir / "results" / f"{suite}-{name}.json",
                      api.results(suite=suite, anchor=anchor or "inject", part="test"))
                counts["results"] += 1
            write(api_dir / "replays" / suite / "index.json", api.replay_index(suite=suite))
            for entry in api.replay_index(suite=suite)["cases"]:
                case_id = entry["case_id"]
                write(api_dir / "replays" / suite / f"{case_id}.json", api.replay(suite, case_id, reveal=False))
                full = api.replay(suite, case_id, reveal=True)
                write(api_dir / "replays" / suite / f"{case_id}.answer.json",
                      {k: full[k] for k in api.HIDDEN_UNTIL_REVEAL if k in full})
                counts["replays"] += 1
        write(api_dir / "detection.json", api.detection())
        write(api_dir / "trust.json", api.trust())

    html = (ROOT / "static" / "console.html").read_text()
    if "<head>" not in html:
        raise SystemExit("console.html has no <head> to mark as static")
    (out / "index.html").write_text(html.replace("<head>", f"<head>\n{STATIC_MARK}", 1))
    (out / ".nojekyll").write_text("")      # GitHub Pages: serve files as they are
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=ROOT / "site")
    parser.add_argument("--cname", help="custom domain for GitHub Pages, e.g. epicenter.watch")
    args = parser.parse_args()
    counts = build(args.out)
    if args.cname:
        (args.out / "CNAME").write_text(args.cname + "\n")
    print(f"wrote {args.out}: {counts['replays']} replays, {counts['results']} result tables")


if __name__ == "__main__":
    main()
