#!/usr/bin/env python3
"""Build the site into _site/. No dependencies beyond Python 3.

    python3 build.py           # build once
    python3 build.py --serve   # build, serve at http://localhost:8000,
                               # and rebuild whenever a file changes

While "coming_soon" is true in config.json, a plain build (what GitHub
runs) produces only a placeholder page; --serve always builds the full site,
drafts included.

Poems live in writings/poetry/ and essays in writings/essays/, named
YYYY-MM-DD-slug.txt. Both are listed on the Writings page.
The first line is the title, then a blank line, then the text.

Poems keep their line breaks and indentation:

    Title of the Poem

    First line of the poem
        indented line (leading spaces are kept)

    Second stanza (blank line = new stanza), *italic words*
    | a line starting with "|" is centered

Essays are prose: a blank line separates paragraphs, and line breaks
within a paragraph are ignored. A paragraph starting with "|" is centered.
Anywhere (titles, poems, essays), <sanskrit>SLP1</sanskrit> is converted to
Devanagari, e.g. <sanskrit>fta</sanskrit> -> ऋत. In SLP1, | or . is a danda
and || or .. a double danda; digits become Devanagari digits.

Text between triple double-quotes becomes an indented block quote, and
<poem>...</poem> an indented passage of verse, laid out like a poem file. Text on
the line right after a closing quote or </poem> continues the same paragraph;
leave a blank line after the quote to start a new, indented paragraph.

A file may start with a <poem> or <prose> line to say how it is set; without
one, files in poetry/ are poems and files in essays/ are prose. Under the title,
before the blank line, "date: 2026-10-01" can stand in for a date in the name.

In a poem, <annotation>...</annotation> anywhere on a line sets whatever is
between the tags flush right, level with the line (e.g. [strophe 1]).

Collections: a subfolder of writings/poetry/ (or writings/essays/) with an
index.txt. Its first line is the collection's title; after a blank line, list
the pieces' file names in reading order. Pieces in a collection don't need a
date. The collection gets a contents page, and each piece links to the next.

A file or collection folder whose name starts with "_" is a draft: skipped on
the live site, shown in the local preview.
"""

import hashlib
import html
import json
import re
import shutil
import sys
import unicodedata
from datetime import date
from pathlib import Path
from string import Template

ROOT = Path(__file__).parent
OUT = ROOT / "_site"


# SLP1 -> Devanagari. Consonants carry an inherent "a"; other vowels after a
# consonant become vowel signs, and a consonant with no vowel gets a virama.
SLP1_VOWELS = {
    "a": ("अ", ""), "A": ("आ", "ा"), "i": ("इ", "ि"), "I": ("ई", "ी"),
    "u": ("उ", "ु"), "U": ("ऊ", "ू"), "f": ("ऋ", "ृ"), "F": ("ॠ", "ॄ"),
    "x": ("ऌ", "ॢ"), "X": ("ॡ", "ॣ"), "e": ("ए", "े"), "E": ("ऐ", "ै"),
    "o": ("ओ", "ो"), "O": ("औ", "ौ"),
}
SLP1_CONSONANTS = dict(zip(
    "kKgGNcCjJYwWqQRtTdDnpPbBmyrlvSzshL",
    "कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसहळ",
))
SLP1_OTHER = {
    "M": "ं", "H": "ः", "~": "ँ", "'": "ऽ", "||": "॥", "|": "।", "..": "॥", ".": "।",
    **{str(d): chr(0x0966 + d) for d in range(10)},
}
SANSKRIT_RE = re.compile(r"<sanskrit>(.*?)<[/\\]sanskrit>", re.DOTALL)


