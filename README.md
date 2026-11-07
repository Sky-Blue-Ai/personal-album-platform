# personal-album-platform

古代艺术名人画展 —— Web + iOS + Android 三端。web 与客户端各一套 UI，客户端为 KMP + CMP。

- 产品文档（飞书）：https://my.feishu.cn/wiki/DrmFwwS1aifwjIksfPPc55hdnsf
- 架构方案：[`docs/architecture.md`](docs/architecture.md)
- 取源实测：[`docs/sourcing-findings.md`](docs/sourcing-findings.md)
- 设计令牌：[`docs/design-system.md`](docs/design-system.md)
- 内容与核验流程：[`docs/content-workflow.md`](docs/content-workflow.md)

## 当前状态

| 里程碑 | 状态 |
|---|---|
| 内容抓取（39 位艺术家 / 228 条候选） | ✅ 已跑通 |
| M0 仓库骨架 | 🟡 web 完成；`apps/mobile`、`services/api`、CI 未建 |
| M1 数据模型与发布门禁 | ✅ schema + 导入 + 门禁视图 + 导出（API 层未做） |
| M2 图片管线 | 🟡 只有下载 + 缩放，无瓦片/IIIF |
| M3 Web MVP | 🟡 首页 + 作品详情 + about，17 件演示图 |
| M4/M5/M6 客户端、长卷、收藏 | ⬜ 未开工（客户端需 macOS / 大内存机器） |

## 目录

| 路径 | 内容 |
|---|---|
| `content/artists.yaml` | 39 位艺术家清单（分期、地域、目标作品），内容即代码，改动走 PR |
| `content/candidates/` | 抓取产出的候选作品（含 license / source_url / credit / fetched_at） |
| `content/design/tokens.json` | 设计令牌唯一事实源（颜色/字阶/间距/授权语义色） |
| `tools/ingest/candidates.py` | 按艺术家抓 Met / CMA 候选，产出待核查清单 |
| `tools/build_design_tokens.py` | 令牌 → web `@theme` / Kotlin 常量 / 预览页 |
| `db/migrations/` | PostgreSQL schema，含门禁视图 `v_published_artworks` |
| `tools/db_migrate.py` / `seed_db.py` / `verify_image.py` / `export_web_content.py` | 迁移 / 导入 / 人工核验 / 导出 |
| `apps/web` | Next.js 15 + Tailwind v4 静态站 |
| `docs/architecture.md` | 三端架构、数据模型、图片管线、里程碑 |

## 快速开始

```bash
# 一次性：项目虚拟环境（系统 /usr/bin/python3 是 3.6，跑不了这些脚本）
python3.11+ -m venv .venv            # 需要 3.11 及以上解释器
.venv/bin/pip install pyyaml pillow "psycopg[binary]"

# 1) 内容侧：抓候选（Met 会限流封 IP，默认 1.2 req/s，响应落盘 content/.cache/）
.venv/bin/python tools/ingest/candidates.py --phase 1

# 2) 数据侧：起库 → 建表 → 导入 → 核验 → 导出
docker compose create db && docker compose start db   # 端口 5433（本机 3000/8080 已被占用）
.venv/bin/python tools/db_migrate.py
.venv/bin/python tools/seed_db.py
.venv/bin/python tools/verify_image.py --list-pending --limit 20
.venv/bin/python tools/verify_image.py met 36048 --license CC0 --by <你的名字> \
    --evidence "Met Open Access: object 36048 isPublicDomain=true"
.venv/bin/python tools/export_web_content.py          # 只导 verified；--demo 可本地预览全部

# 3) web
cd apps/web && npm install && npm run build
```

## 两条硬规矩

1. **授权是逐张图片的事实**，不是逐位艺术家的属性。`verification_status` 一律 `pending`，必须打开 `source_url` 看到 CC0 / PD 标识后人工改成 `verified`。
2. **`pending` 的图不进任何前台查询**。这条已经落到数据库视图 `v_published_artworks`（作品已上架 + 副本已核验 + 授权可公开），构建期的 `export_web_content.py` 只读这个视图——没有 verified 记录时它拒绝覆盖 `works.json`，前端不可能拿到未核验的图。
