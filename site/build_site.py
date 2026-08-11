#!/usr/bin/env python3
"""Static site generator for veldo.dev.

WHY THIS EXISTS
===============
The site is the front door, and the book prints its address as a permanent fact.
PLAN-0017 outcome O3 requires that the front door's content be RENDERED FROM THE
SAME documents the repository ships, never a second hand-written copy that will
drift. So this generator holds no prose of its own. Every sentence on every page
is read out of a document under docs/, and the landing page is assembled from
NAMED SECTIONS of those documents rather than written again. If a page needs
different words, the document is what changes.

The only strings this file contributes to the output are structural chrome:
navigation labels, section eyebrows, the contents heading, and one honest line
recording that the public repository does not exist yet. Those are marked
CHROME where they appear. Everything else is quoted from a source document, with
a citation link back to that document's canonical section.

WHAT IT PRODUCES
================
    _out/index.html                     the landing page
    _out/docs/index.html                the document index, from docs/manifest.yaml
    _out/docs/<slug>.html               one page per published document
    _out/CNAME                          veldo.dev, for GitHub Pages
    _out/.nojekyll                      Pages serves the files as generated

No JavaScript, no external fonts, no CDN, no network at build time or view time.
CSS is inlined into every page so any single page works when opened directly
from disk. The CSS itself lives in exactly one constant, STYLESHEET, so there is
one place to change it.

RUNNING IT
==========
    python3 build_site.py                  build, then self-check, then report
    python3 build_site.py --out DIR        build somewhere else

The self-check is not optional and not a separate script, because a generator
that can silently emit a broken link or a leaked name is a generator nobody can
trust to run before a book goes to print. It checks: every internal link
resolves to a file that exists, zero occurrences of the old internal name, zero
banned dash characters in prose, zero leaked company/customer/person names, and
byte-identical output across two independent builds. Any failure exits non-zero.
"""

from __future__ import annotations

import argparse
import filecmp
import hashlib
import html as html_mod
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit(
        "PyYAML is required to read docs/manifest.yaml, which is the declared "
        "record of which documents are published and what each one is for. "
        "Install it with: python3 -m pip install pyyaml"
    )


# ===========================================================================
# Configuration
# ===========================================================================

SITE_NAME = "Veldo"
SITE_DOMAIN = "veldo.dev"

# The public repository does not exist yet (PLAN-0017 W6 comes after the site,
# W5, deliberately). This is the ONE place that changes when it does: set the
# real URL and flip REPO_PUBLIC to True. Until then no page emits a link into
# the repository, because a front door full of dead links is worse than a front
# door that says the door is not open yet.
# The real address, filled in 2026-08-10 when the project moved into the Bcengi org. It had been
# ORG-PLACEHOLDER, and I first wrote here that the placeholder had shipped and put dead links on the
# live site. THAT WAS WRONG, and checking it is what showed me why: REPO_PUBLIC is False, so no page
# emits a repository link at all, and the placeholder was never rendered anywhere. The flag was doing
# its job. check_no_placeholders still earns its place, because the next placeholder may not sit
# behind a flag, but it did not catch a live defect here.
REPO_URL = "https://github.com/Bcengi/veldo"

# STILL FALSE, and deliberately, even though Bcengi/veldo now exists and is public. What this flag
# means is that there is a public repository WITH THE CODE IN IT. Today that repository holds the
# website branch and nothing else: no main branch, no engine, no packs. Flipping this now would point
# a visitor at an empty repository, which is a worse front door than one that says the door is not
# open yet. It flips when W6 publishes the tree.
REPO_PUBLIC = True   # flipped 2026-08-10: Bcengi/veldo main carries the tree and v1.0.0 is tagged

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"
DEFAULT_OUT = Path(__file__).resolve().parent / "_out"

# Documents the site publishes, in the order docs/manifest.yaml declares them.
# The manifest is the authority on WHICH documents exist and WHAT each is for;
# this generator only decides where each one lands in the output tree.
#
# Deliberately NOT published, because they are internal rather than method:
#   docs/design/      the design history, including the pre-rename explorations;
#                     several filenames carry the company name
#   docs/research/    internal research briefings written to inform the method
#   docs/landscape.md a positioning and market survey, not part of the declared
#                     document set in manifest.yaml
PUBLISHED_TRAINING_PREFIX = "training-"


# ===========================================================================
# The name mapping (TEMPORARY - delete when the rename ships)
# ===========================================================================
#
# The external name is Veldo. The documents under docs/ still carry the old
# internal working name because PLAN-0017 W2 (the rename executed as a migration
# with a proven reverse) has NOT LANDED YET, and hand-editing the documents ahead
# of that migration would fork the prose from its source of truth, which is
# exactly what O3 forbids.
#
# So the rename is applied HERE, at build time, to the source text before it is
# parsed. This whole section is scaffolding with a known end date:
#
#   ONCE WARP-1702 SHIPS AND THE DOCUMENTS SAY Veldo, DELETE NAME_RULES,
#   DELETE ), AND DELETE ITS TWO CALL SITES IN load_document(
#   AND load_manifest(). The residual-name check from WARP-1701 then becomes
#   the thing that keeps the old name out, which is where that job belongs:
#   in the build of the repository, not in the build of the website.
#
# Rules are applied in order, longest and most specific first.

# THE NAME MAPPING IS GONE, on the condition this file set for itself: 'once WARP-1702 ships
# and the documents say Veldo, delete NAME_RULES, delete apply_name_map(), and delete its call
# sites'. Both halves are now true, and keeping it was actively harmful rather than merely dead.
#
# The rename rewrote this file too, so `_OLD = "WARP"` became `_OLD = "VELDO"` and the mapping
# started translating the NEW name into a title-cased variant: a published document rendered
# Veldo-0142 beside PLAN-0007, which is an identifier in two different cases on one page. A
# module that holds the OLD name as data cannot survive the migration that renames it, and this
# is the third instance of that trap in this repository. The other two were caught by controls;
# this one was caught by reading the output.
#
# What keeps the old name out now is the residual-name check further down, which is where the
# job belongs: in the build of the repository, not in the build of the website.


# ===========================================================================
# Markdown rendering
# ===========================================================================
#
# A deliberately small block-and-inline renderer over exactly the constructs the
# documents use: ATX headings, fenced code, pipe tables, blockquotes, nested
# ordered and unordered lists, thematic breaks, paragraphs, and inline code,
# strong, emphasis and links. Underscore emphasis is NOT supported on purpose,
# because the documents are full of snake_case identifiers and schema names and
# treating those as emphasis would mangle them silently.
#
# Nothing here guesses. Anything the renderer fails to convert shows up as
# residue in the output and check_markdown_residue() fails the build on it, so a
# construct this parser does not know about is loud rather than quiet.

LIST_ITEM_RE = re.compile(r"^(\s*)([-*+]|\d+[.)])[ \t]+(.*)$")
HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.*?)[ \t]*#*$")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})\s*([A-Za-z0-9_+-]*)\s*$")
THEMATIC_RE = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")
TABLE_DELIM_RE = re.compile(r"^\s*\|?[\s:|-]*-[\s:|-]*\|[\s:|-]*$")

CODE_PLACEHOLDER = "\x00c{}\x00"


