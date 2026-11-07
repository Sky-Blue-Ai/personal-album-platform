# 架构方案：Web + iOS + Android 三端

> 状态：草案（待产品口径确认）· 更新 2026-11-07
> 约束：客户端用 **KMP（Kotlin Multiplatform）+ CMP（Compose Multiplatform）**；web 与客户端各一套 UI。

## 0. 一句话

内容型产品，卖点在「高清可缩放」与「策展叙事」，不在功能复杂度。因此架构的重心是**内容管线 + 图片管线 + 署名合规**，而不是微服务。三端只共享「业务语义」（模型、授权规则、契约），UI 各写各的——这正好对上「两套 UI」的前提。

## 1. 仓库结构

```
personal-album-platform/
├─ apps/
│  ├─ web/                     # Next.js 15 · Tailwind · TanStack Query · OpenSeadragon
│  └─ mobile/                  # Gradle 多模块
│     ├─ shared/               # KMP：领域模型、License 枚举与署名规则、Ktor client、SQLDelight
│     ├─ composeApp/           # CMP：iOS + Android 共用 UI（composeApp 内含 iOS framework 产物）
│     ├─ androidApp/           # Android 壳
│     └─ iosApp/               # Xcode 工程壳（需 macOS 构建）
├─ services/
│  ├─ api/                     # Ktor：依赖 shared，模型/校验/序列化三端同一份
│  ├─ tiles/                   # Cantaloupe (IIIF Image API) + libvips 切片
│  └─ ingest/                  # Python：抓取 → 核查 → 切片 → 入库（见 tools/ingest）
├─ content/                    # 内容即代码：artists / artworks / exhibitions 的 YAML，走 PR review
├─ contracts/openapi.yaml      # web 与外部集成用的契约（服务端 CI 校验响应符合它）
├─ tools/ingest/               # 候选作品抓取与授权核查脚本
└─ docs/
```

**为什么后端也用 Kotlin**：选了 KMP，最大的红利不是「一套 UI」（你明确要两套），而是 `shared` 这一份领域模型能被客户端与服务端同时编译进去——授权枚举、署名拼接、展览编排规则只写一次，天然不会漂。若后端用 Node/Go，这层共享就退化成 OpenAPI + 两份 DTO。

代价：服务端人才池变窄。团队若不是 Kotlin 班底，就把 `services/api` 换成 NestJS，`shared` 只给客户端用，契约靠 OpenAPI 生成——其余设计不变。

## 2. 客户端（KMP + CMP）

| 关注点 | 选择 | 说明 |
|---|---|---|
| Kotlin / Gradle | 2.2.x / 8.x + version catalog | CMP 1.9.x 起 iOS 已 stable，可用于生产 |
| UI | Compose Multiplatform | iOS + Android 一套 composable，两端共用一套设计系统 |
| 导航 | `androidx.navigation` compose（KMP 支持）或 Decompose | 需要深链/状态恢复选前者，要更可控的返回栈选 Decompose |
| 网络 | Ktor client（Darwin / OkHttp / CIO 引擎） | 与 `shared` 同一套序列化 |
| 图片 | Coil 3（KMP，`coil-network-ktor3`） | 支持自定义 Fetcher，后面接瓦片 |
| 本地库 | SQLDelight | 收藏、浏览历史、离线包 |
| DI | Koin | KMP 友好 |
| 手势 | `detectTransformGestures` 自封装 PinchZoom | CMP 无现成 OSD 等价物，双指缩放要自己封 |

**高清 / 长卷三阶段**（别在 MVP 就硬啃瓦片）：

- **P0**：服务端给长边 4000px 的 WebP，Coil 加载 + 自封 PinchZoom。1–2 人日，第 1 期 20 件足够好看。
- **P1**：客户端接 IIIF 瓦片（512px tile，按缩放层级切图），用 Compose `Canvas` 画 tile 网格。这是**自制件**，估 3–5 人日，是长卷（《千里江山图》11.9m）能顺滑横滑的前提。
- **P2**：相邻 tile 预取 + 作品离线包（SQLDelight 记 manifest，文件落 cache）。

**iOS 构建**：本机（Linux）只能跑 `shared` 的 JVM 侧单测，iOS 产物必须在 macOS 上出。CI 用 GitHub Actions 的 `macos-latest`，否则每次 iOS 联调都要借机器。

## 3. Web（独立一套 UI）

- Next.js 15 App Router，列表/详情走 SSG + ISR：内容站的主流量入口是搜索引擎，客户端帮不上这个忙。
- OpenSeadragon 做高清缩放，比客户端省事一个数量级，先把「对照浏览」「长卷」的交互在 web 上验证，再移植到 CMP。
- 与客户端共用 `content/` 与 `contracts/openapi.yaml`，不共用组件。

