#!/usr/bin/env python3
"""content/artists.yaml + content/candidates/*.yaml → Postgres，幂等。

    .venv/bin/python tools/seed_db.py            # 导入/更新
    .venv/bin/python tools/seed_db.py --dry-run  # 只看会写什么

幂等键：artist.id、artwork.work_group + title、artwork_image (provider, provider_object_id)。

**人工核验不会被覆盖**：yaml 里 verification_status 仍是 pending 时，数据库里已有的
verified / rejected 保留原值；只有 yaml 明确写了 verified / rejected 才覆盖。
理由：核验是人工打开来源页做的判断，不能被一次重新抓取抹掉。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import yaml
import psycopg

ROOT = Path(__file__).resolve().parents[1]
ARTISTS = ROOT / "content" / "artists.yaml"
CANDIDATES = ROOT / "content" / "candidates"
DEFAULT_DSN = os.environ.get("DATABASE_URL", "postgresql://album:album@127.0.0.1:5433/album")

SLUG_RE = re.compile(r"[^a-z0-9]+")


def slug(text: str) -> str:
    return SLUG_RE.sub("-", (text or "").lower()).strip("-")[:60] or "untitled"


def work_group(artist_id: str, candidate: dict) -> str:
    """同一件作品跨馆归并用的键：优先用命中的目标作标题，否则退回作品标题"""
    hint = candidate.get("target_hint") or candidate.get("title") or ""
    return f"{artist_id}:{slug(hint)}"


def load_artists() -> list[dict]:
    doc = yaml.safe_load(ARTISTS.read_text(encoding="utf-8"))
    return doc["artists"]


def load_candidates() -> list[tuple[str, dict]]:
    """返回 [(artist_id, candidate)]，artist_id 取自文件名与文档内的 artist.id"""
    out: list[tuple[str, dict]] = []
    for path in sorted(CANDIDATES.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        artist_id = (doc.get("artist") or {}).get("id") or path.stem
        for cand in doc.get("candidates") or []:
            out.append((artist_id, cand))
    return out


UPSERT_ARTIST = """
insert into artist (id, name_zh, name_en, phase, region, note)
values (%(id)s, %(name_zh)s, %(name_en)s, %(phase)s, %(region)s, %(note)s)
on conflict (id) do update set
    name_zh = excluded.name_zh,
    name_en = excluded.name_en,
    phase   = excluded.phase,
    region  = excluded.region,
    note    = excluded.note,
    updated_at = now()
"""

FIND_ARTWORK = """
select id from artwork where artist_id = %(artist_id)s and work_group = %(work_group)s
  and title = %(title)s
"""

INSERT_ARTWORK = """
insert into artwork (artist_id, work_group, title, title_zh, date_display, medium, dimensions,
                     attribution_level, target_match, published)
values (%(artist_id)s, %(work_group)s, %(title)s, %(title_zh)s, %(date_display)s,
        %(medium)s, %(dimensions)s, %(attribution_level)s, %(target_match)s, true)
returning id
"""

UPDATE_ARTWORK = """
update artwork set
    title_zh = %(title_zh)s,
    date_display = %(date_display)s,
    medium = %(medium)s,
    dimensions = %(dimensions)s,
    attribution_level = %(attribution_level)s,
    target_match = %(target_match)s,
    updated_at = now()
where id = %(id)s
"""

UPSERT_IMAGE = """
insert into artwork_image (artwork_id, provider, provider_object_id, holding, accession_number,
                           license, license_evidence, source_url, image_url, image_thumb,
                           image_profile, credit_line, fetched_at, verification_status)
values (%(artwork_id)s, %(provider)s, %(provider_object_id)s, %(holding)s, %(accession_number)s,
        %(license)s, %(license_evidence)s, %(source_url)s, %(image_url)s, %(image_thumb)s,
        %(image_profile)s, %(credit_line)s, %(fetched_at)s, %(verification_status)s)
