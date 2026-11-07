#!/usr/bin/env python3
"""按文件名顺序执行 db/migrations/*.sql，已执行过的跳过。

    docker compose up -d db
    .venv/bin/python tools/db_migrate.py [--dsn postgresql://...] [--status]

迁移记录在 schema_migrations 表；每个文件在自己的事务里跑，失败整体回滚。
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "db" / "migrations"
DEFAULT_DSN = os.environ.get("DATABASE_URL", "postgresql://album:album@127.0.0.1:5433/album")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=DEFAULT_DSN)
    ap.add_argument("--status", action="store_true", help="只打印状态，不执行")
    args = ap.parse_args()

    files = sorted(MIGRATIONS.glob("*.sql"))
    if not files:
        print(f"没有迁移文件：{MIGRATIONS}", file=sys.stderr)
        return 1

    with psycopg.connect(args.dsn, autocommit=False) as conn:
        conn.execute(
            """
            create table if not exists schema_migrations (
                version    text primary key,
                checksum   text not null,
                applied_at timestamptz not null default now()
            )
            """
        )
        conn.commit()

        applied = {
            row[0]: row[1]
            for row in conn.execute("select version, checksum from schema_migrations").fetchall()
        }

        if args.status:
            for f in files:
                mark = "applied" if f.name in applied else "pending"
                print(f"{mark:8s} {f.name}")
            return 0

        ran = 0
        for f in files:
            sql = f.read_text(encoding="utf-8")
            checksum = hashlib.sha256(sql.encode()).hexdigest()[:16]
            if f.name in applied:
                if applied[f.name] != checksum:
                    print(
                        f"警告：{f.name} 内容已变更（数据库记录 {applied[f.name]}，文件 {checksum}）。"
                        "已执行的迁移不要改，另建新文件。",
                        file=sys.stderr,
                    )
                continue
            try:
                conn.execute(sql)
                conn.execute(
                    "insert into schema_migrations (version, checksum) values (%s, %s)",
                    (f.name, checksum),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                print(f"迁移失败：{f.name}", file=sys.stderr)
                raise
            print(f"applied  {f.name}")
            ran += 1

        print(f"完成：{ran} 个新迁移，{len(applied) + ran}/{len(files)} 已应用")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