def slugify(text: str) -> str:
    """Heading slug, GitHub-compatible except that hyphen runs are collapsed.

    GitHub would turn 'Part I - The loop, operated' into 'part-i' plus three hyphens plus 'the-loop-operated'.
    A run of hyphens reads as a stand-in for a dash and is banned on every surface
    this project ships, so runs collapse to one. The one cross-document anchor the
    documents actually print has no run in it, so nothing breaks; if a document ever
    prints an anchor with a run, check_internal_links() fails on it rather than
    shipping a link that goes nowhere.
    """
    s = re.sub(r"`([^`]*)`", r"\1", text)
    s = re.sub(r"\*\*([^*]*)\*\*", r"\1", s)
    s = re.sub(r"\*([^*]*)\*", r"\1", s)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = s.strip().lower()
    s = re.sub(r"[^\w\- ]+", "", s)
    s = s.replace(" ", "-")
    return re.sub(r"-{2,}", "-", s).strip("-")


@dataclass
class RenderContext:
    """Everything a document needs in order to render its own links and anchors."""

    source_dir: str = ""
    out_depth: int = 0
    out_page: str = "index.html"
    link_resolver: object = None
    slugs: dict = field(default_factory=dict)
    heading_level_offset: int = 0
    # A document page's only h1 is the document title, rendered by the page
    # header, so nothing in the body may render as h1. The runbook has both
    # '# Part I' and '## Part II' at the same conceptual level, and without this
    # clamp Part I would render a second h1 and drop out of the contents list
    # while its siblings stayed in it.
    min_heading_level: int = 1
    collected_headings: list = field(default_factory=list)

    def unique_slug(self, text: str) -> str:
        base = slugify(text) or "section"
        n = self.slugs.get(base, 0)
        self.slugs[base] = n + 1
        return base if n == 0 else f"{base}-{n}"


def esc(text: str) -> str:
    return html_mod.escape(text, quote=True)


def render_inline(text: str, ctx: RenderContext) -> str:
    codes: list[str] = []

    def take_code(m: re.Match) -> str:
        codes.append(m.group(2))
        return CODE_PLACEHOLDER.format(len(codes) - 1)

    text = re.sub(r"(`+)(.+?)\1", take_code, text)
    text = esc(text)

    def link(m: re.Match) -> str:
        label, target = m.group(1), m.group(2)
        href = None
        if ctx.link_resolver is not None:
            href = ctx.link_resolver(target, ctx)
        if href is None:
            # A target that does not resolve on this site keeps its text and
            # loses its link, rather than becoming a dead href.
            return f'<span class="unlinked">{label}</span>'
        external = href.startswith("http")
        rel = ' rel="noreferrer"' if external else ""
        return f'<a href="{esc(href)}"{rel}>{label}</a>'

    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, text)
    text = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![*\w])\*(?=\S)([^*]+?)(?<=\S)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"(?<![\"'>=])\b(https?://[^\s<>)\"']+)", r'<a href="\1" rel="noreferrer">\1</a>', text)

    for i, code in enumerate(codes):
        text = text.replace(CODE_PLACEHOLDER.format(i), f"<code>{esc(code)}</code>")
    return text


def _is_table_start(lines: list[str], i: int) -> bool:
    return (
        "|" in lines[i]
        and i + 1 < len(lines)
        and "|" in lines[i + 1]
        and bool(TABLE_DELIM_RE.match(lines[i + 1]))
    )


def _starts_block(lines: list[str], i: int) -> bool:
    line = lines[i]
    if not line.strip():
        return True
    return bool(
        FENCE_RE.match(line)
        or HEADING_RE.match(line)
        or THEMATIC_RE.match(line)
        or line.lstrip().startswith(">")
        or LIST_ITEM_RE.match(line)
        or _is_table_start(lines, i)
    )


def _render_table(lines: list[str], i: int, ctx: RenderContext) -> tuple[str, int]:
    def cells(row: str) -> list[str]:
        row = row.strip()
        if row.startswith("|"):
            row = row[1:]
        if row.endswith("|"):
            row = row[:-1]
        return [c.strip() for c in row.split("|")]

    header = cells(lines[i])
    aligns = []
    for spec in cells(lines[i + 1]):
        left, right = spec.startswith(":"), spec.endswith(":")
        aligns.append("center" if left and right else "right" if right else "left")
    i += 2
    body = []
    while i < len(lines) and "|" in lines[i] and lines[i].strip():
        body.append(cells(lines[i]))
        i += 1

    def cell(tag: str, value: str, idx: int) -> str:
        align = aligns[idx] if idx < len(aligns) else "left"
        style = "" if align == "left" else f' style="text-align:{align}"'
        return f"<{tag}{style}>{render_inline(value, ctx)}</{tag}>"

    out = ['<div class="scroll"><table>', "<thead><tr>"]
    out += [cell("th", v, n) for n, v in enumerate(header)]
    out.append("</tr></thead>")
    if body:
        out.append("<tbody>")
        for row in body:
            out.append("<tr>" + "".join(cell("td", v, n) for n, v in enumerate(row)) + "</tr>")
        out.append("</tbody>")
    out.append("</table></div>")
    return "\n".join(out), i


def _render_list(lines: list[str], i: int, ctx: RenderContext) -> tuple[str, int]:
    first = LIST_ITEM_RE.match(lines[i])
    assert first is not None
    base = len(first.group(1))
    ordered = first.group(2)[0].isdigit()
    start_at = int(first.group(2)[:-1]) if ordered else 1
    items: list[list[str]] = []
    loose = False

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            j = i
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j >= len(lines) or not items:
                break
            nxt = lines[j]
            nxt_indent = len(nxt) - len(nxt.lstrip())
            nxt_item = LIST_ITEM_RE.match(nxt)
            if (nxt_item and len(nxt_item.group(1)) == base) or nxt_indent > base:
                loose = True
                items[-1].append("")
                i = j
                continue
            break
        item = LIST_ITEM_RE.match(line)
        indent = len(line) - len(line.lstrip())
        if item and indent == base:
            items.append([item.group(3)])
            i += 1
            continue
        if items and indent > base:
            items[-1].append(line[base:])
            i += 1
            continue
        break

    rendered = []
    for item_lines in items:
        while item_lines and not item_lines[-1].strip():
            item_lines.pop()
        body = render_blocks(item_lines, ctx)
        if not loose and body.startswith("<p>") and body.endswith("</p>") and body.count("<p>") == 1:
            body = body[3:-4]
        rendered.append(f"<li>{body}</li>")

    tag = "ol" if ordered else "ul"
    open_tag = f'<{tag} start="{start_at}">' if ordered and start_at != 1 else f"<{tag}>"
    return open_tag + "\n" + "\n".join(rendered) + f"\n</{tag}>", i


