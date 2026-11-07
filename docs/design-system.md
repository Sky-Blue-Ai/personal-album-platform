# 设计系统与令牌（Design Tokens）

本文件说明 `content/design/tokens.json` 这套令牌的来源、约束与消费方式。**改设计先改 tokens.json，再跑生成器，不要手改产物。**

## 1. 来源与取舍

令牌取自 `design.html`（Stitch 生成，Material 3 灰阶 + Bodoni Moda / Inter，页面标题 *Lumière Archive*）。那份稿子只能当"气质与信息架构"的参考，代码不能直接搬，原因有三条，都是实测过的：

| 问题 | 现状 | 本仓库的处理 |
|---|---|---|
| `cdn.tailwindcss.com` | 浏览器端即时编译，官方明确不用于生产 | 改成本地 Tailwind v4 + PostCSS，令牌走 `@theme` |
| 字体没有中文字形 | 全站只声明 Inter / Bodoni Moda，中文实际落到系统字体；无 CJK 字体的机器直接显示方框 | `font.display/serif/sans` 三条中文优先的字体栈，见第 3 节 |
| Material Symbols 是合字图标 | 字体没加载时按钮上直接露出 `manage_search`、`bookmark_add` 文字 | 图标一律内联 SVG，不依赖图标字体 |

另外两处主动修正：

- **正文最小字号**从 11px 提到 13px（`body-sm`），次级文字色用 `#5f5e5e` 而非 `#858383`，对比度从 3.2:1 提到 6.1:1。
- **补了语义色**：原稿纯灰阶，`CC0 / 待核验 / 受限` 三种授权状态在作品卡上肉眼不可分。现在这三种徽标是**全站唯一允许用彩色的地方**，其余保持灰阶。

## 2. 文件与生成链

```
content/design/tokens.json                 ← 唯一事实源（手改这里）
        │  python3 tools/build_design_tokens.py
        ├─→ apps/web/app/tokens.css        Tailwind v4 @theme（web 唯一入口，globals.css 里 @import）
        ├─→ content/design/generated/DesignTokens.kt   纯 Kotlin 常量（KMP / Compose / 服务端都能引用）
        ├─→ content/design/preview/tokens.css           纯 :root CSS（非 Tailwind 场景、静态原型）
        └─→ content/design/preview/tokens.html          令牌预览页（人工核对用，直接浏览器打开）
```

- `@theme static` 是刻意选的：默认情况下 Tailwind 只输出被 utility 用到过的变量，手写 CSS 里 `var(--spacing-lg)` 会拿不到值。`static` 保证全部令牌都进产物（当前 139 个变量）。
- `tokens.css` 里是 `@theme`（Tailwind 的 at-rule），**浏览器不认**，所以预览页和静态原型用 `preview/tokens.css` 那份等价的 `:root`。
- 生成物带"勿手改"头注释。`python3 tools/build_design_tokens.py --check` 只校验不写盘，返回码 1 = 产物与 tokens.json 不同步，适合放 CI。
- 生成器落地时会校验 Kotlin 产物（数字开头的标识符、`4f` 这种非法浮点字面量），本机没有 `kotlinc`，所以这层是文本级守门，不是编译验证。
- 原始参考稿留了一份在 `content/design/reference/design.html`（不参与构建，只用于对照）。
- `apps/web` 里 `npm run tokens` 生成、`npm run tokens:check` 校验、`prebuild` 自动生成（所以 `npm run build` 永远拿到最新令牌）。

## 3. 字体方案

| 角色 | 令牌 | 字体栈 | 用途 |
|---|---|---|---|
| display | `--font-display` | Bodoni Moda → Noto Serif SC → Songti SC → serif | 首页大标题、展览名，允许超大到 4.5rem |
| serif | `--font-serif` | Noto Serif SC → Source Han Serif SC → Songti SC → Georgia | 中文标题（域名/章节/作品名），正文里的标题 |
| sans | `--font-sans` | Inter → Noto Sans SC → PingFang SC → system-ui | **正文默认**，中文正文用思源黑体 |
| mono | `--font-mono` | JetBrains Mono → SF Mono → ui-monospace | 编号、年代区间、授权标识、元数据 |

