#!/usr/bin/env python3
"""按艺术家从 Met / CMA 开放接口取候选作品，产出带溯源字段的待核查清单。

产物：
    content/candidates/<artist-id>.yaml   每位艺术家的候选作品（image 级记录）
    content/candidates/index.json         汇总：每人候选数、目标命中情况

纪律（见 museum-open-data-sourcing skill）：
    * 授权是逐张图片的事实 —— 这里只输出候选，verification_status 一律 pending，
      必须人工打开 source_url 看到 CC0 / PD 标识后改成 verified 才算上架。
    * name 只用于检索，title 用机构元数据原文，不自己翻译。
    * 松检索的 total ≠ 归属该作者的件数，本脚本对 candidates 再做一次创作者字段过滤。

用法：
    python3 tools/ingest/candidates.py --phase 1
    python3 tools/ingest/candidates.py --only fan-kuan ni-zan --rps 1
    python3 tools/ingest/candidates.py --phase 1 --provider cma
"""
import argparse
import hashlib
import json
import pathlib
import random
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

try:
    import yaml
except ImportError:
    sys.exit("need pyyaml: pip install pyyaml")

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTENT = ROOT / "content"
OUT = CONTENT / "candidates"
CACHE = CONTENT / ".cache"
UA = {"User-Agent": "personal-album-ingest/1.0 (open-access metadata harvester)"}
TODAY = time.strftime("%Y-%m-%d")


class Blocked(Exception):
    """源站整站拒绝（403/429 连续触发）——不要当成「没有数据」。"""


class Fetcher:
    """带磁盘缓存 + 全局限速 + 退避的 GET。

    Met 对短时间内的批量请求会直接封 IP（403，且连 object detail 一起封），
    所以默认 2 req/s、连续 3 次 403/429 就停掉该源，避免把整轮任务拖死。
    """

    def __init__(self, rps=2.0, cache_ttl_days=7, use_cache=True):
        self.min_interval = 1.0 / rps
        self.cache_ttl = cache_ttl_days * 86400
        self.use_cache = use_cache
        self._last = 0.0
        self._fails = 0
        CACHE.mkdir(parents=True, exist_ok=True)

    def _cached(self, key):
        if not self.use_cache:
            return None
        p = CACHE / key
        if p.exists() and time.time() - p.stat().st_mtime < self.cache_ttl:
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                return None
        return None

    def get(self, url, timeout=25):
        key = hashlib.sha1(url.encode()).hexdigest() + ".json"
        hit = self._cached(key)
        if hit is not None:
            return hit

        # 全局限速
        wait = self.min_interval - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)
        self._last = time.time()

        last = None
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers=UA)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                self._fails = 0
                (CACHE / key).write_text(json.dumps(data), encoding="utf-8")
                return data
            except urllib.error.HTTPError as exc:
                last = exc
                if exc.code in (403, 429):
                    self._fails += 1
                    if self._fails >= 3:
                        raise Blocked(f"{exc.code} repeated — source is throttling this IP") from exc
                    time.sleep((2 ** attempt) * 2 + random.random())
                    continue
                if 500 <= exc.code < 600:
                    time.sleep((2 ** attempt) + random.random())
                    continue
                raise
            except Exception as exc:  # noqa: BLE001
                last = exc
                time.sleep((2 ** attempt) + random.random())
        if last is not None:
            raise last
        raise RuntimeError(f"gave up on {url}")


def norm(text):
    text = unicodedata.normalize("NFKD", (text or "")).lower()
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", text).strip()


def tokens(text):
    return {t for t in norm(text).split() if len(t) > 2}


def title_match(candidate_title, targets):
    """标题线索比对：返回 (level, target_en)。level ∈ full / partial / none"""
    ct = tokens(candidate_title)
    best = ("none", None)
    for t in targets or []:
        tt = tokens(t.get("en", ""))
        if not tt:
            continue
        hit = len(tt & ct) / len(tt)
        if hit >= 0.8:
            return ("full", t["en"])
        if hit >= 0.5:
            best = ("partial", t["en"])
    return best


def surname_of(name_en):
    toks = norm(name_en).split()
    return toks[-1] if toks else ""