> 如果将来判定 SEO 不重要（纯 App 产品），web 可以换成 Kotlin/Wasm + CMP 单套代码；现在不做，因为会牺牲索引能力。

## 4. 图片管线（决定产品上限）

**不直连源站**（实测依据见 `docs/sourcing-findings.md`）：

```
源站 API → 下载原件 → S3/R2 → libvips 切金字塔 → Cantaloupe 提供 IIIF → CDN → 前端 OSD / CMP tile viewer
```

- Met 只给固定尺寸 JPEG（长边 2000–3000px），没有 IIIF；
- CMA 的 `images.full.url` 是数百 MB TIFF，只能入库后切；
- AIC 原生 IIIF，但对机房 IP 回 Cloudflare 验证页；
- Wikimedia 作为补充源（全卷/孤本），需逐文件核「忠实副本」声明。

切片规范：sRGB、每层 512px tile、JPEG q85（长卷关键段给 q90）、manifest 存 `images/{imageId}/manifest.json`。

## 5. 数据模型（授权与溯源是一等字段）

```
artist(id, name_zh, name_en, dynasty|school, bio, ...)
artwork(id, artist_id, title_zh, title_original, date_text, medium, dimensions, holding, ...)
image(id, artwork_id, provider, provider_object_id, license, license_evidence,
      source_url, credit_line, fetched_at, verification_status, tileset_path, width, height)
collection(id, slug, title, kind)          -- 专题（长卷的时间性 / 肖像与自我 …）
exhibit(id, phase, title, curator_note)    -- 分期展览
collection_item(collection_id, artwork_id, position, section)
user / favorite(user_id, artwork_id | collection_id, created_at)
```

**发布门禁**：`image.verification_status = 'verified'` 才允许出现在任何前台查询；`pending` 只出现在后台核查列表。用 DB 视图 + 应用层 policy 双保险，把文档里「每张图单独核查」的纸面纪律变成系统约束。

## 6. 契约共享

- `contracts/openapi.yaml` 是 web 与外部集成的唯一契约；服务端 CI 用契约测试校验真实响应。
- 客户端不生成代码：直接用 `shared` 里的 DTO（与服务端同一份源码），不存在漂移。
- design token 放 `content/design/tokens.json`，构建时生成 Tailwind config 与 Kotlin `AppTheme` 常量——**两套 UI，一套 token**。

## 7. 里程碑与验收

| 阶段 | 内容 | 验收 |
|---|---|---|
| M0 | 仓库骨架、内容清单、抓取管线、数据模型 | `python3 tools/ingest/candidates.py --phase 1` 产出可核查清单；spec 定稿 |
| M1 | web 第 1 期 20 件：双线首页 → 艺术家 → 作品页（缩放 + 署名 + 来源） | 每件作品的 4 个溯源字段齐全且 `verified` |
| M2 | 客户端 M1 同等能力（KMP/CMP） | iOS/Android 实机通过；弱网下缩放不卡死 |
| M3 | 长卷专题（瓦片 + 横向 strip） | 《千里江山图》《清明上河图》可横滑至末段不糊 |
| M4 | 收藏 / 我的展厅 / 多端同步 | 同账号跨端一致 |

## 8. 风险

1. **Met 限流封 IP**（已实测）：批量抓取会 403，连 object detail 一起封。管线必须节流（≤2 req/s）+ 落盘缓存 + 离线数据集入库，且永不把抓取放在请求路径上。
2. **CMP 瓦片查看器是自制件**：预算 3–5 人日，别低估手势边界条件（长卷两端回弹、双击定位、旋转锁）。
3. **iOS 构建依赖 macOS CI**：第一天就配，别等到联调才想起。
4. **人力结构**：KMP 要求客户端全员 Kotlin（Android 同学迁移成本低，iOS 同学要熟悉 Gradle/CMP）；web 需要独立前端。**如果团队只有 1–2 人，先做 web，把内容与图片管线跑顺，客户端后置**。
5. **署名的法律细节**：CC0 不等于可以省略 credit line，机构对「自己拍摄的副本」另有条款，页脚要留机构原文。

## 9. 待定（阻塞下面所有排期）

- 产品内核：官方策展 / 个人展厅 / 官方 + 收藏
- 首发是否要账号体系与多端同步（建议：不要，本地收藏起步）
- 首发是否公开对外（决定 SEO、多语言、备案与合规投入）