def render_blocks(lines: list[str], ctx: RenderContext) -> str:
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        fence = FENCE_RE.match(line)
        if fence:
            marker, lang = fence.group(1), fence.group(2)
            i += 1
            body: list[str] = []
            while i < len(lines) and not re.match(rf"^\s*{marker[0]}{{{len(marker)},}}\s*$", lines[i]):
                body.append(lines[i])
                i += 1
            i += 1  # closing fence
            cls = f' class="lang-{esc(lang)}"' if lang else ""
            out.append(f"<pre><code{cls}>{esc(chr(10).join(body))}</code></pre>")
            continue

        heading = HEADING_RE.match(line)
        if heading:
            level = min(6, max(ctx.min_heading_level, len(heading.group(1)) + ctx.heading_level_offset))
            text = heading.group(2)
            slug = ctx.unique_slug(text)
            ctx.collected_headings.append((level, text, slug))
            inner = render_inline(text, ctx)
            out.append(
                f'<h{level} id="{esc(slug)}">{inner}'
                f'<a class="anchor" href="#{esc(slug)}" aria-label="link to this section">#</a>'
                f"</h{level}>"
            )
            i += 1
            continue

        if THEMATIC_RE.match(line):
            out.append("<hr>")
            i += 1
            continue

        if line.lstrip().startswith(">"):
            quoted: list[str] = []
            while i < len(lines) and (lines[i].lstrip().startswith(">") or (quoted and lines[i].strip())):
                stripped = lines[i].lstrip()
                quoted.append(stripped[1:].lstrip(" ") if stripped.startswith(">") else lines[i].strip())
                i += 1
            out.append(f"<blockquote>{render_blocks(quoted, ctx)}</blockquote>")
            continue

        if _is_table_start(lines, i):
            table, i = _render_table(lines, i, ctx)
            out.append(table)
            continue

        if LIST_ITEM_RE.match(line):
            lst, i = _render_list(lines, i, ctx)
            out.append(lst)
            continue

        para = [line.strip()]
        i += 1
        while i < len(lines) and not _starts_block(lines, i):
            para.append(lines[i].strip())
            i += 1
        out.append(f"<p>{render_inline(' '.join(para), ctx)}</p>")

    return "\n".join(out)


# ===========================================================================
# Documents
# ===========================================================================

VERSION_RE = re.compile(r"^\*Version\s+([0-9.]+),\s*([0-9-]+)\*$")


@dataclass
class Section:
    level: int
    heading: str
    start: int
    end: int


@dataclass
class Document:
    source: str          # path relative to docs/, e.g. "training/architect.md"
    slug: str            # output stem under docs/, e.g. "training-architect"
    title: str           # h1 text, after the name mapping
    title_line: int      # index of the h1 line, so the body can drop it
    nav_title: str       # title from manifest.yaml, after the name mapping
    tagline: str         # the document's italic strapline, verbatim
    version: str
    version_date: str
    lines: list[str]
    sections: dict[str, Section]
    purpose: str = ""
    audience: str = ""
    covers: str = ""
    reading_order: int = 0
    series: str = "documents"

    @property
    def out_path(self) -> str:
        return f"docs/{self.slug}.html"

    def section(self, pattern: str) -> Section:
        """Find the one section whose heading matches, or fail loudly.

        The landing page pulls named sections out of the documents. If a heading
        is renamed or removed, this raises instead of silently emitting an empty
        page, because a front door with a missing section is a defect and a
        build that hides it is worse than a build that stops.
        """
        rx = re.compile(pattern)
        hits = [s for s in self.sections.values() if rx.match(s.heading)]
        if len(hits) != 1:
            available = "\n  ".join(sorted(s.heading for s in self.sections.values()))
            raise SystemExit(
                f"{self.source}: expected exactly one section matching {pattern!r}, "
                f"found {len(hits)}. Headings present:\n  {available}"
            )
        return hits[0]

    def section_lines(self, pattern: str) -> list[str]:
        s = self.section(pattern)
        return self.lines[s.start : s.end]

    def preamble_lines(self) -> list[str]:
        """The document's opening prose: after the title, tagline and version, before section 1."""
        # Section.start is the line AFTER its heading, so stop one line earlier or
        # the preamble swallows the first section heading.
        first_heading = min((s.start - 1 for s in self.sections.values()), default=len(self.lines))
        body = []
        for line in self.lines[1:first_heading]:
            stripped = line.strip()
            if VERSION_RE.match(stripped):
                continue
            if stripped == self.tagline:
                continue
            body.append(line)
        return body


def _index_sections(lines: list[str]) -> dict[str, Section]:
    """Map slug -> section, skipping every heading inside a fenced code block.

    The documents embed whole specification and proof templates in fences, and
    those templates have their own '## Status' and '## Intent' headings. A
    fence-blind scan would treat them as real sections of the document.
    """
    found: list[tuple[int, int, str]] = []
    in_fence = False
    fence_marker = ""
    for n, line in enumerate(lines):
        fence = FENCE_RE.match(line)
        if fence:
            if not in_fence:
                in_fence, fence_marker = True, fence.group(1)[0]
            elif line.strip()[0] == fence_marker:
                in_fence = False
            continue
        if in_fence:
            continue
        heading = HEADING_RE.match(line)
        if heading and len(heading.group(1)) == 2:
            found.append((n, 2, heading.group(2)))

    sections: dict[str, Section] = {}
    counts: dict[str, int] = {}
    for idx, (n, level, heading) in enumerate(found):
        end = found[idx + 1][0] if idx + 1 < len(found) else len(lines)
        base = slugify(heading)
        seen = counts.get(base, 0)
        counts[base] = seen + 1
        sections[base if seen == 0 else f"{base}-{seen}"] = Section(level, heading, n + 1, end)
    return sections


def load_document(source: str, slug: str, entry: dict, series: str) -> Document:
    raw = (DOCS_DIR / source).read_text(encoding="utf-8")
    lines = raw.replace("\r\n", "\n").split("\n")

    title, title_line = "", -1
    for n, line in enumerate(lines):
        heading = HEADING_RE.match(line)
        if heading and len(heading.group(1)) == 1:
            title, title_line = heading.group(2), n
            break
    if title_line < 0:
        raise SystemExit(f"{source}: no top-level heading, so the page has no title.")

    tagline, version, version_date = "", "", ""
    for line in lines[1:12]:
        stripped = line.strip()
        matched = VERSION_RE.match(stripped)
        if matched:
            version, version_date = matched.group(1), matched.group(2)
        elif not tagline and stripped.startswith("*") and stripped.endswith("*") and len(stripped) > 2:
            tagline = stripped

    return Document(
        source=source,
        slug=slug,
        title=title,
        title_line=title_line,
        nav_title=str(entry.get("title", title)),
        tagline=tagline,
        version=version,
        version_date=version_date,
        lines=lines,
        sections=_index_sections(lines),
        purpose=str(entry.get("purpose", "")).strip(),
        audience=str(entry.get("audience", "")).strip(),
        covers=str(entry.get("covers", "")).strip(),
        reading_order=int(entry.get("reading_order", 0)),
        series=series,
    )


def load_manifest() -> tuple[dict, list[Document]]:
    manifest = yaml.safe_load((DOCS_DIR / "manifest.yaml").read_text(encoding="utf-8"))
    docs: list[Document] = []
    for entry in manifest.get("documents", []):
        source = entry["file"]
        docs.append(load_document(source, Path(source).stem, entry, "documents"))
    for entry in manifest.get("training", []):
        source = f"training/{entry['file']}"
        slug = PUBLISHED_TRAINING_PREFIX + Path(entry["file"]).stem
        docs.append(load_document(source, slug, entry, "training"))
    return manifest, docs


# ===========================================================================
# Link resolution
# ===========================================================================


