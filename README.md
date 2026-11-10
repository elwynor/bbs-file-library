# BBS File Library
Static, auto-generated library of the latest public GitHub releases (binaries + source) for the accounts in `config.json`.
Rebuilt every 6 hours and on push by GitHub Actions; published with GitHub Pages. Edit `config.json` to add/remove accounts or exclude repos.
Local preview: `GITHUB_TOKEN=$(gh auth token) python3 scripts/build.py && open docs/index.html`
