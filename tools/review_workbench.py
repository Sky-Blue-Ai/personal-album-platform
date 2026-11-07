#!/usr/bin/env python3
"""核验工作台：把待核验候选做成一个可点选的本地页面。

    .venv/bin/python tools/review_workbench.py            # http://127.0.0.1:8790
    .venv/bin/python tools/review_workbench.py --port 8791 --limit 50

页面做的事只有三件：打开 source_url 看授权 → 点通过/拒绝 → 写回数据库。
**不做批量通过**：授权是逐张的事实，批量就是给自己埋雷。
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import psycopg
from psycopg.rows import dict_row

DEFAULT_DSN = os.environ.get("DATABASE_URL", "postgresql://album:album@127.0.0.1:5433/album")

SQL_LIST = """
select i.id, i.provider, i.provider_object_id, i.license, i.license_evidence,
       i.source_url, i.image_url, i.image_thumb, i.holding, i.credit_line,
       i.verification_status,
       a.title, a.title_zh, a.date_display, a.medium, a.dimensions,
       a.attribution_level, a.target_match,
       ar.name_zh, ar.name_en, ar.region, ar.phase
from artwork_image i
join artwork a on a.id = i.artwork_id
join artist ar on ar.id = a.artist_id
where i.verification_status = %s
order by ar.phase, ar.region, ar.id, i.id
limit %s
"""

SQL_COUNTS = """
select verification_status, count(*) as n from artwork_image group by 1
"""

PAGE = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>核验工作台 · 古代艺术名人画展</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  :root{
    --surface:#f9f9f9; --surface-low:#f3f3f3; --surface-lowest:#fff;
    --on-surface:#1a1c1c; --on-variant:#444748; --muted:#5f5e5e;
    --outline:#c4c7c7; --accent:#9c3327;
    --cc0:#2f6b4f; --pending:#8a6a1f; --restricted:#7a1f16;
    --mono:"JetBrains Mono",ui-monospace,Menlo,monospace;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--surface);color:var(--on-surface);
       font-family:Inter,"Noto Sans SC","PingFang SC",system-ui,sans-serif;font-size:14px}
  header{position:sticky;top:0;z-index:5;background:rgba(249,249,249,.94);
         backdrop-filter:blur(6px);border-bottom:1px solid var(--outline);padding:12px 24px;
         display:flex;align-items:center;gap:20px;flex-wrap:wrap}
  h1{font-family:"Noto Serif SC",Georgia,serif;font-size:17px;font-weight:500;margin:0;letter-spacing:.04em}
  .stats{font-family:var(--mono);font-size:11px;color:var(--muted);letter-spacing:.08em}
  .stats b{color:var(--on-surface)}
  .bar{flex:1;min-width:120px;height:3px;background:#e2e2e2;position:relative}
  .bar i{position:absolute;inset:0 auto 0 0;background:var(--cc0);width:0}
  .filters{display:flex;gap:6px;font-family:var(--mono);font-size:11px}
  .filters a{padding:4px 9px;border:1px solid var(--outline);color:var(--on-variant);text-decoration:none}
  .filters a.on{background:var(--on-surface);color:#fff;border-color:var(--on-surface)}
  main{padding:20px 24px 120px;display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(330px,1fr))}
  article{background:var(--surface-lowest);border:1px solid var(--outline);display:flex;flex-direction:column}
  .thumb{aspect-ratio:4/3;background:var(--surface-low);overflow:hidden;display:block}
  .thumb img{width:100%;height:100%;object-fit:cover;display:block}
  .thumb .ph{display:flex;align-items:center;justify-content:center;height:100%;
             font-family:var(--mono);font-size:11px;color:var(--muted)}
  .thumb[data-nophoto]::after{content:"图源未加载 · 点开核对授权";display:flex;align-items:center;justify-content:center;
             height:100%;font-family:var(--mono);font-size:11px;color:var(--muted)}
  .body{padding:12px 13px 13px;display:flex;flex-direction:column;gap:7px;flex:1}
  .artist{font-family:var(--mono);font-size:10px;letter-spacing:.12em;color:var(--muted);text-transform:uppercase}
  .title{font-family:"Noto Serif SC",Georgia,serif;font-size:15px;line-height:1.35;margin:0}
  .sub{font-size:11.5px;color:var(--on-variant);line-height:1.55}
  .ev{font-family:var(--mono);font-size:10.5px;color:var(--muted);background:var(--surface-low);
      padding:6px 7px;line-height:1.5;word-break:break-word}
  .acts{display:flex;gap:6px;margin-top:auto;padding-top:6px}
  button{flex:1;font-family:var(--mono);font-size:11px;letter-spacing:.06em;padding:7px 4px;cursor:pointer;
         border:1px solid var(--outline);background:var(--surface-lowest);color:var(--on-surface)}
  button:hover{border-color:var(--on-surface)}
  button.pass{background:var(--cc0);border-color:var(--cc0);color:#fff}
  button.rej{color:var(--restricted);border-color:#dcc6c2}
  select{font-family:var(--mono);font-size:11px;padding:6px;border:1px solid var(--outline);background:#fff}
  .empty{padding:60px;text-align:center;color:var(--muted);font-family:var(--mono);font-size:12px}
  .hint{position:fixed;bottom:0;left:0;right:0;padding:8px 24px;background:var(--surface-lowest);
        border-top:1px solid var(--outline);font-family:var(--mono);font-size:10.5px;color:var(--muted)}
</style></head>
<body>
<header>
  <h1>核验工作台</h1>
  <div class="stats" id="stats">…</div>
  <div class="bar"><i id="bar"></i></div>
  <div class="filters" id="filters"></div>
</header>
<main id="grid"></main>
<div class="hint">每条都要打开 source_url 亲眼确认 CC0 / Public Domain 标识再点通过 —— 授权是逐张图片的事实，不做批量。</div>
<script>
const TOKEN = "__TOKEN__";
let items = __ITEMS__, counts = __COUNTS__;

const esc = s => (s ?? "").toString().replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

function renderStats(){
  const total = Object.values(counts).reduce((a,b)=>a+b,0);
  const v = counts.verified||0, r = counts.rejected||0;
  document.getElementById("stats").innerHTML =
    `共 <b>${total}</b> · 已核验 <b>${v}</b> · 拒绝 <b>${r}</b> · 待核 <b>${counts.pending||0}</b>`;
  document.getElementById("bar").style.width = (total ? (v/total*100) : 0).toFixed(1) + "%";
}
function renderFilters(){
  const regions = [...new Set(items.map(i => i.region))];
  document.getElementById("filters").innerHTML =
    `<a href="#" data-r="" class="${cur===""?"on":""}">全部</a>` +
    regions.map(r => `<a href="#" data-r="${r}" class="${cur===r?"on":""}">${r==="cn"?"中国":"西方"}</a>`).join("");
  document.querySelectorAll("#filters a").forEach(a=>a.onclick=e=>{e.preventDefault();cur=a.dataset.r;renderFilters();render();});
}

let cur = "";
function render(){
  const list = items.filter(i => !cur || i.region === cur);
  const grid = document.getElementById("grid");
  if(!list.length){ grid.innerHTML = `<div class="empty">这一批处理完了。刷新页面看下一批，或用 --limit 拉更多。</div>`; return; }
  grid.innerHTML = list.map(it => `
    <article data-id="${it.id}">
      <a class="thumb" href="${esc(it.source_url)}" target="_blank" rel="noopener">
        ${it.thumb
          ? `<img loading="lazy" referrerpolicy="no-referrer" src="${esc(it.thumb)}" alt=""
                 onerror="this.style.display='none';this.parentNode.dataset.nophoto=1">`
          : `<span class="ph">无图 · 点开来源核对</span>`}
      </a>
      <div class="body">
        <div class="artist">${esc(it.name_zh)} · ${esc(it.region==="cn"?"中国":"西方")} · ${esc(it.provider)} ${esc(it.provider_object_id)}</div>
        <h2 class="title">${esc(it.title_zh || it.title)}</h2>
        <div class="sub">${esc(it.title)}${it.date_display?" · "+esc(it.date_display):""}<br>${esc(it.holding||"")}</div>
        <div class="ev">${esc(it.license_evidence || it.license)}</div>
        <div class="acts">
          <select data-sel><option value="CC0">CC0</option><option value="PDM">PDM</option><option value="FAITHFUL_COPY">忠实副本</option></select>
          <button class="pass" data-act="verified">通过</button>
          <button class="rej" data-act="rejected">拒绝</button>
        </div>
      </div>
    </article>`).join("");

  grid.querySelectorAll("article").forEach(card => {
    const id = Number(card.dataset.id);
    card.querySelectorAll("button").forEach(btn => btn.onclick = async () => {
      const sel = card.querySelector("select").value;
      btn.disabled = true; btn.textContent = "…";
      const res = await fetch("/api/action", {
        method: "POST",
        headers: {"content-type": "application/json", "x-token": TOKEN},
        body: JSON.stringify({id, action: btn.dataset.act, license: sel})
      });
      if(!res.ok){ btn.disabled = false; btn.textContent = "失败"; return; }
      const data = await res.json();
      counts = data.counts;
      items = items.filter(i => i.id !== id);
      renderStats(); render();
    });
  });
}
renderStats(); renderFilters(); render();
</script>
</body></html>
"""


