# personal-album-platform

古代艺术名人画展 —— Web + iOS + Android 三端。web 与客户端各一套 UI，客户端为 KMP + CMP。

- 产品文档（飞书）：https://my.feishu.cn/wiki/DrmFwwS1aifwjIksfPPc55hdnsf
- 架构方案：[`docs/architecture.md`](docs/architecture.md)
- 取源实测：[`docs/sourcing-findings.md`](docs/sourcing-findings.md)

## 当前状态

仓库刚开始，M0 阶段：内容清单与抓取管线已跑通，代码骨架待定技术口径后落地（见架构文档 §9 的待定项）。

## 目录

| 路径 | 内容 |
|---|---|
| `content/artists.yaml` | 39 位艺术家清单（分期、地域、目标作品），内容即代码，改动走 PR |
| `content/candidates/` | 抓取产出的候选作品（含 license / source_url / credit / fetched_at） |
| `tools/ingest/candidates.py` | 按艺术家抓 Met / CMA 候选，产出待核查清单 |
| `docs/architecture.md` | 三端架构、数据模型、图片管线、里程碑 |
| `contracts/openapi.yaml` | 服务端与 web 的契约（待补） |

## 快速开始（内容侧）

```bash
python3 -m pip install pyyaml

# 第 1 期 20 位艺术家，Met + CMA
python3 tools/ingest/candidates.py --phase 1

# 只跑某几位，或只跑一个源
python3 tools/ingest/candidates.py --only fan-kuan ni-zan --rps 1
python3 tools/ingest/candidates.py --phase 1 --provider cma
```

产物：`content/candidates/<artist-id>.yaml` 与 `content/candidates/index.json`。

**Met 会限流封 IP**：默认 1.2 req/s、响应落盘到 `content/.cache/`；被封后等几分钟再跑，已有缓存不会重复请求。

## 两条硬规矩

1. **授权是逐张图片的事实**，不是逐位艺术家的属性。`verification_status` 一律 `pending`，必须打开 `source_url` 看到 CC0 / PD 标识后人工改成 `verified`。
2. **`pending` 的图不进任何前台查询**。这条最终要落到 DB 视图与 API policy 上，而不是靠流程文档。