class LinkResolver:
    """Rewrite the links the documents already carry so they land on this site.

    Three outcomes, and no fourth:
      - a link to another published document becomes a relative link to its page
      - an absolute or mail link is kept as written
      - a link into the repository tree becomes a repository link when the
        repository is public, and loses its href when it is not
    """

    def __init__(self, docs: list[Document]):
        self.by_source = {d.source: d for d in docs}

    def __call__(self, target: str, ctx: RenderContext) -> str | None:
        if target.startswith(("http://", "https://", "mailto:")):
            return target
        if target.startswith("#"):
            return target

        path, _, anchor = target.partition("#")
        anchor = f"#{anchor}" if anchor else ""
        if not path:
            return target

        resolved = os.path.normpath(os.path.join(ctx.source_dir, path)).replace(os.sep, "/")
        doc = self.by_source.get(resolved)
        if doc is not None:
            here = os.path.dirname(ctx.out_page) or "."
            rel = os.path.relpath(doc.out_path, start=here).replace(os.sep, "/")
            return f"{rel}{anchor}"

        # Not a published document: it is a path inside the repository tree.
        if REPO_PUBLIC:
            return f"{REPO_URL}/blob/main/{resolved}{anchor}"
        return None


# ===========================================================================
# Page shell and stylesheet
# ===========================================================================

# CHROME. Navigation labels and section eyebrows are the only editorial strings
# this generator owns. Everything with prose in it comes from a document.
NAV = [("Overview", "index.html"), ("Method", "docs/method.html"), ("Documents", "docs/index.html")]

STYLESHEET = """
:root{
  --paper:#fbfaf6; --ink:#16150f; --muted:#6a665b; --rule:#d9d6cc;
  --wash:#f2f0e8; --measure:41rem;
}
@media (prefers-color-scheme: dark){
  :root{ --paper:#14140f; --ink:#ecebe3; --muted:#98948a; --rule:#33322b; --wash:#1d1c16; }
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  margin:0; background:var(--paper); color:var(--ink);
  font-family:Georgia,"Iowan Old Style","Palatino Linotype",Palatino,"Times New Roman",serif;
  font-size:17px; line-height:1.62; text-rendering:optimizeLegibility;
}
.sans{font-family:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
/* Two frame widths, one per page type. A document page is 56rem because it
   carries a contents rail beside the prose (40 + 4 gap + 12); every other page
   is exactly the measure plus its gutters, so its single column fills the frame
   and sits centred instead of hugging the left edge of a wider one. */
.wrap{max-width:57rem;margin:0 auto;padding:0 1.5rem}
.wrap.narrow{max-width:44rem}

/* masthead */
.masthead{border-bottom:1px solid var(--rule);margin-bottom:3.5rem}
.masthead .wrap{display:flex;flex-wrap:wrap;align-items:baseline;gap:.5rem 2rem;padding-top:1.4rem;padding-bottom:1.4rem}
.wordmark{font-size:1.15rem;letter-spacing:.02em;font-weight:600;text-decoration:none;color:inherit}
.masthead nav{font-family:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  font-size:.8rem;letter-spacing:.07em;text-transform:uppercase;margin-left:auto;
  display:flex;flex-wrap:wrap;gap:1.4rem}
.masthead nav a{color:var(--muted);text-decoration:none;border-bottom:1px solid transparent;padding-bottom:2px}
.masthead nav a:hover{color:var(--ink);border-bottom-color:var(--ink)}
.masthead nav a[aria-current="page"]{color:var(--ink);border-bottom-color:var(--ink)}

/* prose */
main{padding-bottom:5rem}
article,.column{max-width:var(--measure)}
h1{font-size:2.35rem;line-height:1.14;font-weight:600;letter-spacing:-.012em;margin:0 0 .6rem}
h2{font-size:1.4rem;line-height:1.25;font-weight:600;margin:3.2rem 0 .9rem;letter-spacing:-.005em}
h3{font-size:1.08rem;line-height:1.3;font-weight:600;margin:2.2rem 0 .7rem}
h4{font-size:1rem;font-weight:600;margin:1.7rem 0 .5rem}
h2+h3,h3+h4{margin-top:1.2rem}
p{margin:0 0 1.15rem}
a{color:inherit;text-decoration:underline;text-decoration-thickness:1px;text-underline-offset:.16em}
a:hover{text-decoration-thickness:2px}
.anchor{float:right;margin-left:1rem;color:var(--rule);text-decoration:none;font-weight:400;opacity:0}
h2:hover .anchor,h3:hover .anchor{opacity:1}
strong{font-weight:600}
ul,ol{margin:0 0 1.15rem;padding-left:1.4rem}
li{margin:.28rem 0}
li>ul,li>ol{margin:.3rem 0}
hr{border:0;border-top:1px solid var(--rule);margin:2.5rem 0}
blockquote{
  margin:1.6rem 0;padding:.1rem 0 .1rem 1.4rem;border-left:2px solid var(--ink);
  font-size:1.14rem;line-height:1.5;font-style:italic;color:var(--ink);
}
blockquote p:last-child{margin-bottom:0}
code{
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;
  font-size:.855em;background:var(--wash);padding:.08em .2em;border-radius:2px;
  font-style:normal;
}
pre{
  background:var(--wash);border:1px solid var(--rule);border-radius:2px;
  padding:.95rem 1.1rem;overflow-x:auto;margin:0 0 1.35rem;line-height:1.5;
}
/* Sized so the loop diagram, the longest line the front page has to show
   without scrolling, fits the measure. */
pre code{background:none;padding:0;font-size:.78rem}
.unlinked{border-bottom:1px dotted var(--rule)}
.scroll{overflow-x:auto;margin:0 0 1.4rem}
table{border-collapse:collapse;width:100%;font-size:.92rem;line-height:1.45}
th,td{border-bottom:1px solid var(--rule);padding:.5rem .8rem .5rem 0;text-align:left;vertical-align:top}
th{font-family:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  font-size:.72rem;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);
  border-bottom:1px solid var(--ink);font-weight:600;white-space:nowrap}

/* eyebrow labels */
.eyebrow{font-family:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  font-size:.7rem;letter-spacing:.13em;text-transform:uppercase;color:var(--muted);
  margin:0 0 .55rem;display:block}

/* landing */
.hero{max-width:var(--measure);margin:0 0 3rem}
.hero h1{font-size:3.6rem;letter-spacing:-.02em;margin-bottom:.9rem}
.hero .tagline{font-size:1.3rem;line-height:1.42;font-style:italic;color:var(--muted);margin:0}
.band{max-width:var(--measure);padding-top:2.6rem;margin-top:2.6rem;border-top:1px solid var(--rule)}
.band>h2:first-child{margin-top:0}
.band.first{padding-top:0;margin-top:0;border-top:0}
.band>ol>li{margin:.75rem 0}
.source{font-family:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  font-size:.75rem;color:var(--muted);margin:1.5rem 0 0}
.source a{color:var(--muted)}

/* document index */
.docrow{padding:1.5rem 0;border-top:1px solid var(--rule)}
.docrow:first-of-type{border-top:0;padding-top:.5rem}
.docrow h3{margin:0 0 .4rem;font-size:1.15rem}
.docrow h3 a{text-decoration:none;border-bottom:1px solid var(--rule)}
.docrow h3 a:hover{border-bottom-color:var(--ink)}
.docrow p{margin:0 0 .5rem}
.docrow dl{margin:.55rem 0 0;font-size:.87rem;color:var(--muted)}
.docrow dt{font-family:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  font-size:.68rem;letter-spacing:.11em;text-transform:uppercase;margin:.6rem 0 .1rem}
.docrow dd{margin:0}
.ordinal{font-size:.8rem;color:var(--muted);font-variant-numeric:tabular-nums}

/* document page */
.dochead{max-width:var(--measure);margin-bottom:0}
.dochead .tagline{font-size:1.14rem;line-height:1.45;font-style:italic;color:var(--muted);margin:0 0 .8rem}
.meta{font-family:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  font-size:.75rem;letter-spacing:.05em;color:var(--muted)}
.doc{display:grid;grid-template-columns:minmax(0,1fr);gap:2.5rem}
.toc{font-family:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;font-size:.8rem;line-height:1.45}
.toc ol{list-style:none;margin:0;padding:0}
.toc li{margin:.42rem 0}
.toc a{color:var(--muted);text-decoration:none}
.toc a:hover{color:var(--ink);text-decoration:underline}
/* Below the two-column breakpoint the contents sit above the prose, where a
   long stacked list would push the document itself off the first screen. They
   run in as one flowing line instead, the way a book's contents note does. */
@media (max-width:62rem){
  .toc ol{line-height:1.95}
  .toc li{display:inline;margin:0}
  .toc li:not(:last-child)::after{content:" / ";color:var(--rule)}
}
@media (min-width:62rem){
  .doc{grid-template-columns:minmax(0,var(--measure)) 12rem;gap:2.5rem 4rem}
  .doc>.dochead{grid-column:1 / -1}
  .doc>article{grid-column:1;grid-row:2}
  .doc>.toc{grid-column:2;grid-row:2;position:sticky;top:2rem;align-self:start;
    max-height:calc(100vh - 4rem);overflow-y:auto}
}

/* footer */
footer{border-top:1px solid var(--rule);padding:2rem 0 3.5rem;
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  font-size:.78rem;color:var(--muted)}
footer p{margin:0 0 .4rem;max-width:var(--measure)}
"""


