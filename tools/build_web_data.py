#!/usr/bin/env python3
"""把 content/candidates 里已抓到的候选，编成 web 端可用的演示数据。

做的事：
  1. 每位艺术家挑一条最佳候选（目标命中 > 直标作者 > 有图）
  2. 下载原图到 apps/web/public/art/ 并生成 full(2400) / thumb(640) 两档
  3. 写 apps/web/data/works.json（含 license / source_url / credit_line / fetched_at）

注意：产出仍是 pending 状态——演示用，不代表已核验。
"""
import json
import pathlib
import subprocess
import sys
import urllib.request

import yaml
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]
CAND = ROOT / "content" / "candidates"
OUT_IMG = ROOT / "apps" / "web" / "public" / "art"
OUT_DATA = ROOT / "apps" / "web" / "data"
UA = {"User-Agent": "Mozilla/5.0 (compatible; personal-album-build/1.0)"}


def score(rec):
    return (
        {"full": 2, "partial": 1}.get(rec.get("target_match"), 0),
        {"primary": 2, "target_title_match": 1}.get(rec.get("attribution"), 0),
        1 if rec.get("provider") == "met" else 0,
    )


def download(url, dest):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as resp:
        dest.write_bytes(resp.read())


def build_image(src_url, base, width=2400):
    tmp = base.with_suffix(".src")
    download(src_url, tmp)
    with Image.open(tmp) as im:
        im = im.convert("RGB")
        w, h = im.size
        if w > width:
            im = im.resize((width, round(h * width / w)), Image.LANCZOS)
        full_path = base.with_suffix(".jpg")
        im.save(full_path, "JPEG", quality=88, optimize=True, progressive=True)
        tw = 640
        thumb = im.resize((tw, round(im.size[1] * tw / im.size[0])), Image.LANCZOS)
        thumb_path = base.parent / (base.name + "-thumb.jpg")
        thumb.save(thumb_path, "JPEG", quality=82, optimize=True, progressive=True)
        size = im.size
    tmp.unlink(missing_ok=True)
    return full_path, thumb_path, size


def main():
    from concurrent.futures import ThreadPoolExecutor

    index = json.loads((CAND / "index.json").read_text(encoding="utf-8"))
    OUT_IMG.mkdir(parents=True, exist_ok=True)
    OUT_DATA.mkdir(parents=True, exist_ok=True)

    jobs = []
    for entry in index["artists"]:
        path = CAND / f"{entry['id']}.yaml"
        if not path.exists():
            continue
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        cands = [c for c in (doc.get("candidates") or []) if c.get("image_url")]
        if not cands:
            continue
        best = sorted(cands, key=score, reverse=True)[0]
        jobs.append((entry, doc, best))

    def make(job):
        entry, doc, best = job
        base = OUT_IMG / f"{entry['id']}"
        try:
            full, thumb, size = build_image(best["image_url"], base)
        except Exception as exc:  # noqa: BLE001
            print(f"skip {entry['id']}: image failed ({exc})", file=sys.stderr)
            return None
        targets = {t["en"]: t["zh"] for t in doc.get("targets") or []}
        target_zh = targets.get(best.get("target_hint")) if best.get("target_hint") else None
        print(f"+ {entry['id']:<16} {(best.get('title') or '')[:44]:<46} {size[0]}x{size[1]}")
        return {
            "id": entry["id"],
            "artist": {"name_zh": doc["artist"]["name_zh"], "name_en": doc["artist"]["name_en"]},
            "region": doc["artist"]["region"],
            "phase": doc["artist"]["phase"],
            "title_zh": target_zh,
            "title": best.get("title"),
            "date": best.get("date"),
            "medium": best.get("medium"),
            "dimensions": best.get("dimensions"),
            "holding": best.get("holding"),
            "attribution": best.get("attribution"),
            "target_match": best.get("target_match"),
            "license": best.get("license"),
            "license_evidence": best.get("license_evidence"),
            "source_url": best.get("source_url"),
            "credit_line": best.get("credit_line"),
            "fetched_at": best.get("fetched_at"),
            "verification_status": best.get("verification_status"),
            "image": {
                "src": f"/art/{full.name}",
                "thumb": f"/art/{thumb.name}",
                "width": size[0],
                "height": size[1],
            },
        }

    with ThreadPoolExecutor(max_workers=5) as pool:
        works = [w for w in pool.map(make, jobs) if w]

    (OUT_DATA / "works.json").write_text(
        json.dumps(works, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(works)} 件 → {OUT_DATA/'works.json'}")


if __name__ == "__main__":
    main()