on conflict (provider, provider_object_id) do update set
    artwork_id       = excluded.artwork_id,
    holding          = excluded.holding,
    accession_number = excluded.accession_number,
    license          = excluded.license,
    license_evidence = excluded.license_evidence,
    source_url       = excluded.source_url,
    image_url        = coalesce(excluded.image_url, artwork_image.image_url),
    image_thumb      = coalesce(excluded.image_thumb, artwork_image.image_thumb),
    image_profile    = excluded.image_profile,
    credit_line      = excluded.credit_line,
    fetched_at       = excluded.fetched_at,
    -- 人工核验优先：yaml 里还是 pending 就不动数据库里已核过的结果
    verification_status = case
        when excluded.verification_status <> 'pending' then excluded.verification_status
        else artwork_image.verification_status
    end,
    updated_at = now()
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=DEFAULT_DSN)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    artists = load_artists()
    candidates = load_candidates()

    if args.dry_run:
        print(json.dumps({"artists": len(artists), "candidates": len(candidates)}, indent=2))
        by_artist: dict[str, int] = {}
        for artist_id, _ in candidates:
            by_artist[artist_id] = by_artist.get(artist_id, 0) + 1
        for artist_id, count in sorted(by_artist.items(), key=lambda kv: -kv[1]):
            print(f"  {artist_id:16s} {count}")
        return 0

    stats = {"artist": 0, "artwork_new": 0, "artwork_upd": 0, "image": 0, "skipped": 0}

    with psycopg.connect(args.dsn) as conn:
        with conn.transaction():
            for a in artists:
                conn.execute(
                    UPSERT_ARTIST,
                    {
                        "id": a["id"],
                        "name_zh": a["name_zh"],
                        "name_en": a.get("name_en"),
                        "phase": int(a.get("phase") or 1),
                        "region": a.get("region") or "cn",
                        "note": a.get("note"),
                    },
                )
                stats["artist"] += 1

            for artist_id, cand in candidates:
                provider = cand.get("provider")
                object_id = str(cand.get("provider_object_id") or "")
                if not provider or not object_id:
                    stats["skipped"] += 1
                    continue

                art = {
                    "artist_id": artist_id,
                    "work_group": work_group(artist_id, cand),
                    "title": cand.get("title") or "(untitled)",
                    "title_zh": cand.get("target_hint") if cand.get("target_match") == "full" else None,
                    "date_display": cand.get("date"),
                    "medium": cand.get("medium"),
                    "dimensions": cand.get("dimensions"),
                    "attribution_level": cand.get("attribution") or "unidentified_search_hit",
                    "target_match": cand.get("target_match"),
                }
                row = conn.execute(FIND_ARTWORK, art).fetchone()
                if row:
                    art["id"] = row[0]
                    conn.execute(UPDATE_ARTWORK, art)
                    artwork_id = row[0]
                    stats["artwork_upd"] += 1
                else:
                    artwork_id = conn.execute(INSERT_ARTWORK, art).fetchone()[0]
                    stats["artwork_new"] += 1

                conn.execute(
                    UPSERT_IMAGE,
                    {
                        "artwork_id": artwork_id,
                        "provider": provider,
                        "provider_object_id": object_id,
                        "holding": cand.get("holding"),
                        "accession_number": cand.get("accession_number"),
                        "license": cand.get("license") or "UNKNOWN",
                        "license_evidence": cand.get("license_evidence"),
                        "source_url": cand.get("source_url") or "",
                        "image_url": cand.get("image_url"),
                        "image_thumb": cand.get("image_thumb"),
                        "image_profile": cand.get("image_profile"),
                        "credit_line": cand.get("credit_line"),
                        "fetched_at": cand.get("fetched_at"),
                        "verification_status": cand.get("verification_status") or "pending",
                    },
                )
                stats["image"] += 1

    print(f"artist upsert: {stats['artist']}")
    print(f"artwork: 新增 {stats['artwork_new']} / 更新 {stats['artwork_upd']}")
    print(f"image upsert: {stats['image']}")
    if stats["skipped"]:
        print(f"跳过（缺 provider/provider_object_id）: {stats['skipped']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