要点：

- 西文与中文配对，`font-family` 里**必须显式列出中文字体**，否则中文会退到浏览器默认无衬线，标题的排版节奏全丢。
- 中文正文行高 1.7–1.75（`body-md/body-lg`），西文 1.6 会显得挤；这是分开定义 `font` 与 `type` 的原因。
- 生产环境建议自托管思源（Noto Serif SC / Noto Sans SC 的 woff2 子集），别依赖 Google Fonts 的国内可达性；本地服务缺失时字体栈会退到 PingFang / 宋体，不会出方框。移动端 Compose 侧把同样的 ttf 打进 `composeApp` 的资源目录。

## 4. 颜色与授权语义

灰阶骨（`surface` / `on-surface` / `outline`）直接来自 design.html，`accent`（`#9c3327` 朱红）沿用原实现，用来做链接、分隔线强调。

**授权三态**（`--color-license-*`，全站唯一彩色的地方）：

| 令牌 | 值 | 含义 | 用在哪 |
|---|---|---|---|
| `license-cc0` | `#2f6b4f` | 已核验 CC0 / PDM / 忠实摄影副本 | 作品卡与详情页的授权徽标 |
| `license-pending` | `#8a6a1f` | 候选记录，待人工点开来源页核验 | 后台列表、`verification_status: pending` |
| `license-restricted` | `#7a1f16` | 受限或不开放，前台不得展示原图 | 拦截提示、下架列表 |

这和"授权状态是发布门禁"是同一条规则的两种落法：数据库/视图层面拦，UI 层面必须让运营一眼看出差异。

对比度（WCAG AA）实测：正文 `16.3:1`，次级正文 `8.9:1`，muted `6.1:1`，accent `6.8:1`；三种徽标白字分别 `6.3:1` / `5.1:1` / `10.3:1`。`on-surface-disabled` 只有 `3.6:1`，仅用于禁用态装饰，不承载信息。

## 5. 两端怎么用

**Web（Tailwind v4）**

```css
/* apps/web/app/globals.css 顶部 */
@import "tailwindcss";
@import "./tokens.css";
```

```tsx
<h2 className="font-serif text-headline-md text-on-surface">作品名</h2>
<p className="text-body-md text-on-surface-variant">说明文字</p>
<span className="text-label-sm uppercase text-on-surface-muted">CC0</span>
```

现存的旧变量（`--paper` / `--ink` / `--line` / `--accent` / `--max`）保留成别名，值指向令牌，页面不用改结构就能换调性。

**KMP / Compose（模块尚未落地时的用法）**

```kotlin
// color: Long → Compose Color
Color(DesignTokens.color.surface)
// type: px → sp，多倍行高直接乘
TextStyle(fontSize = DesignTokens.type.bodyMd.sizePx.sp,
          lineHeight = (DesignTokens.type.bodyMd.sizePx * DesignTokens.type.bodyMd.lineHeightMultiplier).sp,
          letterSpacing = DesignTokens.type.bodyMd.letterSpacingEm.em,
          fontWeight = FontWeight(DesignTokens.type.bodyMd.weight))
```

`DesignTokens.kt` 刻意不依赖 `androidx.compose`：`shared`、`services/api` 也能编译，等 `apps/mobile` 骨架起好后再加一层 `AppTheme.kt` 做映射（`MaterialTheme.typography` / `lightColorScheme`），令牌本身不用改。

## 6. 未做 / 待办

- `apps/mobile` 还没建，`AppTheme.kt` 的 Compose 映射层等骨架落地再写。
- 令牌目前只有 light 版；design.html 的 `darkMode: "class"` 只是开关，没有定义暗色值，需要真做时再补第二套 surface。
- 页面级重做（四维分类矩阵、作品卡、检索 chips）属于设计稿的另一档工作，不在"令牌对齐"范围内。
