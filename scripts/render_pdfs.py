"""Render all VELDO documents to PDF, driven by docs/manifest.yaml.

For each document in the manifest: parse its version line, render it to
pdf/<name>.pdf with a footer showing "<Title> vX.Y", "by <author>", and
"Page N of M" on every page. Then generate the document map
(VELDO_Documents.pdf) from the same manifest, so the map cannot drift.

Usage: python3 scripts/render_pdfs.py
Requires: google-chrome, python3-markdown, python3-websockets, python3-yaml.
"""
import asyncio, base64, datetime, json, re, subprocess, tempfile, time
from pathlib import Path

import markdown
import websockets
import yaml

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
PDF = ROOT / "pdf"

CSS = """
* { box-sizing: border-box; }
body { font-family: 'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif;
       font-size: 10.5pt; line-height: 1.55; color: #1a1a1a; margin: 0; }
h1 { font-size: 21pt; margin: 0 0 4pt 0; }
h2 { font-size: 15pt; margin-top: 22pt; padding-bottom: 4pt;
     border-bottom: 1.5px solid #d0d0d0; page-break-after: avoid; }
h3 { font-size: 12pt; margin-top: 16pt; page-break-after: avoid; }
h4 { font-size: 10.5pt; margin-top: 12pt; page-break-after: avoid; }
p, li { orphans: 3; widows: 3; }
code { font-family: 'DejaVu Sans Mono', 'Consolas', monospace; font-size: 8.8pt;
       background: #f2f3f5; padding: 1px 4px; border-radius: 3px; }
pre { background: #f6f8fa; border: 1px solid #e1e4e8; border-radius: 6px;
      padding: 10px 12px; overflow-x: hidden; white-space: pre-wrap;
      word-wrap: break-word; page-break-inside: avoid; }
pre code { background: none; padding: 0; font-size: 8.3pt; line-height: 1.45; }
blockquote { margin: 10px 0; padding: 8px 14px; border-left: 4px solid #4a6fa5;
             background: #f4f7fb; color: #222; page-break-inside: avoid; }
blockquote p { margin: 0; }
table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 9pt;
        page-break-inside: avoid; }
th, td { border: 1px solid #ccc; padding: 5px 8px; text-align: left; vertical-align: top; }
th { background: #eef1f5; font-weight: 600; }
tr:nth-child(even) td { background: #fafbfc; }
ul, ol { padding-left: 22px; }
li { margin: 2px 0; }
hr { border: none; border-top: 1px solid #ddd; margin: 18px 0; }
strong { font-weight: 600; }
a { color: #2a5db0; text-decoration: none; }
"""

FOOTER = """
<div style="width:100%; font-size:8px; font-family:Helvetica,Arial,sans-serif; color:#777;
            padding:0 16mm; display:flex; justify-content:space-between; align-items:center;">
  <span>{left}</span>
  <span>by {author}</span>
  <span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
</div>
"""

VERSION_RE = re.compile(r"^\*Version ([0-9][0-9.]*), (\d{4}-\d{2}-\d{2})\*$", re.M)


def parse_version(md_text, name):
    m = VERSION_RE.search(md_text)
    if not m:
        raise SystemExit(f"{name}: no version line ('*Version X.Y, YYYY-MM-DD*') found")
    return m.group(1), m.group(2)


def to_html(md_text, title):
    body = markdown.markdown(md_text, extensions=["tables", "fenced_code", "sane_lists"])
    return (f'<!DOCTYPE html><html><head><meta charset="utf-8">'
            f'<title>{title}</title><style>{CSS}</style></head><body>{body}</body></html>')


def build_map_md(manifest, versions, tversions=None):
    today = datetime.date.today().isoformat()
    lines = [
        "# VELDO Documents",
        "",
        f"*The map of the VELDO document set. Generated {today} from the document manifest; it cannot drift from what is actually published.*",
        "",
        "Read in reading order. Every PDF carries its document name and version in the footer of every page; the Document History section at the end of each document says what changed between versions.",
        "",
    ]
    docs = sorted(manifest["documents"], key=lambda d: d["reading_order"])
    lines += ["| # | Document | Version | PDF |", "|---|---|---|---|"]
    for d in docs:
        v, dt = versions[d["file"]]
        lines.append(f"| {d['reading_order']} | {d['title']} | v{v} ({dt}) | {d['pdf']} |")
    lines.append("")
    for d in docs:
        v, dt = versions[d["file"]]
        lines += [
            f"## {d['reading_order']}. {d['title']}",
            "",
            f"**Version:** {v} ({dt})",
            "",
            f"**Purpose:** {d['purpose'].strip()}",
            "",
            f"**Audience:** {d['audience'].strip()}",
            "",
            f"**Covers:** {d['covers'].strip()}",
            "",
        ]
    if tversions and manifest.get("training"):
        lines += ["## The training series", "",
                  "Role-based training in `pdf/training/`: who transforms, who dissolves, and how to upskill. Start with the guide.", "",
                  "| # | Document | Version | Audience | PDF |", "|---|---|---|---|---|"]
        for d in sorted(manifest["training"], key=lambda x: x["reading_order"]):
            v, dt = tversions[d["file"]]
            lines.append(f"| {d['reading_order']} | {d['title']} | v{v} | {d['audience']} | training/{d['pdf']} |")
        lines.append("")
    lines += [
        "## Source of truth",
        "",
        "These PDFs are generated renders. The documents themselves live as Markdown in the repository's `docs/` directory, which is the source of truth; the PDFs in `pdf/` are regenerated from it by `scripts/render_pdfs.py` whenever a document changes.",
    ]
    return "\n".join(lines)


