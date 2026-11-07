# 内容与授权核验流程

从「抓到的候选」到「能上线的作品」只有一条路，中间那一步必须是人做的。

```
content/artists.yaml ──┐
content/candidates/*.yaml ─┴→ tools/seed_db.py → Postgres
                                                   │
                                    人工核验（verify_image.py）
                                                   │
                                    视图 v_published_artworks
                                                   │
                                    tools/export_web_content.py
                                                   │
                                       apps/web/data/works.json
                                                   │
                                          npm run build → out/
```

## 1. 起库与建表

```bash
docker compose create db && docker compose start db   # 5433（本机 3000/8080 已被其他服务占用）
.venv/bin/python tools/db_migrate.py --status         # 看哪些迁移待执行
.venv/bin/python tools/db_migrate.py
```

迁移文件在 `db/migrations/`，按文件名顺序执行，记录在 `schema_migrations`。**已执行的文件不要再改**——改了会打印 checksum 警告，正确做法是新加一个 `002_xxx.sql`。

## 2. 导入候选

```bash
.venv/bin/python tools/seed_db.py --dry-run   # 先看会写多少
.venv/bin/python tools/seed_db.py
```

幂等键：

- `artist.id`
- `artwork`：`(artist_id, work_group, title)`，`work_group` = 艺术家 + 目标作品标题的 slug，用于后续把跨馆的同一件作品归并
- `artwork_image`：`(provider, provider_object_id)`

**重新导入不会抹掉人工核验**：yaml 里 `verification_status` 还是 `pending` 时，数据库里已有的 `verified` / `rejected` 保持原值；只有 yaml 明确写了 `verified` / `rejected` 才覆盖。（判断是人工打开来源页做的，不能被一次重抓冲掉。）

## 3. 人工核验

### 3.1 工作台（推荐）

```bash
.venv/bin/python tools/review_workbench.py            # http://127.0.0.1:8790
.venv/bin/python tools/review_workbench.py --limit 24 # 一次加载多少条
```

页面把待核验候选铺成卡片：缩略图、作者、材质年代、馆藏、`source_url` 直链、原始授权依据。
点「通过」就把该副本写成 `verified`（下拉框选 CC0 / PDM / 忠实副本），点「拒绝」写 `rejected`，
卡片即时消失、顶部计数与进度条同步。

刻意**没有批量通过**：授权是逐张图片的事实，批量就是给自己埋雷。左上角可按中西分区筛。

缩略图用的是 `web-large`（Met 的 `/original/` 动辄几十 MB，24 张就能把浏览器拖死）；
图源加载不出来时会显示「图源未加载 · 点开核对授权」，不影响判断。

### 3.2 命令行（单条、脚本化）

```bash
.venv/bin/python tools/verify_image.py --list-pending --limit 20
# 打开打印出来的 source_url，确认页面上的 CC0 / Public Domain 标识，然后：
.venv/bin/python tools/verify_image.py met 36048 --license CC0 --by chenxiang \
    --evidence "Met Open Access: object 36048 isPublicDomain=true"
# 不合格：
.venv/bin/python tools/verify_image.py cma 160137 --reject --reason "来源页无授权标识"
# 改错了退回：
.venv/bin/python tools/verify_image.py met 36048 --reset
```

`--evidence` 请填来源页上**原样看到的授权依据**，这句话以后是唯一的追溯凭证。

## 4. 导出并构建

```bash
.venv/bin/python tools/export_web_content.py            # 只导 verified（发布口径）
.venv/bin/python tools/export_web_content.py --demo     # 连同 pending 一起导（本地预览，不可上线）
.venv/bin/python tools/export_web_content.py --stdout   # 打印不写盘
cd apps/web && npm run build
```

一条 verified 都没有时，导出脚本**拒绝覆盖** `works.json` 并返回退出码 2——空内容比假内容安全，也让"忘记核验"在构建期就暴露。

## 5. 门禁规则

`v_published_artworks` 是前台唯一的内容来源，三个条件同时满足才出现：

1. `artwork.published = true`（运营排期上架）
2. `artwork_image.verification_status = 'verified'`（人工核验过）
3. `artwork_image.license in ('CC0','PDM','FAITHFUL_COPY')`（授权类型可公开）

一件作品有多份已核验副本时，导出只取分辨率最高的一条（`distinct on (artwork_id)`）。

## 已跑的验收记录（2026-11-07）

| 检查 | 结果 |
|---|---|
| 迁移 | `001_init.sql` applied，artist/artwork/artwork_image/schema_migrations 四张表 |
| 导入 | 39 位艺术家、228 条候选 → 220 件作品、228 个图像副本 |
| 幂等 | 第二次 `seed_db.py`：新增 0，更新 228 |
| 门禁（未核验） | 视图 0 行；`export_web_content.py` 退出码 2，`works.json` sha256 未变 |
| 门禁（核验一条） | 视图 1 行，导出该条（Met 36048 张择端《清明上河图》） |
| 人工核验抗覆盖 | 重新 seed 后该条仍为 `verified` / `by=chenxiang` |
| 多副本去重 | 同一作品 2 条 verified → 视图 2 行，导出 1 行 |
| 核验工作台（新增） | 页面点「通过」→ 数据库 `verified` / `license=CC0` / `by=workbench` → 视图 1 行 → 导出一致，计数 228→227、卡片 24→23 |

## 尚未做

- **核验工作台**：现在是 CLI + 手工打开链接，228 条一条条点还行，上千条就需要带缩略图、可批量勾选的本地页面。
- **API 层**：`services/api`（Ktor）未建，web 目前靠构建期导出的 JSON。等有能跑 Gradle 的机器再接。
- **瓦片**：`tools/build_tiles.py` 未写，`artwork_image.width/height/tileset_path` 字段已留好。
