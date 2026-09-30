# Site

A tiny static site for poems. Plain-text files in, HTML out, no dependencies beyond Python 3.

## Add a poem

Create `posts/YYYY-MM-DD-some-slug.txt`:

```
Title of the Poem

First line
    indented line (leading spaces are kept)

A blank line starts a new stanza.
*Asterisks* make italics.
```

- The first line is the title; everything after it is the poem.
- The date comes from the filename; the slug becomes the URL (`/writings/some-slug/`).
- Prefix the filename with `_` to keep it as an unpublished draft.

Then publish:

```
git add posts && git commit -m "New poem" && git push
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