async def print_pdf(ws, mid, html_path, pdf_path, footer_left, author):
    async def cmd(method, params=None, session=None):
        mid[0] += 1
        msg = {"id": mid[0], "method": method, "params": params or {}}
        if session:
            msg["sessionId"] = session
        await ws.send(json.dumps(msg))
        while True:
            resp = json.loads(await ws.recv())
            if resp.get("id") == mid[0]:
                if "error" in resp:
                    raise RuntimeError(f"{method}: {resp['error']}")
                return resp["result"]

    target = await cmd("Target.createTarget", {"url": "about:blank"})
    att = await cmd("Target.attachToTarget", {"targetId": target["targetId"], "flatten": True})
    sess = att["sessionId"]
    await cmd("Page.enable", session=sess)
    await cmd("Page.navigate", {"url": f"file://{html_path}"}, session=sess)
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            ev = json.loads(await asyncio.wait_for(ws.recv(), timeout=3))
            if ev.get("method") == "Page.loadEventFired" and ev.get("sessionId") == sess:
                break
        except asyncio.TimeoutError:
            break
    await asyncio.sleep(0.5)
    res = await cmd("Page.printToPDF", {
        "printBackground": True, "preferCSSPageSize": False,
        "paperWidth": 8.27, "paperHeight": 11.69,
        "marginTop": 0.65, "marginBottom": 0.8, "marginLeft": 0.63, "marginRight": 0.63,
        "displayHeaderFooter": True, "headerTemplate": "<span></span>",
        "footerTemplate": FOOTER.format(left=footer_left, author=author),
    }, session=sess)
    Path(pdf_path).write_bytes(base64.b64decode(res["data"]))
    await cmd("Target.closeTarget", {"targetId": target["targetId"]})


async def main():
    manifest = yaml.safe_load((DOCS / "manifest.yaml").read_text())
    author = manifest["author"]
    PDF.mkdir(exist_ok=True)

    versions = {}
    jobs = []  # (html_text, pdf_path, footer_left)
    for d in manifest["documents"]:
        md_text = (DOCS / d["file"]).read_text()
        v, dt = parse_version(md_text, d["file"])
        versions[d["file"]] = (v, dt)
        jobs.append((to_html(md_text, d["title"]), PDF / d["pdf"], f"{d['title']} v{v}"))

    tversions = {}
    for d in manifest.get("training", []):
        md_text = (DOCS / "training" / d["file"]).read_text()
        v, dt = parse_version(md_text, "training/" + d["file"])
        tversions[d["file"]] = (v, dt)
        (PDF / "training").mkdir(parents=True, exist_ok=True)
        jobs.append((to_html(md_text, d["title"]), PDF / "training" / d["pdf"],
                     f"{d['title']} v{v}"))

    map_md = build_map_md(manifest, versions, tversions)
    jobs.append((to_html(map_md, manifest["map"]["title"]),
                 PDF / manifest["map"]["pdf"],
                 f"{manifest['map']['title']} ({datetime.date.today().isoformat()})"))

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
        proc = subprocess.Popen(
            ["google-chrome", "--headless=new", "--disable-gpu",
             f"--user-data-dir={profile}", "--remote-debugging-port=0", "about:blank"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        ws_url = None
        deadline = time.time() + 20
        while time.time() < deadline:
            line = proc.stderr.readline()
            m = re.search(r"DevTools listening on (ws://\S+)", line or "")
            if m:
                ws_url = m.group(1)
                break
        if not ws_url:
            raise SystemExit("no DevTools endpoint")
        try:
            async with websockets.connect(ws_url, max_size=None) as ws:
                mid = [0]
                for html_text, pdf_path, footer_left in jobs:
                    html_file = Path(tempfile.mkstemp(suffix=".html", dir=profile)[1])
                    html_file.write_text(html_text)
                    await print_pdf(ws, mid, html_file, pdf_path, footer_left, author)
                    print(f"{pdf_path.name}: {pdf_path.stat().st_size} bytes [{footer_left}]")
        finally:
            proc.terminate()


asyncio.run(main())