def slp1_to_devanagari(text):
    out, i = [], 0
    while i < len(text):
        c = text[i]
        if c in SLP1_CONSONANTS:
            out.append(SLP1_CONSONANTS[c])
            nxt = text[i + 1] if i + 1 < len(text) else ""
            if nxt in SLP1_VOWELS:
                out.append(SLP1_VOWELS[nxt][1])
                i += 1
            else:
                out.append("्")
        elif c in SLP1_VOWELS:
            out.append(SLP1_VOWELS[c][0])
        elif c == "." and text[i - 1:i].isdigit() and text[i + 1:i + 2].isdigit():
            out.append(".")  # keep the point in verse numbers like 2.47
        elif text[i:i + 2] in SLP1_OTHER:
            out.append(SLP1_OTHER[text[i:i + 2]])
            i += 1
        else:
            out.append(SLP1_OTHER.get(c, c))
        i += 1
    return "".join(out)


def read_text(path):
    """Read a UTF-8 file, composing accents (e.g. a + combining acute -> á) so
    fonts use their precomposed letters, which are better drawn, and turning
    <sanskrit>SLP1</sanskrit> into Devanagari."""
    text = unicodedata.normalize("NFC", path.read_text(encoding="utf-8"))
    text = SANSKRIT_RE.sub(lambda m: slp1_to_devanagari(m.group(1)), text)
    if "<sanskrit>" in text:
        print(f"  warning: {path.name} has a <sanskrit> tag that is never closed")
    return text


def inline(text):
    """Escape HTML, then turn *words* into italics."""
    return re.sub(r"\*(\S(?:.*?\S)?)\*", r"<em>\1</em>", html.escape(text))


def blocks(text):
    """Split text into blocks separated by one or more blank lines."""
    return [b for b in re.split(r"\n\s*\n", text.strip("\n")) if b.strip()]


ANNOTATION_RE = re.compile(r"<(?:right-)?annotation>(.*?)<[/\\](?:right-)?annotation>")


def render_poem(body):
    stanzas = []
    for stanza in blocks(body):
        lines = []
        for line in stanza.rstrip().splitlines():
            # <annotation>...</annotation>: set flush right, level with the line
            notes = "".join(f'<span class="annot">{inline(n.strip())}</span>'
                            for n in ANNOTATION_RE.findall(line))
            line = ANNOTATION_RE.sub("", line).rstrip()
            stripped = line.lstrip(" \t")
            if stripped.startswith("|"):  # "| text" = centered line
                lines.append(f'<span class="line center">{notes}{inline(stripped[1:].strip())}</span>')
                continue
            indent = len(line[: len(line) - len(stripped)].expandtabs(4))
            style = f' style="margin-left:{indent * 0.5:g}em"' if indent else ""
            text = inline(stripped) or "&nbsp;"
            lines.append(f'<span class="line"{style}>{notes}{text}</span>')
        stanzas.append('<p class="stanza">\n' + "\n".join(lines) + "\n</p>")
    return '<div class="poem">\n' + "\n".join(stanzas) + "\n</div>"


def render_paragraphs(text, continues=False):
    """continues=True: the first block carries on a paragraph interrupted by a quote."""
    paragraphs = []
    for i, b in enumerate(blocks(text)):
        b = " ".join(b.split())
        if b.startswith("|"):  # "| text" = centered paragraph
            paragraphs.append(f'<p class="center">{inline(b[1:].strip())}</p>')
        elif i == 0 and continues:
            paragraphs.append(f'<p class="cont">{inline(b)}</p>')
        else:
            paragraphs.append(f"<p>{inline(b)}</p>")
    return "\n".join(paragraphs)


BLOCK_RE = re.compile(r'"""(.*?)"""|<poem>(.*?)<[/\\]poem>', re.DOTALL)


def render_prose(text):
    """Paragraphs, with \"\"\"...\"\"\" as a block quote and <poem>...</poem> as an
    inset passage of verse (same rules as a poem file)."""
    html_parts, pos = [], 0

    def add_paragraphs(chunk, after_block):
        if chunk.strip():
            # Text straight after a quote or poem (no blank line) continues the paragraph
            continues = after_block and not re.match(r"[ \t]*\n[ \t]*\n", chunk)
            html_parts.append(render_paragraphs(chunk, continues))

    for m in BLOCK_RE.finditer(text):
        add_paragraphs(text[pos:m.start()], after_block=pos > 0)
        if m.group(1) is not None:
            html_parts.append(f"<blockquote>\n{render_paragraphs(m.group(1))}\n</blockquote>")
        else:
            html_parts.append(f'<blockquote class="verse">\n{render_poem(m.group(2))}\n</blockquote>')
        pos = m.end()
    rest = text[pos:]
    for marker in ('"""', "<poem>"):
        if marker in rest:
            print(f"  warning: unmatched {marker} (left open)")
    add_paragraphs(rest, after_block=pos > 0)
    return "\n".join(html_parts)