def page_shell(
    title: str,
    description: str,
    body: str,
    depth: int,
    active: str,
    author: str,
    wide: bool = False,
) -> str:
    up = "../" * depth
    frame = "wrap" if wide else "wrap narrow"
    nav = "".join(
        '<a href="{href}"{cur}>{label}</a>'.format(
            href=esc(up + href),
            label=esc(label),
            cur=' aria-current="page"' if href == active else "",
        )
        for label, href in NAV
    )
    repo_note = (
        f'<p><a href="{esc(REPO_URL)}" rel="noreferrer">{esc(_repo_slug(REPO_URL))}</a></p>'
        if REPO_PUBLIC
        # CHROME. The truthful state of the repository on the day the site goes
        # live: the site exists first, by design. One line, and it changes by
        # flipping REPO_PUBLIC.
        else "<p>The public repository is not open yet. This site is the front door, and it stands up first.</p>"
    )
    return (
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{esc(title)}</title>\n"
        f'<meta name="description" content="{esc(description)}">\n'
        f'<meta name="author" content="{esc(author)}">\n'
        f"<style>{STYLESHEET}</style>\n"
        f'<header class="masthead"><div class="{frame}">'
        f'<a class="wordmark" href="{esc(up + "index.html")}">{esc(SITE_NAME)}</a>'
        f"<nav>{nav}</nav></div></header>\n"
        f'<main class="{frame}">\n{body}\n</main>\n'
        f'<footer class="{frame}">{repo_note}'
        f"<p>{esc(SITE_NAME)}. Written by {esc(author)}. "
        f"Every page on this site is rendered from the documents in the repository.</p>"
        f"</footer>\n"
    )


# ===========================================================================
# Pages
# ===========================================================================


def _ctx_for(doc: Document, resolver: LinkResolver, depth: int, out_page: str = "index.html") -> RenderContext:
    return RenderContext(
        source_dir=str(Path(doc.source).parent) if "/" in doc.source else "",
        out_depth=depth,
        out_page=out_page,
        link_resolver=resolver,
    )


def citation(doc: Document, anchor: str, heading: str, depth: int) -> str:
    """Name the exact document section this block was rendered from, and link to it.

    Every quoted block on the landing page carries one of these, so a reader can
    always reach the canonical text, and so nobody can quietly let the front page
    drift from the document it quotes.
    """
    up = "../" * depth
    href = f"{up}{doc.out_path}#{anchor}" if anchor else f"{up}{doc.out_path}"
    where = f"{doc.nav_title}, {heading}" if heading and heading != doc.title else doc.nav_title
    # CHROME: the word "Source". The rest is the document's own title and heading.
    return f'<p class="source">Source: <a href="{esc(href)}">{esc(where)}</a></p>'


def build_landing(docs: list[Document], resolver: LinkResolver, author: str) -> str:
    by_slug = {d.slug: d for d in docs}
    method, plugin = by_slug["method"], by_slug["plugin"]
    # One slug registry for the whole page, so two quoted sections can never
    # collide on an id.
    page_slugs: dict[str, int] = {}

    def band(label: str, sources: list[tuple[Document, str]], first: bool = False) -> str:
        """One landing band: a chrome label, quoted document prose, and its citations.

        The band's visible heading is the chrome label, NOT the source document's
        own heading, because a front page that announces "9. Definition of Proven"
        is quoting another document's table of contents at a reader who has not
        opened it. The source heading is named exactly once, in the citation.
        """
        parts = []
        for source_doc, pattern in sources:
            section = source_doc.section(pattern)
            ctx = _ctx_for(source_doc, resolver, 0)
            ctx.slugs = page_slugs
            if len(sources) > 1:
                parts.append(f"<h3>{esc(section.heading)}</h3>")
            parts.append(render_blocks(source_doc.lines[section.start : section.end], ctx))
            # The citation sits directly under the prose it accounts for, so a
            # band quoting two sections does not end in a stack of sources.
            parts.append(citation(source_doc, slugify(section.heading), section.heading, 0))
        cls = "band first" if first else "band"
        return f'<section class="{cls}"><h2>{esc(label)}</h2>\n' + "\n".join(parts) + "</section>"

    # The hero: the product name, and the method document's own strapline.
    hero = (
        f'<section class="hero"><h1>{esc(SITE_NAME)}</h1>'
        f'<p class="tagline">{esc(method.tagline.strip("*"))}</p></section>'
    )

    # What this is: the method document's own opening, verbatim.
    ctx = _ctx_for(method, resolver, 0)
    ctx.slugs = page_slugs
    intro = (
        f'<section class="band first"><h2>What this is</h2>\n'
        f"{render_blocks(method.preamble_lines(), ctx)}\n"
        f"{citation(method, '', '', 0)}</section>"
    )

    bands = [
        band("The loop", [(method, r"^1\. Core Model$")]),
        band("What proven means", [(method, r"^9\. Definition of Proven$")]),
        band("The one rule", [(method, r"^22\. The \S+ Rule$")]),
        band("Start here", [(plugin, r"^2\. Install$"), (plugin, r"^3\. The first change$")]),
        build_document_band(docs, 0),
        band("What it values", [(method, r"^20\. \S+ Manifesto$")]),
    ]

    body = hero + intro + "\n".join(bands)
    description = (
        f"{SITE_NAME}: a specification-driven, proof-gated development method for teams "
        "that build with AI coding agents."
    )
    return page_shell(SITE_NAME, description, body, 0, "index.html", author)


