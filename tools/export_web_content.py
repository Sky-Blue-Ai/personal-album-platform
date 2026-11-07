#!/usr/bin/env python3
"""v_published_artworks → apps/web/data/works.json

默认只导出「已核验」的记录，这正是发布门禁在构建期的落点：
数据库里没有 verified 的副本，构建产物里就没有作品，前端不可能展示未核验的图。

    .venv/bin/python tools/export_web_content.py            # 只导 verified
    .venv/bin/python tools/export_web_content.py --demo     # 连同 pending 一起导（演示用）
    .venv/bin/python tools/export_web_content.py --stdout   # 打印不写盘

一条 verified 都没有时不覆盖 works.json，直接退出码 2，避免把线上内容清空。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "apps" / "web" / "data" / "works.json"
ART_DIR = ROOT / "apps" / "web" / "public" / "art"
DEFAULT_DSN = os.environ.get("DATABASE_URL", "postgresql://album:album@127.0.0.1:5433/album")

# 一件作品可能有多份已核验副本，前端只要一条：取分辨率最高的那份
SQL_VERIFIED = """
select * from (
    select distinct on (artwork_id) *
    from v_published_artworks
    order by artwork_id, coalesce(width, 0) desc, image_id
) t
order by phase, region, artist_id, artwork_id
"""

# --demo：不走门禁视图，放开 verification_status，只用于本地看页面
SQL_DEMO = """
select * from (
select distinct on (a.id) a.id as artwork_id, a.title, a.title_zh, a.date_display, a.medium, a.dimensions,
       a.attribution_level, a.target_match, a.work_group,
       ar.id as artist_id, ar.name_zh as artist_name_zh, ar.name_en as artist_name_en,
       ar.region, ar.phase,
       i.id as image_id, i.provider, i.provider_object_id, i.holding, i.accession_number,
       i.license, i.license_evidence, i.source_url, i.image_url, i.image_thumb,
       i.image_profile, i.credit_line, i.fetched_at, i.verification_status,
       i.width, i.height, i.tileset_path
from artwork a
join artist ar on ar.id = a.artist_id
join artwork_image i on i.artwork_id = a.id
where a.published
order by a.id, (i.verification_status = 'verified') desc, coalesce(i.width, 0) desc, i.id
) t
order by phase, region, artist_id, artwork_id
"""


def local_image(artist_id: str) -> dict | None:
    """web 的演示图按 artist_id 命名，存在就带上；不存在就留给 image_url"""
    full = ART_DIR / f"{artist_id}.jpg"
    thumb = ART_DIR / f"{artist_id}-thumb.jpg"
    if not full.exists():
        return None
    return {"src": f"/art/{full.name}", "thumb": f"/art/{thumb.name}" if thumb.exists() else f"/art/{full.name}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=DEFAULT_DSN)
    ap.add_argument("--demo", action="store_true", help="包含未核验记录（演示用，不可上线）")
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()

    with psycopg.connect(args.dsn, row_factory=psycopg.rows.dict_row) as conn:
        rows = conn.execute(SQL_DEMO if args.demo else SQL_VERIFIED).fetchall()

    works = []
    for r in rows:
        art_id = f"{r['artist_id']}-{r['artwork_id']}"
        img = local_image(r["artist_id"])
        works.append(
            {
                "id": art_id,
                "artist": {"name_zh": r["artist_name_zh"], "name_en": r["artist_name_en"]},
                "region": r["region"],
                "phase": r["phase"],
                "title_zh": r["title_zh"],
                "title": r["title"],
                "date": r["date_display"],
                "medium": r["medium"],
                "dimensions": r["dimensions"],
                "holding": r["holding"],
                "attribution": r["attribution_level"],
                "target_match": r["target_match"],
                "license": r["license"],
                "license_evidence": r["license_evidence"],
                "source_url": r["source_url"],
                "credit_line": r["credit_line"],
                "fetched_at": r["fetched_at"].isoformat() if r["fetched_at"] else None,
                "verification_status": r["verification_status"],
                "provider": r["provider"],
                "provider_object_id": r["provider_object_id"],
                "image": img or {"src": r["image_url"], "thumb": r["image_thumb"] or r["image_url"]},
            }
        )

    verified = sum(1 for w in works if w["verification_status"] == "verified")
    payload = json.dumps(works, ensure_ascii=False, indent=2)

    if args.stdout:
        print(payload)
        print(f"\n# {len(works)} 件（verified {verified}）", file=sys.stderr)
        return 0

    if not works:
        print(
            "门禁生效：v_published_artworks 里没有任何已核验记录，未覆盖 works.json。\n"
            "  先把某个副本改成 verified（见 docs/content-workflow.md），或用 --demo 本地预览。",
            file=sys.stderr,
        )
        return 2

    if not args.demo and verified == 0:
        print("没有任何 verified 记录，拒绝覆盖 works.json", file=sys.stderr)
        return 2

    OUT.write_text(payload + "\n", encoding="utf-8")
    mode = "演示模式（含未核验）" if args.demo else "已核验"
    print(f"{len(works)} 件 → {OUT.relative_to(ROOT)}  [{mode}，verified {verified}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
