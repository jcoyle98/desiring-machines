# Site

A tiny static site for poems. Plain-text files in, HTML out, no dependencies beyond Python 3.

## Add a poem or essay

Poems go in `writings/poetry/`, essays in `writings/essays/`, reviews in `writings/reviews/`, named `YYYY-MM-DD-some-slug.txt`.
Each is listed in its own section on the Writings page: poems and essays newest
first, reviews oldest first. Sections with nothing published are left off.
The first line is the title, then a blank line, then the text.

A poem keeps its line breaks and indentation exactly:

```
Title of the Poem

First line
    indented line (tabs or spaces; a tab = 4 spaces)

A blank line starts a new stanza.
*Asterisks* make italics.
| A line starting with a bar is centered.
```

An essay is prose: a blank line separates paragraphs, and line breaks inside a
paragraph are ignored. A paragraph starting with `|` is centered (e.g. `| * * *`
for a section break).
Wrap text in triple quotes to make a block quote, inset slightly on both sides:

```
As Hegel puts it:

"""
The owl of Minerva spreads its wings only with the falling of the dusk.
"""

And so on.
```

(`"""A one-paragraph quote."""` on a single line works too.)

Text on the line right after a closing `"""` continues the same paragraph (no
indent). Leave a blank line after the quote to start a new, indented paragraph.

To quote verse inside an essay, put it between `<poem>` and `</poem>`. Inside, the
poem rules apply (line breaks, indentation, stanzas, `|` for centered lines), and the
passage is inset like a quote. The same continue-or-new-paragraph rule applies after it.

### Poem or prose

A file can start with a `<poem>` or `<prose>` line to say how it is set. Without
one, files in `writings/poetry/` are poems and files in `writings/essays/` are prose.
(Useful for an introductory essay inside a poetry collection.)

### Annotations (strophe labels etc.)

In a poem, `<annotation>…</annotation>` anywhere on a line sets whatever you type
between the tags flush right, level with that line:

```
<annotation>[strophe 1]</annotation>First line of the strophe
second line
<annotation>στρ. α´</annotation>or any other label
```

### Collections

A subfolder of `writings/poetry/` (or `writings/essays/`) is a collection. It needs
an `index.txt`: the collection's title, a blank line, then the pieces' file names
in reading order:

```
writings/poetry/poem-counter-poem/
    index.txt                     Poem/Counter-Poem
                                  
                                  introduction.txt
                                  2026-10-01-flying-music.txt
    introduction.txt              <prose>, then title, blank line, text
    2026-10-01-flying-music.txt
```

- The folder name becomes the URL, so keep it to lowercase letters, digits and hyphens
  (no slashes). The title in `index.txt` can contain anything.
- On the Writings page the collection gets its own header, which folds open to its
  contents. It also gets a contents page, and each piece links to the previous and next.
- Pieces in a collection don't need a date in the name. A `date: 2026-10-01` line
  under the title also works, anywhere.
- A `_` prefix makes a piece (or a whole collection folder) a draft. `index.txt` can
  list a draft without the underscore, so nothing needs changing when you publish it.
- A collection whose pieces are all drafts is left off the live site entirely
  (it still shows in the local preview).
- The build warns about files that aren't listed in `index.txt`, and listed files that don't exist.

### Sanskrit

Anywhere (titles, poems, essays), type SLP1 between `<sanskrit>` and `</sanskrit>`
and it becomes Devanagari: `<sanskrit>fta</sanskrit>` → ऋत. `|` or `.` is a danda,
`||` or `..` a double danda, `'` an avagraha, and digits become Devanagari digits
(a point between digits, as in `2.47`, stays a point).

- The date comes from the filename and is shown at the bottom of the piece.
- The slug becomes the URL (`/writings/poetry/some-slug/`, `/writings/essays/some-slug/`).
- Prefix the filename with `_` to keep it as an unpublished draft. Drafts show in the local
  preview but never on the site, and git ignores them, so they never reach GitHub either.

Then publish:

```
git add -A && git commit -m "New poem" && git push
```

GitHub Actions rebuilds and deploys the site in about a minute.

## Edit the rest

| What | Where |
|---|---|
| About / landing page | `about.txt` (blank line between paragraphs) |
| Site title, author, description | `config.json` |
| Coming-soon placeholder on the live site | `"coming_soon": true` in `config.json` (set to `false` to launch) |
| Page layout | `templates/base.html` |
| Styling | `static/style.css` |

## Preview locally

```
python3 build.py --serve
```

Open http://localhost:8000. The site rebuilds when you save a file; refresh to see it.

## First-time GitHub setup

1. Create an empty repo on GitHub (no README).
2. `git remote add origin git@github.com:USER/REPO.git && git push -u origin main`
3. In the repo: **Settings → Pages → Source: GitHub Actions**.

The site will be at `https://USER.github.io/REPO/`. (Name the repo `USER.github.io`
to serve it at the root instead. All links are relative, so either works.)
