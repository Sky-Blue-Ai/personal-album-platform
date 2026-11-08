#!/usr/bin/env python3
"""把候选缩略图落到本地 public/thumbs/，让演示站不依赖机构 CDN。

    .venv/bin/python tools/fetch_thumbs.py            # 只抓缺失的
    .venv/bin/python tools/fetch_thumbs.py --limit 20 # 先试 20 张
    .venv/bin/python tools/fetch_thumbs.py --force    # 全部重抓

注意：这是**演示缓存**，不是内容发布。生产环境图片由自家切片服务出，
不直连机构 CDN（见 docs/architecture.md「客户端不解析图片源站」）。

Met 的 /original/ 是几十 MB 的原件，一律降级到 /web-large/（约 1200px）。
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg
import requests
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "apps" / "web" / "public" / "thumbs"
DEFAULT_DSN = os.environ.get("DATABASE_URL", "postgresql://album:album@127.0.0.1:5433/album")

SQL = """
select provider, provider_object_id, image_thumb, image_url
from artwork_image
where coalesce(image_thumb, image_url) is not null
order by id
"""

HEADERS = {"user-agent": "Mozilla/5.0 (compatible; personal-album-platform/0.1; thumbnail cache)"}


def target_url(provider: str, thumb: str | None, url: str | None) -> str | None:
    src = thumb or url
    if not src:
        return None
    if provider == "met" and "/original/" in src:
        return src.replace("/original/", "/web-large/")
    return src


def file_for(provider: str, object_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in object_id)
    return OUT / f"{provider}-{safe}.jpg"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=DEFAULT_DSN)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--workers", type=int, default=5)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)

    with psycopg.connect(args.dsn, row_factory=dict_row) as conn:
        rows = conn.execute(SQL).fetchall()

    if args.limit:
        rows = rows[: args.limit]

    jobs = []
    for r in rows:
        url = target_url(r["provider"], r["image_thumb"], r["image_url"])
        if not url:
            continue
        dest = file_for(r["provider"], r["provider_object_id"])
        if dest.exists() and not args.force and dest.stat().st_size > 1024:
            continue
        jobs.append((url, dest))

    print(f"待抓取 {len(jobs)} / {len(rows)}")
    ok = failed = 0

    def one(job: tuple[str, Path]) -> bool:
        url, dest = job
        try:
            resp = requests.get(url, headers=HEADERS, timeout=45)
            if resp.status_code != 200 or len(resp.content) < 1024:
                print(f"  跳过 {resp.status_code} {len(resp.content)}B {url}", file=sys.stderr)
                return False
            tmp = dest.with_suffix(".part")
            tmp.write_bytes(resp.content)
            tmp.replace(dest)
            return True
        except Exception as exc:  # noqa: BLE001 - 单张失败不该中断整批
            print(f"  失败 {url} : {exc}", file=sys.stderr)
            return False

    start = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i, good in enumerate(pool.map(one, jobs), 1):
            if good:
                ok += 1
            else:
                failed += 1
            if i % 20 == 0:
                print(f"  {i}/{len(jobs)} … {time.time() - start:.0f}s")

    total = sum(1 for _ in OUT.glob("*.jpg"))
    size = sum(p.stat().st_size for p in OUT.glob("*.jpg")) / 1e6
    print(f"完成：成功 {ok} / 失败 {failed}；本地共 {total} 张，{size:.1f} MB")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