# folder -> (heading, default kind of piece, order of standalone pieces)
SECTIONS = {
    "poetry": ("Poetry", "poem", "newest first"),
    "essays": ("Essays", "essay", "newest first"),
    "reviews": ("Reviews", "essay", "oldest first"),
}
RENDER = {"poem": render_poem, "essay": render_prose}
ARTICLE_CLASS = {"poem": "", "essay": "prose essay"}
DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-")


def parse_piece(path, default_kind):
    """A piece file: optional <poem> or <prose> line, title line, optional
    "date: YYYY-MM-DD" line, blank line, text."""
    text = read_text(path).strip()
    kind = default_kind
    m = re.match(r"<(poem|prose)>[ \t]*\n", text)
    if m:
        kind = "poem" if m.group(1) == "poem" else "essay"
        text = re.sub(r"\n[ \t]*<[/\\](poem|prose)>$", "", text[m.end():])  # optional closing tag
    header, _, body = re.split(r"(\n[ \t]*\n)", text + "\n\n", 1)
    title, *meta_lines = header.splitlines()
    meta = {}
    for line in meta_lines:
        key, sep, value = line.partition(":")
        if sep and key.strip().lower() == "date":
            meta["date"] = value.strip()
        else:
            print(f"  warning: {path.name}: ignoring header line {line!r} "
                  "(expected date:, then a blank line before the text)")

    name = path.stem.lstrip("_")
    m = DATE_PREFIX_RE.match(name)
    when = meta.get("date") or (m and m.group(1))
    return {
        "slug": DATE_PREFIX_RE.sub("", name),
        "title": title.strip(),
        "date": date.fromisoformat(when) if when else None,
        "kind": kind,
        "html": RENDER[kind](body),
        "draft": path.name.startswith("_"),
    }


def load_collection(folder, default_kind, include_drafts):
    """A collection is a subfolder with an index.txt: a title line, a blank line,
    then the file names of its pieces, one per line, in reading order."""
    draft = folder.name.startswith("_")
    if draft and not include_drafts:
        return None
    index = folder / "index.txt"
    if not index.exists():
        print(f"  skipping folder {folder.name}/: no index.txt")
        return None
    title, _, listing = read_text(index).strip().partition("\n")
    pieces, listed = [], set()
    for entry in listing.splitlines():
        entry = entry.strip()
        if not entry:
            continue
        name = entry.lstrip("_") + ("" if entry.endswith(".txt") else ".txt")
        path = next((p for p in (folder / name, folder / f"_{name}") if p.exists()), None)
        if path is None:
            if include_drafts:  # on GitHub, drafts are absent on purpose (git ignores them)
                print(f"  warning: {folder.name}/index.txt lists {entry!r}, but there is no such file")
            continue
        listed.add(path.name)
        piece = parse_piece(path, default_kind)
        if piece["draft"] and not include_drafts:
            continue
        pieces.append(piece)
    for path in folder.glob("*.txt"):
        if path.name != "index.txt" and path.name not in listed:
            print(f"  warning: {folder.name}/{path.name} is not listed in index.txt, so it is left out")
    if not pieces and not include_drafts:
        return None  # nothing published yet: leave the whole collection off the live site
    return {"slug": folder.name.lstrip("_"), "title": title.strip(), "pieces": pieces, "draft": draft}


