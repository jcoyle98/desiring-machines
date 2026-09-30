#!/usr/bin/env python3
"""Build the site into _site/. No dependencies beyond Python 3.

    python3 build.py           # build once
    python3 build.py --serve   # build, serve at http://localhost:8000,
                               # and rebuild whenever a file changes

Poems live in posts/ as YYYY-MM-DD-slug.txt:

    Title of the Poem
                                 <- blank line
    First line of the poem
        indented line (leading spaces are kept)
                                 <- blank line = new stanza
    Second stanza, *italic words*

A file whose name starts with "_" is a draft and is skipped.
"""

import html
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from string import Template

ROOT = Path(__file__).parent
OUT = ROOT / "_site"
POSTS = ROOT / "posts"
FILENAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)\.txt$")


def inline(text):
    """Escape HTML, then turn *words* into italics."""
    return re.sub(r"\*(\S(?:.*?\S)?)\*", r"<em>\1</em>", html.escape(text))


def blocks(text):
    """Split text into blocks separated by one or more blank lines."""
    return [b for b in re.split(r"\n\s*\n", text.strip("\n")) if b.strip()]


def render_poem(body):
    stanzas = []
    for stanza in blocks(body):
        lines = []
        for line in stanza.rstrip().splitlines():
            stripped = line.lstrip(" \t")
            indent = len(line[: len(line) - len(stripped)].expandtabs(4))
            style = f' style="margin-left:{indent * 0.5:g}em"' if indent else ""
            lines.append(f'<span class="line"{style}>{inline(stripped)}</span>')
        stanzas.append('<p class="stanza">\n' + "\n".join(lines) + "\n</p>")
    return '<div class="poem">\n' + "\n".join(stanzas) + "\n</div>"


def render_prose(text):
    return "\n".join(f"<p>{inline(' '.join(b.split()))}</p>" for b in blocks(text))


def load_posts():
    posts = []
    for path in sorted(POSTS.glob("*.txt")):
        if path.name.startswith("_"):
            continue
        match = FILENAME_RE.match(path.name)
        if not match:
            print(f"  skipping {path.name}: name must look like YYYY-MM-DD-slug.txt")
            continue
        title, _, body = path.read_text(encoding="utf-8").strip().partition("\n")
        posts.append({
            "slug": match.group(2),
            "title": title.strip(),
            "date": date.fromisoformat(match.group(1)),
            "lines": sum(1 for l in body.splitlines() if l.strip()),
            "html": render_poem(body),
        })
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def fmt_date(d):
    return f"{d.day} {d.strftime('%B %Y')}"


def meta(p):
    return f'{fmt_date(p["date"])} · {p["lines"]} lines'


def write_page(rel_path, title, content, config, depth):
    base = Template((ROOT / "templates" / "base.html").read_text(encoding="utf-8"))
    page = base.substitute(
        root="../" * depth,
        title=html.escape(title),
        site_title=html.escape(config["site_title"]),
        author=html.escape(config["author"]),
        description=html.escape(config["description"]),
        year=date.today().year,
        content=content,
    )
    dest = OUT / rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(page, encoding="utf-8")


def build():
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    posts = load_posts()

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "static", OUT / "static")

    # Landing / about page
    about = render_prose((ROOT / "about.txt").read_text(encoding="utf-8"))
    write_page("index.html", config["site_title"],
               f'<article class="prose">\n{about}\n</article>', config, depth=0)

    # Index of poems
    rows = "\n".join(
        f'<li><a href="{p["slug"]}/">{html.escape(p["title"])}</a>'
        f'<span class="meta">{meta(p)}</span></li>'
        for p in posts
    ) or "<li>Nothing yet.</li>"
    write_page("writings/index.html", "Writings",
               f'<h1>Writings</h1>\n<ul class="index">\n{rows}\n</ul>', config, depth=1)

    # Individual poems
    for p in posts:
        content = (
            f'<article>\n<header><h1>{html.escape(p["title"])}</h1>'
            f'<p class="meta">{meta(p)}</p></header>\n{p["html"]}\n</article>'
        )
        write_page(f'writings/{p["slug"]}/index.html', p["title"], content, config, depth=2)

    (OUT / ".nojekyll").touch()
    print(f"Built {len(posts)} poem(s) into _site/")


def snapshot():
    watched = [ROOT / "about.txt", ROOT / "config.json"]
    for folder in ("posts", "templates", "static"):
        watched += (ROOT / folder).rglob("*")
    return {p: p.stat().st_mtime for p in watched if p.is_file()}


def serve(port=8000):
    import functools
    import http.server
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
                last = current
                try:
                    build()
                except Exception as e:
                    print(f"  build failed: {e}")
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    build()
    if "--serve" in sys.argv:
        serve()
