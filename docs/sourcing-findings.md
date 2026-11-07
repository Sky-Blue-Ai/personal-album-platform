# 取源实测记录（2026-11-07）

结论都来自真实请求，不是转述文档。跑法见 `tools/ingest/candidates.py`。

## 1. 覆盖度（Met PD + CMA CC0，按艺术家名松检索）

39 位艺术家里，36 位至少能拿到候选；**第 1 期 20 位里 17 位有候选**。

真·无源（必须走 Wikimedia Commons 兜底）：

| 艺术家 | 目标作品 | 状况 |
|---|---|---|
| 展子虔 | 游春图 | Met/CMA 均 0 |
| 王希孟 | 千里江山图 | Met/CMA 均 0 |
| 委拉斯开兹 | 宫娥 | Met 无 PD 有图件（原作在普拉多） |

## 2. 松检索的 total ≠ 归属该作者的件数

按艺术家名检索得到的是「名字出现过的对象」，含**后人摹本、临仿、"in the style of"、以及同名异人**。

例：`q=Ni Zan & cc0=1 & has_image=1` 的 total 是 13，但创作者字段真正归属倪瓒的只有 2 件，其余是后人临仿。文档里「不以艺术家为单位假设开放」这条纪律，在数据层就是「检索命中 ≠ 归属」。

## 3. Met 的中国书画大多标为 “Unidentified artist”

这是最影响方案的一条：

- 张择端《清明上河图》在 Met 是 object **36048** `Spring Festival on the River`，`artistDisplayName` 却是 `Unidentified artist`；
- 顾恺之相关件同样匿名，归属只体现在标题（`in the style of …` / `after …`）；
- 郭熙 `Old Trees, Level Distance`（39668）是少数直标作者的。

后果：**只按 artistDisplayName 过滤会把中国区最要紧的摹本全部丢掉**。管线改为四级归属标注：
`primary`（直标作者）/ `copy_or_attributed`（标题含作者名）/ `target_title_match`（标题命中目标作）/ `unidentified_search_hit`（匿名检索命中，待人工判断）。

## 4. Met 对批量请求直接封 IP

- 并发 8 抓 ~500 个 detail 请求后，整站 403，**连 object detail 一起封**，`curl` 换 UA 也无效；
- 封禁持续约 3–5 分钟，之后自动恢复；
- 复跑时降到 1–1.2 req/s 的串行速率，约 100–150 个请求后再次触发。

处置（已写进脚本）：全局限速 ≤1.2 req/s、三次 403 即停掉该源并明确报错、**所有响应落盘缓存**（`content/.cache/`）避免重复请求；结论性的元数据（objectID → 图片/署名）应落库，永不把抓取放在请求路径上。

## 5. 图片能力差异（决定必须自建切片）

| 源 | 图片形态 | IIIF | 备注 |
|---|---|---|---|
| Met | 固定尺寸 JPEG，长边约 2000–3000px | ❌ | 高清缩放只能自己切 |
| CMA | `images.full.url` 是数百 MB TIFF | ❌（原始件） | 列表用 `images.web.url` |
| AIC | 原生 IIIF `/iiif/2/<id>/full/843,/0/default.jpg` | ✅ | 对机房 IP 回 Cloudflare 403 |
| Wikimedia | 原图 + `Special:FilePath?width=` | 部分 | 需逐文件核「忠实副本」声明 |
| Rijksmuseum | `webImage.url` | ❌ | 需 API key（伦勃朗/维米尔/哈尔斯最厚） |

## 6. 标题匹配是线索，不是结论

脚本用词重叠做 `target_match` 初筛，噪声明显：米开朗基罗被命中成 *The Young David Playing the Harp*（另一件作品）、梵高命中的是自画像背面。**命中只用于排序**，最终以人工打开 `source_url` 看到 CC0 / PD 标识为准——即 `verification_status: pending → verified`。
