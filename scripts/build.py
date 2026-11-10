#!/usr/bin/env python3
"""Generate docs/index.html + docs/releases.json from public GitHub releases."""
import html, json, os, sys, urllib.request, urllib.error, datetime, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "config.json").read_text())
TOKEN = os.environ.get("GITHUB_TOKEN", "")


def api(path):
    items, url = [], f"https://api.github.com{path}"
    while url:
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "bbs-file-library"})
        if TOKEN:
            req.add_header("Authorization", f"Bearer {TOKEN}")
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
            link = r.headers.get("Link", "")
        if isinstance(data, list):
            items += data
        else:
            return data
        url = None
        for part in link.split(","):
            if 'rel="next"' in part:
                url = part[part.find("<") + 1:part.find(">")]
    return items


def repos_for(acct):
    for kind in ("orgs", "users"):
        try:
            return api(f"/{kind}/{acct}/repos?type=public&per_page=100")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
    raise SystemExit(f"account not found: {acct}")


def main():
    products = []
    for acct in CFG["accounts"]:
        for r in repos_for(acct):
            if r["private"] or r["archived"] or (r["fork"] and not CFG["include_forks"]):
                continue
            if r["full_name"] in CFG["exclude_repos"]:
                continue
            rels = [x for x in api(f"/repos/{r['full_name']}/releases?per_page={CFG['releases_per_repo']}") if not x["draft"]]
            if not rels:
                continue
            products.append({
                "account": acct, "repo": r["name"], "url": r["html_url"],
                "description": r["description"] or "",
                "releases": [{
                    "tag": x["tag_name"], "name": x["name"] or x["tag_name"],
                    "date": (x["published_at"] or "")[:10], "url": x["html_url"],
                    "prerelease": x["prerelease"],
                    "zip": x["zipball_url"], "tar": x["tarball_url"],
                    "assets": [{"name": a["name"], "size": a["size"], "url": a["browser_download_url"], "downloads": a["download_count"]} for a in x["assets"]],
                } for x in rels],
            })
    products.sort(key=lambda p: p["releases"][0]["date"], reverse=True)
    out = ROOT / "docs"
    out.mkdir(exist_ok=True)
    (out / "releases.json").write_text(json.dumps(products, indent=1))
    (out / "index.html").write_text(render(products))
    print(f"{len(products)} products")


def size(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024


def render(products):
    e = html.escape
    rows = []
    for p in products:
        latest = p["releases"][0]
        assets = "".join(f'<li><a href="{e(a["url"])}">{e(a["name"])}</a> <span class="m">{size(a["size"])} · {a["downloads"]}↓</span></li>' for a in latest["assets"]) or '<li class="m">no binary assets</li>'
        older = "".join(
            f'<div class="old"><b>{e(r["tag"])}</b> <span class="m">{e(r["date"])}</span> · ' +
            " · ".join(f'<a href="{e(a["url"])}">{e(a["name"])}</a>' for a in r["assets"]) +
            f' · <a href="{e(r["zip"])}">source.zip</a></div>' for r in p["releases"][1:])
        rows.append(f"""<tr data-s="{e((p['repo'] + ' ' + p['description'] + ' ' + p['account']).lower())}">
<td><a href="{e(p['url'])}"><b>{e(p['repo'])}</b></a><div class="m">{e(p['account'])}</div><div class="d">{e(p['description'])}</div></td>
<td><a href="{e(latest['url'])}">{e(latest['tag'])}</a>{' <span class="pre">pre</span>' if latest['prerelease'] else ''}</td>
<td>{e(latest['date'])}</td>
<td><ul>{assets}</ul></td>
<td><a href="{e(latest['zip'])}">zip</a> · <a href="{e(latest['tar'])}">tar.gz</a></td>
<td>{('<details><summary>' + str(len(p['releases']) - 1) + ' older</summary>' + older + '</details>') if older else ''}</td></tr>""")
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(CFG['title'])}</title><style>
:root{{--bg:#fff;--fg:#1a1a1a;--m:#666;--line:#ddd;--a:#0b57d0}}
@media(prefers-color-scheme:dark){{:root{{--bg:#14161a;--fg:#e6e6e6;--m:#999;--line:#333;--a:#8ab4f8}}}}
body{{background:var(--bg);color:var(--fg);font:15px system-ui,sans-serif;margin:0;padding:16px}}
a{{color:var(--a)}}h1{{margin:0 0 4px;font-size:1.4rem}}.m{{color:var(--m);font-size:.85em}}.d{{font-size:.85em;color:var(--m)}}
input{{width:100%;max-width:420px;padding:8px;margin:12px 0;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg)}}
table{{border-collapse:collapse;width:100%}}th,td{{text-align:left;vertical-align:top;padding:8px;border-bottom:1px solid var(--line)}}
th{{cursor:pointer;user-select:none}}ul{{margin:0;padding-left:16px}}.pre{{font-size:.75em;border:1px solid var(--line);padding:0 4px;border-radius:4px}}
.old{{font-size:.85em;margin:4px 0}}@media(max-width:700px){{table,tbody,tr,td{{display:block}}thead{{display:none}}}}
</style></head><body><h1>{e(CFG['title'])}</h1>
<div class="m">{len(products)} products · updated {now} · accounts: {e(', '.join(CFG['accounts']))}</div>
<input id="q" placeholder="Filter products…" autofocus>
<table id="t"><thead><tr><th>Product</th><th>Version</th><th>Released</th><th>Files</th><th>Source</th><th>History</th></tr></thead><tbody>
{''.join(rows)}</tbody></table>
<script>
const q=document.getElementById('q'),rs=[...document.querySelectorAll('#t tbody tr')];
q.oninput=()=>{{const v=q.value.toLowerCase();rs.forEach(r=>r.style.display=r.dataset.s.includes(v)?'':'none')}};
document.querySelectorAll('#t th').forEach((th,i)=>th.onclick=()=>{{const b=document.querySelector('#t tbody'),d=th.dataset.d=th.dataset.d=='1'?-1:1;
[...rs].sort((x,y)=>d*x.cells[i].innerText.localeCompare(y.cells[i].innerText)).forEach(r=>b.appendChild(r))}});
</script></body></html>"""


if __name__ == "__main__":
    main()