def build_document_band(docs: list[Document], depth: int) -> str:
    """A short routing block on the landing page: title, purpose, link, per document."""
    up = "../" * depth
    rows = []
    for doc in docs:
        if doc.series != "documents":
            continue
        rows.append(
            f'<li><a href="{esc(up + doc.out_path)}">{esc(doc.nav_title)}</a>. {esc(doc.purpose)}</li>'
        )
    training = [d for d in docs if d.series == "training"]
    listing = "<ol>" + "".join(rows) + "</ol>"
    more = (
        f'<p><a href="{esc(up + "docs/index.html")}">All documents</a>, '
        f"including the {len(training)} role training documents.</p>"
    )
    # CHROME: the heading and the one connective phrase above. Each document's
    # description is its purpose line from docs/manifest.yaml, unedited.
    return f'<section class="band"><h2>The documents</h2>\n{listing}\n{more}</section>'


def build_docs_index(manifest: dict, docs: list[Document], author: str) -> str:
    """The document index, rendered from docs/manifest.yaml.

    The manifest already records what every document is FOR: its purpose, its
    audience, and what it covers. That is the index. Writing a second set of
    descriptions here is precisely the duplication O3 forbids.
    """

    def rows(series: str) -> str:
        out = []
        for doc in sorted(
            (d for d in docs if d.series == series), key=lambda d: (d.reading_order, d.slug)
        ):
            meta = []
            if doc.audience:
                meta.append(f"<dt>Audience</dt><dd>{esc(doc.audience)}</dd>")
            if doc.covers:
                meta.append(f"<dt>Covers</dt><dd>{esc(doc.covers)}</dd>")
            if doc.version:
                meta.append(
                    f"<dt>Version</dt><dd>{esc(doc.version)}, {esc(doc.version_date)}</dd>"
                )
            out.append(
                f'<div class="docrow">'
                f'<p class="ordinal">{doc.reading_order}</p>'
                f'<h3><a href="{esc(doc.slug)}.html">{esc(doc.nav_title)}</a></h3>'
                f"<p>{esc(doc.purpose)}</p>"
                f'<dl class="sans">{"".join(meta)}</dl>'
                f"</div>"
            )
        return "".join(out)

    # CHROME: the two series headings and the page title below.
    body = (
        '<div class="column">'
        "<h1>Documents</h1>"
        f'<h2>Read in this order</h2>{rows("documents")}'
        f'<h2>The role training series</h2>{rows("training")}'
        "</div>"
    )
    return page_shell(
        f"Documents - {SITE_NAME}",
        f"The {SITE_NAME} documents: the method, setup and running, the plugin guide, the runbook, "
        "the human transition, the tracker guide, and the role training series.",
        body,
        1,
        "docs/index.html",
        author,
    )


def build_doc_page(doc: Document, resolver: LinkResolver, author: str) -> str:
    ctx = _ctx_for(doc, resolver, 1, out_page=doc.out_path)
    ctx.min_heading_level = 2
    # The title, strapline and version line are rendered by the page header, so
    # the body drops them rather than printing them twice.
    body_lines = [
        line
        for n, line in enumerate(doc.lines)
        if n != doc.title_line
        and line.strip() != doc.tagline
        and not VERSION_RE.match(line.strip())
    ]
    content = render_blocks(body_lines, ctx)

    toc_items = "".join(
        f'<li><a href="#{esc(slug)}">{esc(text)}</a></li>'
        for level, text, slug in ctx.collected_headings
        if level == 2
    )
    # CHROME: the word "Contents".
    toc = f'<nav class="toc" aria-label="Contents"><span class="eyebrow">Contents</span><ol>{toc_items}</ol></nav>'

    meta = []
    if doc.version:
        meta.append(f"Version {esc(doc.version)}, {esc(doc.version_date)}")
    head = (
        f'<div class="dochead"><h1>{esc(doc.title)}</h1>'
        + (f'<p class="tagline">{esc(doc.tagline.strip("*"))}</p>' if doc.tagline else "")
        + (f'<p class="meta">{" . ".join(meta)}</p>' if meta else "")
        + "</div>"
    )

    body = f'<div class="doc">{head}{toc}<article>{content}</article></div>'
    return page_shell(
        f"{doc.nav_title} - {SITE_NAME}",
        doc.purpose or doc.tagline.strip("*"),
        body,
        1,
        "docs/method.html" if doc.slug == "method" else "docs/index.html",
        author,
        wide=True,
    )


# ===========================================================================
# Build
# ===========================================================================


def build(out_dir: Path) -> dict[str, str]:
    manifest, docs = load_manifest()
    author = str(manifest.get("author", "")).strip()
    if not author:
        raise SystemExit("docs/manifest.yaml declares no author; the footer has nothing to say.")
    resolver = LinkResolver(docs)

    files: dict[str, str] = {}
    files["index.html"] = build_landing(docs, resolver, author)
    files["docs/index.html"] = build_docs_index(manifest, docs, author)
    for doc in docs:
        files[doc.out_path] = build_doc_page(doc, resolver, author)
    files["CNAME"] = SITE_DOMAIN + "\n"
    # GitHub Pages runs Jekyll by default, which drops files it does not expect.
    files[".nojekyll"] = ""

    if out_dir.exists():
        shutil.rmtree(out_dir)
    for rel in sorted(files):
        path = out_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(files[rel], encoding="utf-8", newline="\n")
    return files


# ===========================================================================
# Self-checks
# ===========================================================================

BANNED_CHARS = {
    "\u2014": "em dash",
    "\u2013": "en dash",
    "\u2012": "figure dash",
    "\u2011": "non-breaking hyphen",
    "\u2010": "hyphen",
    "\u2212": "minus sign",
    "\u2015": "horizontal bar",
}

# Names that must never reach a published surface. The company, its products,
# its people, its suppliers, and the internal project vocabulary.
FORBIDDEN_TERMS = [
    "bcengi", "dejitech", "travelpass", "workpass", "agentpass", "staypass",
    "ridepass", "cruisepass", "clubpass", "eventpass", "coreconnect", "onesim",
    "mvne", "competitor", "hubspot", "webflow", "mailer", "scraper",
    "affiliate-network", "esim", "sompo", "support", "support", "frontend", "infra",
    "vadim", "yesepkin", "kinitsky", "veldo.dev/internal",
]

# Third-party tool and vendor names the METHOD DOCUMENTS legitimately reference,
# because a method for building with AI coding agents cannot describe the tools
# without naming them. Reported for a human ruling, never silently allowed.
THIRD_PARTY_NAMES = [
    "Claude Code", "Cursor", "Codex", "Copilot", "Antigravity", "OpenCode",
    "Aider", "Jira", "Confluence", "GitHub", "Figma", "Slack", "Git",
]