def load_section(folder, default_kind, order, include_drafts=False):
    """Standalone pieces (newest first) and collections (alphabetical by folder)."""
    root = ROOT / "writings" / folder
    pieces, collections = [], []
    if not root.is_dir():  # e.g. a section whose only files are drafts, which git ignores
        return pieces, collections
    for path in sorted(root.glob("*.txt")):
        if path.name.startswith("_") and not include_drafts:
            continue
        piece = parse_piece(path, default_kind)
        if piece["date"] is None:
            print(f"  skipping {path.name}: needs a date (YYYY-MM-DD- at the start of the "
                  "name, or a 'date:' line under the title)")
            continue
        pieces.append(piece)
    pieces.sort(key=lambda p: p["date"], reverse=(order == "newest first"))
    for sub in sorted(d for d in root.iterdir() if d.is_dir()):
        c = load_collection(sub, default_kind, include_drafts)
        if c:
            collections.append(c)
    return pieces, collections


def fmt_date(d):
    return f"{d.day} {d.strftime('%B %Y')}"


def meta(p):
    parts = [fmt_date(p["date"])] if p.get("date") else []
    if p["draft"]:
        parts.append("draft")
    return " · ".join(parts)
def css_version():
    """Changes whenever style.css does, so browsers never use a stale copy."""
    return hashlib.md5((ROOT / "static" / "style.css").read_bytes()).hexdigest()[:8]


def write_page(rel_path, title, content, config, depth):
    base = Template((ROOT / "templates" / "base.html").read_text(encoding="utf-8"))
    page = base.substitute(
        root="../" * depth,
        title=html.escape(title),
        site_title=html.escape(config["site_title"]),
        author=html.escape(config["author"]),
        description=html.escape(config["description"]),
        year=date.today().year,
        css_version=css_version(),
        content=content,
    )
    dest = OUT / rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(page, encoding="utf-8")


def inline_title(title):
    return html.escape(title)


def collection_meta(c):
    n = len(c["pieces"])
    return f"{n} piece{'s' if n != 1 else ''}" + (" · draft" if c["draft"] else "")


def collection_block(folder, c):
    """A collection on the Writings page: a header that folds open to its contents."""
    items = "\n".join(
        f'<li><a href="{folder}/{c["slug"]}/{p["slug"]}/">{inline_title(p["title"])}</a>'
        f'<span class="meta">{meta(p)}</span></li>'
        for p in c["pieces"]
    ) or '<li class="empty">Nothing yet.</li>'
    return (f'<details class="collection" open>\n<summary><h3>{inline_title(c["title"])}</h3>'
            f'<span class="meta">{collection_meta(c)}</span></summary>\n'
            f'<ol class="index">\n{items}\n</ol>\n</details>')


def write_piece(rel_dir, p, config, depth, above="", below=""):
    date_line = f'\n<p class="post-date">{meta(p)}</p>' if meta(p) else ""
    content = (
        f'<article class="{ARTICLE_CLASS[p["kind"]]}">\n{above}'
        f'<header><h1>{inline_title(p["title"])}</h1></header>\n'
        f'{p["html"]}{date_line}\n</article>{below}'
    )
    write_page(f"{rel_dir}/index.html", p["title"], content, config, depth)


def write_collection(rel_dir, c, config):
    """A contents page, then each piece with links to its neighbours."""
    items = "\n".join(
        f'<li><a href="{p["slug"]}/">{inline_title(p["title"])}</a>'
        + (' <span class="meta">draft</span>' if p["draft"] else "") + "</li>"
        for p in c["pieces"]
    ) or '<li class="empty">Nothing yet.</li>'
    draft = '<p class="meta">draft</p>' if c["draft"] else ""
    write_page(f"{rel_dir}/index.html", c["title"],
               f'<h1>{inline_title(c["title"])}</h1>{draft}\n<ol class="contents">\n{items}\n</ol>',
               config, depth=3)

    pieces = c["pieces"]
    for i, p in enumerate(pieces):
        prev_link = (f'<a class="prev" href="../{pieces[i-1]["slug"]}/">← {inline_title(pieces[i-1]["title"])}</a>'
                     if i > 0 else "<span></span>")
        next_link = (f'<a class="next" href="../{pieces[i+1]["slug"]}/">{inline_title(pieces[i+1]["title"])} →</a>'
                     if i + 1 < len(pieces) else "<span></span>")
        above = f'<p class="collection-name"><a href="../"><em>{inline_title(c["title"])}</em></a></p>\n'
        below = (f'\n<nav class="sequence">{prev_link}<a class="up" href="../">Contents</a>'
                 f'{next_link}</nav>')
        write_piece(f"{rel_dir}/{p['slug']}", p, config, depth=4, above=above, below=below)