# ---------------- Met ----------------
def met_candidates(f, artist, limit=25):
    try:
        s = f.get("https://collectionapi.metmuseum.org/public/collection/v1.1/search?"
                  + urllib.parse.urlencode({"q": artist["name_en"], "hasImages": "true",
                                            "isPublicDomain": "true", "limit": limit}))
    except Blocked as exc:
        raise
    except Exception as exc:  # noqa: BLE001
        return [], f"met search failed: {exc}"

    ids = (s.get("objectIDs") or [])[:limit]
    surname = surname_of(artist["name_en"])

    def detail(oid):
        try:
            return f.get(f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{oid}")
        except Blocked:
            raise
        except Exception:  # noqa: BLE001
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        objs = list(pool.map(detail, ids))

    out = []
    for o in objs:
        if not o or not o.get("isPublicDomain") or not o.get("primaryImage"):
            continue
        artist_field = norm(o.get("artistDisplayName", ""))
        title_field = norm(o.get("title", ""))
        # 中国书画大量标为 "Unidentified artist"，作品归属只体现在标题
        # （"…in the style of Fan Kuan" / "Landscape after Guo Xi"），
        # 只按 artistDisplayName 过滤会把真正想要的摹本全部丢掉。
        if surname and surname in artist_field:
            attribution = "primary"
        elif surname and surname in title_field:
            attribution = "copy_or_attributed"
        elif title_match(o.get("title"), artist.get("targets"))[0] != "none":
            attribution = "target_title_match"
        elif artist_field in ("", "unidentified artist", "unknown", "unknown artist"):
            attribution = "unidentified_search_hit"
        else:
            continue
        out.append({
            "provider": "met",
            "provider_object_id": str(o.get("objectID")),
            "artist_display": o.get("artistDisplayName"),
            "title": o.get("title"),
            "date": o.get("objectDate"),
            "medium": o.get("medium"),
            "dimensions": o.get("dimensions"),
            "department": o.get("department"),
            "holding": "The Metropolitan Museum of Art",
            "attribution": attribution,
            "license": "CC0",
            "license_evidence": f"Met Open Access: object {o.get('objectID')} isPublicDomain=true",
            "source_url": o.get("objectURL"),
            "image_url": o.get("primaryImage"),
            "image_profile": "fixed-jpeg, no IIIF",
            "credit_line": o.get("creditLine"),
            "fetched_at": TODAY,
            "verification_status": "pending",
        })
    return out, None


# ---------------- CMA ----------------
def cma_candidates(f, artist, limit=25):
    try:
        d = f.get("https://openaccess-api.clevelandart.org/api/artworks/?"
                  + urllib.parse.urlencode({"q": artist["name_en"], "cc0": 1,
                                            "has_image": 1, "limit": limit}))
    except Blocked:
        raise
    except Exception as exc:  # noqa: BLE001
        return [], f"cma search failed: {exc}"

    surname = surname_of(artist["name_en"])
    out = []
    for a in d.get("data", []):
        creators = a.get("creators") or []
        creator_names = " ".join(norm(c.get("description", "")) for c in creators)
        if surname and surname not in creator_names:
            continue
        if a.get("share_license_status") != "CC0":
            continue
        images = a.get("images") or {}
        full = (images.get("full") or {}).get("url")
        web = (images.get("web") or {}).get("url")
        if not full and not web:
            continue
        out.append({
            "provider": "cma",
            "provider_object_id": str(a.get("id")),
            "artist_display": (creators[0].get("description") if creators else None),
            "title": a.get("title"),
            "date": a.get("creation_date"),
            "medium": a.get("technique"),
            "dimensions": a.get("measurements"),
            "department": a.get("department"),
            "holding": "Cleveland Museum of Art",
            "accession_number": a.get("accession_number"),
            "license": "CC0",
            "license_evidence": f"CMA open access: share_license_status=CC0 (artwork {a.get('id')})",
            "source_url": a.get("url"),
            "image_url": full,
            "image_thumb": web,
            "image_profile": "full TIFF (huge) + web JPEG; tile on ingest",
            "credit_line": a.get("creditline"),
            "fetched_at": TODAY,
            "verification_status": "pending",
        })
    return out, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", type=int, choices=[1, 2, 3])
    ap.add_argument("--region", choices=["cn", "west"])
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--provider", choices=["both", "met", "cma"], default="both")
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--rps", type=float, default=2.0, help="全局请求速率（Met 建议 ≤2）")
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args()

    doc = yaml.safe_load((CONTENT / "artists.yaml").read_text(encoding="utf-8"))
    artists = doc["artists"]
    if args.phase:
        artists = [a for a in artists if a.get("phase") == args.phase]
    if args.region:
        artists = [a for a in artists if a.get("region") == args.region]
    if args.only:
        artists = [a for a in artists if a["id"] in set(args.only)]
    if not artists:
        sys.exit("no artist matched the filters")

    OUT.mkdir(parents=True, exist_ok=True)
    f = Fetcher(rps=args.rps, use_cache=not args.no_cache)
    index = []
    met_blocked = False

    for artist in artists:
        records, errors = [], []
        if args.provider in ("both", "met") and not met_blocked:
            try:
                recs, err = met_candidates(f, artist, args.limit)
                records += recs
                if err:
                    errors.append(err)
            except Blocked as exc:
                met_blocked = True
                errors.append(f"met BLOCKED: {exc}")
                print("!! Met 开始封禁本机 IP，本轮后续只取 CMA（已有结果仍有效）", file=sys.stderr)
        if args.provider in ("both", "cma"):
            try:
                recs, err = cma_candidates(f, artist, args.limit)
                records += recs
                if err:
                    errors.append(err)
            except Blocked as exc:
                errors.append(f"cma BLOCKED: {exc}")

        targets = artist.get("targets") or []

        # 增量合并：同一 (provider, provider_object_id) 覆盖，其余保留
        path = OUT / f"{artist['id']}.yaml"
        merged = {}
        if path.exists():
            try:
                old = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                for rec in old.get("candidates") or []:
                    merged[(rec.get("provider"), rec.get("provider_object_id"))] = rec
            except Exception:  # noqa: BLE001
                merged = {}
        for rec in records:
            merged[(rec.get("provider"), rec.get("provider_object_id"))] = rec
        records = list(merged.values())

        hits = {"full": [], "partial": []}
        for rec in records:
            level, target = title_match(rec.get("title"), targets)
            rec["target_match"] = level
            rec["target_hint"] = target
            if level != "none":
                hits[level].append(f"{rec['provider']}:{rec.get('title')}")

        payload = {
            "artist": {k: artist.get(k) for k in ("id", "name_zh", "name_en", "phase", "region")},
            "targets": targets,
            "generated_at": TODAY,
            "note": "verification_status 一律 pending：必须打开 source_url 看到 CC0/PD 标识后才可改为 verified",
            "errors": errors,
            "candidates": sorted(records, key=lambda r: ({"full": 0, "partial": 1}.get(r["target_match"], 2), r["provider"])),
        }
        (OUT / f"{artist['id']}.yaml").write_text(
            yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")

        index.append({
            "id": artist["id"],
            "name_zh": artist.get("name_zh"),
            "phase": artist.get("phase"),
            "region": artist.get("region"),
            "candidates": len(records),
            "by_provider": {
                "met": sum(1 for r in records if r["provider"] == "met"),
                "cma": sum(1 for r in records if r["provider"] == "cma"),
            },
            "target_full": hits["full"],
            "target_partial": hits["partial"],
            "errors": errors,
        })
        flag = "✅" if hits["full"] else ("△" if hits["partial"] else ("·" if records else "✗"))
        print(f"{flag} {artist['id']:<16} 候选 {len(records):>2}  "
              f"(met {index[-1]['by_provider']['met']}, cma {index[-1]['by_provider']['cma']})"
              + (f"  命中: {hits['full'][:2]}" if hits["full"] else ""))

    (OUT / "index.json").write_text(
        json.dumps({"generated_at": TODAY, "met_blocked": met_blocked, "artists": index},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    tot = sum(i["candidates"] for i in index)
    full = sum(1 for i in index if i["target_full"])
    print(f"\n合计：{len(index)} 位艺术家 / {tot} 条候选 / 目标作品完全命中 {full} 位 → {OUT}")
    if met_blocked:
        print("注意：本轮 Met 被限流封禁，结果只含 CMA，不代表 Met 无素材；隔一段时间 --provider met 复跑（有缓存不重复请求）")


if __name__ == "__main__":
    main()