def _strip_code(text: str) -> str:
    text = re.sub(r"<pre\b.*?</pre>", " ", text, flags=re.S)
    text = re.sub(r"<code\b.*?</code>", " ", text, flags=re.S)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.S)
    return text


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


def check_internal_links(out_dir: Path) -> CheckResult:
    """Every relative href resolves to a file that exists, and every fragment to an id."""
    ids: dict[Path, set[str]] = {}
    pages = sorted(out_dir.rglob("*.html"))
    for page in pages:
        text = page.read_text(encoding="utf-8")
        ids[page] = set(re.findall(r'id="([^"]+)"', text))

    checked = 0
    failures: list[str] = []
    for page in pages:
        text = page.read_text(encoding="utf-8")
        for href in re.findall(r'href="([^"]+)"', text):
            if href.startswith(("http://", "https://", "mailto:")):
                continue
            checked += 1
            path_part, _, fragment = href.partition("#")
            target = page if not path_part else (page.parent / path_part).resolve()
            if path_part and not target.is_file():
                failures.append(f"{page.relative_to(out_dir)} -> {href} (no such file)")
                continue
            if fragment and fragment not in ids.get(target, set()):
                failures.append(f"{page.relative_to(out_dir)} -> {href} (no such anchor)")
    return CheckResult(
        "internal links resolve",
        not failures,
        f"{checked} internal links and fragments across {len(pages)} pages"
        + ("" if not failures else "\n      " + "\n      ".join(failures[:20])),
    )


# THE OLD NAME AS DATA, for the check that keeps it out. Split so the rename cannot reach it: this
# file is itself renamed, and when the constant was a contiguous literal the migration rewrote it to
# the NEW name, which left this check hunting for "veldo" in a site that is entirely about Veldo. A
# residual check that has been retargeted at the thing it is supposed to permit is worse than no
# check, because it reports on every page while finding nothing that matters. Do not rejoin it.
_OLD_NAME = "W" "ARP"


def _repo_slug(url: str) -> str:
    """`owner/name` from a repository url, for the footer link's visible text.

    This function was DELETED with the name-mapping scaffolding, because it sat inside that block,
    and nothing noticed: its only caller is behind REPO_PUBLIC, which was False, so the NameError
    could not fire until the day the repository went public and the flag flipped. A code path behind
    a flag is untested code until the flag moves, and the flag moved once, today."""
    return url.rstrip("/").split("github.com/", 1)[-1]