def build_coming_soon(config):
    page = Template((ROOT / "templates" / "coming-soon.html").read_text(encoding="utf-8"))
    (OUT / "index.html").write_text(page.substitute(
        site_title=html.escape(config["site_title"]),
        description=html.escape(config["description"]),
        css_version=css_version(),
    ), encoding="utf-8")
    (OUT / ".nojekyll").touch()
    print("Built coming-soon page into _site/ (set coming_soon to false to publish)")


def build(full=False):
    """Build the site. Unless full=True, honour the coming_soon switch."""
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "static", OUT / "static")

    if config.get("coming_soon") and not full:
        build_coming_soon(config)
        return

    # Landing / about page
    about = render_prose(read_text(ROOT / "about.txt"))
    write_page("index.html", config["site_title"],
               f'<article class="prose">\n{about}\n</article>', config, depth=0)

    # Writings page: one subsection per section, collections first, then
    # standalone pieces. Pieces live at writings/<section>/<slug>/ and, in a
    # collection, at writings/<section>/<collection>/<slug>/.
    counts, sections = [], []
    for folder, (heading, default_kind, order) in SECTIONS.items():
        pieces, collections = load_section(folder, default_kind, order, include_drafts=full)
        counts.append(f"{len(pieces)} {folder} + {len(collections)} collection(s)")

        # Standalone pieces first, then each collection under its own header
        rows = "\n".join(
            f'<li><a href="{folder}/{p["slug"]}/">{inline_title(p["title"])}</a>'
            f'<span class="meta">{meta(p)}</span></li>'
            for p in pieces
        )
        parts = [f'<ul class="index">\n{rows}\n</ul>'] if rows else []
        parts += [collection_block(folder, c) for c in collections]
        if parts:  # sections with nothing to show are left off the page
            sections.append(f'<section>\n<h2>{heading}</h2>\n' + "\n".join(parts) + '\n</section>')

        for p in pieces:
            write_piece(f"writings/{folder}/{p['slug']}", p, config, depth=3)
        for c in collections:
            write_collection(f"writings/{folder}/{c['slug']}", c, config)

    write_page("writings/index.html", "Writings",
               "<h1>Writings</h1>\n" + "\n".join(sections), config, depth=1)

    (OUT / ".nojekyll").touch()
    print(f"Built {', '.join(counts)} into _site/")




def snapshot():
    watched = [ROOT / "about.txt", ROOT / "config.json", ROOT / "build.py"]
    for folder in ("writings", "templates", "static"):
        watched += (ROOT / folder).rglob("*")
    return {p: p.stat().st_mtime for p in watched if p.is_file()}


def serve(port=8000):
    import functools
    import http.server
    import os
    import threading
    import time

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    handler = functools.partial(Quiet, directory=str(OUT))
    server = http.server.ThreadingHTTPServer(("localhost", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"Serving at http://localhost:{port}  (Ctrl-C to stop)")

    last = snapshot()
    try:
        while True:
            time.sleep(1)
            current = snapshot()
            if current != last:
                if current.get(ROOT / "build.py") != last.get(ROOT / "build.py"):
                    print("build.py changed; restarting")
                    server.server_close()
                    os.execv(sys.executable, [sys.executable, *sys.argv])
                last = current
                try:
                    build(full=True)
                except Exception as e:
                    print(f"  build failed: {e}")
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    serving = "--serve" in sys.argv
    build(full=serving)  # the local preview always shows the full site
    if serving:
        serve()