def thumb_url(provider: str, image_thumb: str | None, image_url: str | None) -> str | None:
    """缩略图别用原件：Met 的 /original/ 动辄几十 MB，换成 /web-large/（约 1200px）"""
    url = image_thumb or image_url
    if not url:
        return None
    if provider == "met" and "/original/" in url:
        return url.replace("/original/", "/web-large/")
    return url


def fetch(conn, status: str, limit: int) -> list[dict]:
    rows = conn.execute(SQL_LIST, (status, limit)).fetchall()
    for r in rows:
        r["thumb"] = thumb_url(r["provider"], r["image_thumb"], r["image_url"])
        r["fetched_at"] = None
    return rows


def counts(conn) -> dict:
    rows = conn.execute(SQL_COUNTS).fetchall()
    out = {"pending": 0, "verified": 0, "rejected": 0}
    for r in rows:
        out[r["verification_status"]] = r["n"]
    return out


def make_handler(dsn: str, token: str, limit: int):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):  # 安静一点
            if "/api/" in (args[0] if args else ""):
                super().log_message(fmt, *args)

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("content-type", ctype)
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path.startswith("/api/state"):
                with psycopg.connect(dsn, row_factory=dict_row) as conn:
                    self._send(200, json.dumps(counts(conn)).encode(), "application/json")
                return
            if self.path in ("/", "/index.html"):
                with psycopg.connect(dsn, row_factory=dict_row) as conn:
                    items = fetch(conn, "pending", limit)
                    cnt = counts(conn)
                html = (
                    PAGE.replace("__ITEMS__", json.dumps(items, ensure_ascii=False, default=str))
                    .replace("__COUNTS__", json.dumps(cnt))
                    .replace("__TOKEN__", token)
                )
                self._send(200, html.encode(), "text/html; charset=utf-8")
                return
            self._send(404, b"not found", "text/plain")

        def do_POST(self):
            if self.path != "/api/action":
                self._send(404, b"not found", "text/plain")
                return
            if self.headers.get("x-token") != token:
                self._send(403, b"bad token", "text/plain")
                return
            length = int(self.headers.get("content-length") or 0)
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
                image_id = int(payload["id"])
                action = payload["action"]
                license_ = payload.get("license")
            except Exception:
                self._send(400, b"bad request", "text/plain")
                return
            if action not in ("verified", "rejected"):
                self._send(400, b"bad action", "text/plain")
                return
            with psycopg.connect(dsn, row_factory=dict_row) as conn:
                conn.execute(
                    """
                    update artwork_image
                    set verification_status = %s,
                        license = case when %s = 'verified' then coalesce(%s, license) else license end,
                        verified_by = 'workbench', verified_at = now(), updated_at = now()
                    where id = %s
                    """,
                    (action, action, license_, image_id),
                )
                conn.commit()
                cnt = counts(conn)
            self._send(200, json.dumps({"ok": True, "counts": cnt}).encode(), "application/json")

    return Handler


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=DEFAULT_DSN)
    ap.add_argument("--port", type=int, default=8790)
    ap.add_argument("--limit", type=int, default=60, help="一次加载多少条待核验记录")
    args = ap.parse_args()

    token = secrets.token_urlsafe(12)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(args.dsn, token, args.limit))
    url = f"http://127.0.0.1:{args.port}/"
    print(f"核验工作台：{url}")
    print(f"（只监听 127.0.0.1，写完即停：Ctrl-C）")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n停止")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