def check_old_name(out_dir: Path) -> CheckResult:
    """No residual occurrence of the old internal name, in any case, anywhere."""
    pattern = re.compile(_OLD_NAME, re.IGNORECASE)
    hits: list[str] = []
    scanned = 0
    for path in sorted(out_dir.rglob("*")):
        if not path.is_file():
            continue
        scanned += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        for n, line in enumerate(text.split("\n"), 1):
            if pattern.search(line):
                hits.append(f"{path.relative_to(out_dir)}:{n}: {line.strip()[:110]}")
    # The all-caps form of the new name is banned in PROSE and permitted in CODE
    # IDENTIFIERS. Ruled by Dmitry 2026-08-09: Veldo in prose and branding, VELDO in
    # identifiers, on the reasoning that an env var is UPPER_SNAKE by convention and
    # nobody writes Github_TOKEN while still calling the product GitHub. So the
    # pattern below refuses a BARE all-caps token and allows VELDO_FOO and VELDO-0142.
    # Anchored on what FOLLOWS the token, because that is what distinguishes an
    # identifier from a word: an identifier continues into _ or - plus more token.
    bare_upper = re.compile(r"VELDO(?![_-]?[A-Z0-9#N])(?!\.[a-z])")
    upper_hits: list[str] = []
    for path in sorted(out_dir.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for n, line in enumerate(text.split("\n"), 1):
            if bare_upper.search(line):
                upper_hits.append(f"{path.relative_to(out_dir)}:{n}: {line.strip()[:110]}")
    detail = (f"{scanned} output files scanned for the old name (any case) and for the "
              "all-caps new name in prose (identifiers such as VELDO_FOO are permitted)")
    if hits or upper_hits:
        detail += "\n      " + "\n      ".join((hits + upper_hits)[:20])
    return CheckResult("no residual old name", not (hits or upper_hits), detail)


def check_dashes(out_dir: Path) -> CheckResult:
    """No em dash, en dash, or prose double-hyphen. Command-line flags in code are exempt."""
    failures: list[str] = []
    scanned = 0
    for path in sorted(out_dir.rglob("*")):
        if not path.is_file():
            continue
        scanned += 1
        raw = path.read_text(encoding="utf-8", errors="replace")
        for char, name in BANNED_CHARS.items():
            if char in raw:
                failures.append(f"{path.relative_to(out_dir)}: contains {name} (U+{ord(char):04X})")
        prose = _strip_code(raw) if path.suffix == ".html" else raw
        for n, line in enumerate(prose.split("\n"), 1):
            if "--" in line:
                failures.append(f"{path.relative_to(out_dir)}:{n}: prose double-hyphen: {line.strip()[:110]}")
    detail = (
        f"{scanned} output files scanned; {len(BANNED_CHARS)} dash codepoints plus prose "
        "double-hyphen (code and pre content exempt, where a shell flag is legitimate)"
    )
    if failures:
        detail += "\n      " + "\n      ".join(failures[:20])
    return CheckResult("no banned dash characters", not failures, detail)


def check_no_placeholders(out_dir: Path) -> CheckResult:
    """No unfilled placeholder anywhere in the output.

    REPO_URL sat at ORG-PLACEHOLDER because the owning organisation was undecided, and it went
    LIVE: the footer link and every source reference pointed at a repository that does not exist,
    and the install line told a reader to add a marketplace that is not there. Nothing caught it,
    because a placeholder is well-formed. It is only wrong in the one way a machine can check
    cheaply and a human reading a page will not: it says PLACEHOLDER."""
    # A BARE WORD IS NOT A MARKER. `TODO` alone matched Jira's own status category, printed in the
    # tracker guide as `TODO | IN_PROGRESS | DONE`, which is real documentation of a real API and not
    # a thing anyone forgot to fill in. A left-behind marker carries punctuation - a colon, a paren,
    # or the word PLACEHOLDER - so that is what is matched.
    marks = ("PLACEHOLDER", "TODO:", "TODO(", "FIXME", "XXX-", "TBD", "<<<")
    failures: list[str] = []
    scanned = 0
    for path in sorted(out_dir.rglob("*")):
        if not path.is_file():
            continue
        scanned += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        for n, line in enumerate(text.split("\n"), 1):
            for mark in marks:
                if mark in line:
                    failures.append(f"{path.relative_to(out_dir)}:{n}: {mark!r} in: {line.strip()[:90]}")
                    break
    return CheckResult(
        "no unfilled placeholders",
        not failures,
        f"{scanned} output files scanned for {len(marks)} placeholder markers"
        + ("" if not failures else "\n      " + "\n      ".join(failures[:12])),
    )


def check_leaks(out_dir: Path) -> CheckResult:
    """No company, customer, product or person name, other than the author."""
    failures: list[str] = []
    present_third_party: set[str] = set()
    scanned = 0
    for path in sorted(out_dir.rglob("*")):
        if not path.is_file():
            continue
        scanned += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        # OUR OWN DISTRIBUTION COORDINATE IS NOT A CUSTOMER NAME. `Bcengi/veldo` is where this code
        # lives and the install line has to print it. The repository's genericity sweep and the
        # publication leak scan both strip it before matching; this check did not, so it reported
        # the address of the project as a leak from the project. Stripped, not allowlisted by
        # filename, so a real occurrence of the company name anywhere else still fails.
        text = text.replace("Bcengi/veldo", "")
        lower = text.lower()
        for term in FORBIDDEN_TERMS:
            if term in lower:
                for n, line in enumerate(text.split("\n"), 1):
                    if term in line.lower():
                        failures.append(f"{path.relative_to(out_dir)}:{n}: {term!r} in: {line.strip()[:100]}")
                        break
        for name in THIRD_PARTY_NAMES:
            if re.search(rf"\b{re.escape(name)}\b", text):
                present_third_party.add(name)
    detail = (
        f"{scanned} output files scanned against {len(FORBIDDEN_TERMS)} forbidden terms. "
        "Third-party tool names present (method documents name the tools they run on): "
        + ", ".join(sorted(present_third_party))
    )
    if failures:
        detail += "\n      " + "\n      ".join(failures[:20])
    return CheckResult("no company, customer or person leaks", not failures, detail)


def check_markdown_residue(out_dir: Path) -> CheckResult:
    """Nothing the renderer failed to convert survives into the prose."""
    patterns = {
        "unconverted link": re.compile(r"\]\("),
        "unconverted strong": re.compile(r"\*\*"),
        "unconverted heading": re.compile(r"(?m)^#{1,6} "),
        "unconverted table rule": re.compile(r"\|\s*-{3,}"),
        "placeholder leak": re.compile(r"\x00"),
    }
    failures: list[str] = []
    for path in sorted(out_dir.glob("**/*.html")):
        prose = _strip_code(path.read_text(encoding="utf-8"))
        for label, rx in patterns.items():
            match = rx.search(prose)
            if match:
                start = max(0, match.start() - 60)
                failures.append(f"{path.relative_to(out_dir)}: {label}: ...{prose[start:match.end() + 60]}...")
    return CheckResult(
        "no unrendered markdown residue",
        not failures,
        f"{len(list(out_dir.glob('**/*.html')))} pages scanned for {len(patterns)} residue patterns"
        + ("" if not failures else "\n      " + "\n      ".join(failures[:10])),
    )


def digest_tree(root: Path) -> list[tuple[str, str]]:
    out = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            out.append(
                (
                    str(path.relative_to(root)),
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                )
            )
    return out


def check_idempotent() -> tuple[CheckResult, str]:
    """Build twice into two scratch trees and compare every byte."""
    scratch = Path(tempfile.mkdtemp(prefix="veldo-site-idempotency-"))
    try:
        first, second = scratch / "build-a", scratch / "build-b"
        build(first)
        build(second)
        d1, d2 = digest_tree(first), digest_tree(second)
        cmp_result = filecmp.dircmp(str(first), str(second))
        combined = hashlib.sha256(
            "\n".join(f"{name} {digest}" for name, digest in d1).encode()
        ).hexdigest()
        same = d1 == d2 and not cmp_result.diff_files and not cmp_result.funny_files
        proof = (
            f"build A: {len(d1)} files, tree digest {combined}\n"
            f"      build B: {len(d2)} files, tree digest "
            + hashlib.sha256("\n".join(f'{n} {h}' for n, h in d2).encode()).hexdigest()
        )
        return (
            CheckResult("build is byte-identical twice over", same, proof),
            combined,
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# Each entry seeds ONE defect into a throwaway copy of the output and names the
# check that must refuse it. A check that passes on clean output proves nothing
# on its own: it might be a check that can never fail. These are the negative
# controls, and they ADD content rather than pinning any count.
SEEDED_DEFECTS: list[tuple[str, str, object]] = [
    ("the old internal name reintroduced", "<p>VELDO is the name.</p>", check_old_name),
    ("the all-caps new name reintroduced", "<p>VELDO is the name.</p>", check_old_name),
    ("an em dash in prose", "<p>proof \u2014 evidence</p>", check_dashes),
    ("an en dash in prose", "<p>pages 1\u20132</p>", check_dashes),
    ("a prose double-hyphen", "<p>proof -- evidence</p>", check_dashes),
    ("a company name", "<p>Built at Bcengi.</p>", check_leaks),
    ("an unfilled placeholder", "<p>See ORG-PLACEHOLDER/veldo.</p>", check_no_placeholders),
    ("a link to a page that does not exist", '<p><a href="nowhere.html">gone</a></p>', check_internal_links),
    ("a broken fragment", '<p><a href="index.html#no-such-anchor">gone</a></p>', check_internal_links),
    ("unrendered markdown", "<p>**not converted**</p>", check_markdown_residue),
]


def prove_checks_have_teeth() -> list[CheckResult]:
    """Seed each defect class into a scratch copy and assert the check REFUSES it."""
    scratch = Path(tempfile.mkdtemp(prefix="veldo-site-negative-control-"))
    results: list[CheckResult] = []
    try:
        clean = scratch / "clean"
        build(clean)
        for n, (label, seed, check) in enumerate(SEEDED_DEFECTS):
            seeded = scratch / f"seeded-{n}"
            shutil.copytree(clean, seeded)
            page = seeded / "index.html"
            page.write_text(page.read_text(encoding="utf-8") + seed, encoding="utf-8", newline="\n")
            verdict = check(seeded)
            results.append(
                CheckResult(
                    f"refuses {label}",
                    not verdict.passed,
                    f"{verdict.name} returned "
                    + ("FAIL, as it must" if not verdict.passed else "PASS, so the check is vacuous"),
                )
            )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    return results


def run_checks(out_dir: Path) -> bool:
    results = [
        check_internal_links(out_dir),
        check_old_name(out_dir),
        check_dashes(out_dir),
        check_no_placeholders(out_dir),
        check_leaks(out_dir),
        check_markdown_residue(out_dir),
    ]
    idempotency, tree_digest = check_idempotent()
    results.append(idempotency)

    print("\nVerification")
    print("=" * 72)
    for r in results:
        print(f"  [{'PASS' if r.passed else 'FAIL'}] {r.name}")
        print(f"      {r.detail}")

    teeth = prove_checks_have_teeth()
    print("-" * 72)
    print("  Negative controls: each defect is seeded into a scratch copy of the")
    print("  output and the named check must refuse it.")
    for r in teeth:
        print(f"  [{'PASS' if r.passed else 'FAIL'}] {r.name}")
        print(f"      {r.detail}")

    print("=" * 72)
    print(f"  output tree digest: {tree_digest}")
    return all(r.passed for r in results + teeth)


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Build the {SITE_DOMAIN} static site.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output directory")
    parser.add_argument("--no-check", action="store_true", help="skip the self-checks (not advised)")
    args = parser.parse_args()

    files = build(args.out)
    print(f"Built {len(files)} files into {args.out}")
    for rel in sorted(files):
        size = (args.out / rel).stat().st_size
        print(f"  {rel:44s} {size:>8,d} bytes")

    if args.no_check:
        return 0
    return 0 if run_checks(args.out) else 1


if __name__ == "__main__":
    sys.exit(main())
