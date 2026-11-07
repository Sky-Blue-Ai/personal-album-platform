#!/usr/bin/env python3
"""人工核验入口：把某个副本标成 verified / rejected / pending。

核验是人工动作，脚本只负责记录判断与依据，不替人做判断：

    # 打开 source_url 看到 CC0 标识后
    .venv/bin/python tools/verify_image.py met 36048 --license CC0 \
        --evidence "Met Open Access: object 36048 isPublicDomain=true" --by chenxiang

    .venv/bin/python tools/verify_image.py cma 160137 --reject --reason "来源页无授权标识"
    .venv/bin/python tools/verify_image.py --list-pending --limit 20
"""

from __future__ import annotations

import argparse
import os
import sys

import psycopg

DEFAULT_DSN = os.environ.get("DATABASE_URL", "postgresql://album:album@127.0.0.1:5433/album")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("provider", nargs="?", help="met / cma / wikimedia ...")
    ap.add_argument("object_id", nargs="?", help="provider 侧的对象 id")
    ap.add_argument("--license", dest="license_", help="CC0 / PDM / FAITHFUL_COPY")
    ap.add_argument("--evidence", help="来源页上看到的授权依据原文")
    ap.add_argument("--by", help="核验人")
    ap.add_argument("--reject", action="store_true", help="标成 rejected")
    ap.add_argument("--reason", help="reject 的原因")
    ap.add_argument("--reset", action="store_true", help="退回 pending")
    ap.add_argument("--list-pending", action="store_true")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--dsn", default=DEFAULT_DSN)
    args = ap.parse_args()

    with psycopg.connect(args.dsn, row_factory=psycopg.rows.dict_row) as conn:
        if args.list_pending:
            rows = conn.execute(
                """
                select i.provider, i.provider_object_id, i.license, a.title, ar.name_zh, i.source_url
                from artwork_image i
                join artwork a on a.id = i.artwork_id
                join artist ar on ar.id = a.artist_id
                where i.verification_status = 'pending'
                order by ar.phase, ar.region, ar.id
                limit %s
                """,
                (args.limit,),
            ).fetchall()
            print(f"待核验（前 {len(rows)} 条）:")
            for r in rows:
                print(f"  {r['provider']:9s} {r['provider_object_id']:>8s}  {r['name_zh'] or '':8s} "
                      f"{(r['title'] or '')[:38]:38s} {r['source_url']}")
            return 0

        if not args.provider or not args.object_id:
            ap.error("要指定 provider 和 object_id，或用 --list-pending")

        if args.reject:
            row = conn.execute(
                """
                update artwork_image
                set verification_status = 'rejected',
                    license_evidence = coalesce(%s, license_evidence),
                    verified_by = %s, verified_at = now(), updated_at = now()
                where provider = %s and provider_object_id = %s
                returning id
                """,
                (args.reason, args.by, args.provider, args.object_id),
            ).fetchone()
        elif args.reset:
            row = conn.execute(
                """
                update artwork_image
                set verification_status = 'pending', verified_by = null, verified_at = null, updated_at = now()
                where provider = %s and provider_object_id = %s
                returning id
                """,
                (args.provider, args.object_id),
            ).fetchone()
        else:
            row = conn.execute(
                """
                update artwork_image
                set verification_status = 'verified',
                    license = coalesce(%s, license),
                    license_evidence = coalesce(%s, license_evidence),
                    verified_by = %s, verified_at = now(), updated_at = now()
                where provider = %s and provider_object_id = %s
                returning id
                """,
                (args.license_, args.evidence, args.by, args.provider, args.object_id),
            ).fetchone()

        if not row:
            print(f"没找到 {args.provider}/{args.object_id}", file=sys.stderr)
            return 1
        conn.commit()

        status = "pending" if args.reset else ("rejected" if args.reject else "verified")
        print(f"{args.provider}/{args.object_id} → {status}")

        published = conn.execute(
            """
            select count(*) from v_published_artworks v
            join artwork_image i on i.id = v.image_id
            where i.provider = %s and i.provider_object_id = %s
            """,
            (args.provider, args.object_id),
        ).fetchone()["count"]
        print(f"该副本现在{'会' if published else '不会'}出现在发布视图里")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
