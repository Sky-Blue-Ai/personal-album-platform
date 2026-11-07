#!/usr/bin/env python3
"""content/design/tokens.json → web (Tailwind v4 @theme) + Kotlin 常量 + 预览页。

单一事实源是 tokens.json；本脚本只做生成，不要手改产物。

    python3 tools/build_design_tokens.py            # 全量生成
    python3 tools/build_design_tokens.py --check    # 只校验产物是否与 tokens.json 同步（CI 用）

产物：
    apps/web/app/tokens.css                     Tailwind v4 @theme（web 端唯一入口）
    content/design/generated/DesignTokens.kt    KMP/Compose 端常量（纯 Kotlin，不依赖 Compose）
    content/design/preview/tokens.html          设计令牌预览页（人工核对用）
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKENS_PATH = ROOT / "content" / "design" / "tokens.json"

OUT_CSS = ROOT / "apps" / "web" / "app" / "tokens.css"
OUT_KT = ROOT / "content" / "design" / "generated" / "DesignTokens.kt"
OUT_HTML = ROOT / "content" / "design" / "preview" / "tokens.html"
OUT_PLAIN = ROOT / "content" / "design" / "preview" / "tokens.css"

HEADER = "自动生成，勿手改。源文件 content/design/tokens.json，生成器 tools/build_design_tokens.py"


def kebab(name: str) -> str:
    """displayXl -> display-xl, onSurface -> on-surface"""
    out: list[str] = []
    for i, ch in enumerate(name):
        if ch.isupper():
            if i:
                out.append("-")
            out.append(ch.lower())
        else:
            out.append(ch)
    return "".join(out)


def camel(name: str) -> str:
    """display-xl -> displayXl"""
    parts = name.replace("_", "-").split("-")
    return parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:])


def flatten(node: dict, prefix: str = "", strip_default: bool = False) -> list[tuple[str, str]]:
    """嵌套 dict -> [(a-b-c, value)]，值为标量的叶子

    strip_default=True 时去掉结尾的 -default（surface.default -> surface），
    让 Tailwind 得到 bg-surface 而不是 bg-surface-default。
    """
    items: list[tuple[str, str]] = []
    for key, value in node.items():
        name = f"{prefix}-{kebab(key)}" if prefix else kebab(key)
        if name.endswith("-default"):
            name = name[: -len("-default")]
        if isinstance(value, dict):
            items.extend(flatten(value, name, strip_default))
        else:
            items.append((name, str(value)))
    return items


def css_font_stack(stack: list[str]) -> str:
    quoted = [f'"{f}"' if " " in f else f for f in stack]
    return ", ".join(quoted)


def build_css(tokens: dict) -> str:
    lines: list[str] = [f"/* {HEADER} */", ""]

    lines.append("@theme static {")
    lines.append("  /* static：所有令牌都输出为 CSS 变量，未被 utility 使用也不裁掉 */")
    lines.append("")
    lines.append("  /* ---- color ---- */")
    for name, value in flatten(tokens["color"]):
        lines.append(f"  --color-{name}: {value};")
    lines.append("")
    lines.append("  /* ---- font family ---- */")
    for name, stack in tokens["font"].items():
        lines.append(f"  --font-{kebab(name)}: {css_font_stack(stack)};")
    lines.append("")
    lines.append("  /* ---- type scale ---- */")
    for name, spec in tokens["type"].items():
        key = kebab(name)
        lines.append(f"  --text-{key}: {spec['size']};")
        lines.append(f"  --text-{key}--line-height: {spec['lineHeight']};")
        lines.append(f"  --text-{key}--letter-spacing: {spec['letterSpacing']};")
        lines.append(f"  --text-{key}--font-weight: {spec['weight']};")
        lines.append(f"  --text-{key}--font-family: var(--font-{kebab(spec['family'])});")
    lines.append("")
    lines.append("  /* ---- spacing ---- */")
    for name, value in tokens["space"].items():
        lines.append(f"  --spacing-{kebab(name)}: {value};")
    lines.append("")
    lines.append("  /* ---- radius ---- */")
    for name, value in tokens["radius"].items():
        lines.append(f"  --radius-{kebab(name)}: {value};")
    lines.append("")
    lines.append("  /* ---- layout ---- */")
    layout = tokens["layout"]
    for key in ("maxContent", "maxProse", "gutter", "gutterMobile", "marginMobile"):
        lines.append(f"  --layout-{kebab(key)}: {layout[key]};")
    for name, value in layout["breakpoints"].items():
        lines.append(f"  --breakpoint-{kebab(name)}: {value};")
    lines.append("")
    lines.append("  /* ---- motion ---- */")
    for name, value in tokens["motion"].items():
        lines.append(f"  --motion-{kebab(name)}: {value};")
    lines.append("}")

    # 非 Tailwind 场景（现有手写 CSS / 内联样式）用的别名，值全部指向上面的 token
    lines += [
        "",
        ":root {",
        "  --lv-surface: var(--color-surface);",
        "  --lv-surface-low: var(--color-surface-low);",
        "  --lv-ink: var(--color-on-surface);",
        "  --lv-ink-variant: var(--color-on-surface-variant);",
        "  --lv-ink-muted: var(--color-on-surface-muted);",
        "  --lv-line: var(--color-outline-variant);",
        "  --lv-accent: var(--color-accent);",
        "  --lv-license-cc0: var(--color-license-cc0);",
        "  --lv-license-pending: var(--color-license-pending);",
        "  --lv-license-restricted: var(--color-license-restricted);",
        "  --lv-font-display: var(--font-display);",
        "  --lv-font-serif: var(--font-serif);",
        "  --lv-font-sans: var(--font-sans);",
        "}",
        "",
    ]
    return "\n".join(lines)


def kotlin_float(value: float) -> str:
    """Kotlin 的浮点字面量必须是 4.0f，不能写 4f"""
    text = f"{value:g}"
    if "e" in text or "E" in text:
        text = f"{value:.6f}".rstrip("0")
    if "." not in text:
        text += ".0"
    return text + "f"


def kotlin_ident(group: str, name: str) -> str:
    """3xs / 2xl 这类数字开头的名字在 Kotlin 里非法，加组名前缀"""
    ident = name.replace("-", "_")
    if ident[0].isdigit():
        ident = f"{group}_{ident}"
    return ident


def hex_to_argb(value: str) -> str:
    v = value.lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    return f"0xFF{v.upper()}"


def build_kotlin(tokens: dict) -> str:
    out: list[str] = [
        "// " + HEADER,
        "package design",
        "",
        "/**",
        " * 设计令牌。纯 Kotlin 常量，不依赖 androidx.compose，可在 shared / 服务端直接引用。",
        " * Compose 侧映射：",
        " *   Color(DesignTokens.color.surface)            // Long → Color",
        " *   DesignTokens.type.bodyMd.size.sp             // Float → TextUnit",
        " *   FontFamily(Font(...))                        // 字体文件见 docs/design-system.md",
        " */",
        "object DesignTokens {",
    ]

    out.append("    object color {")
    for name, value in flatten(tokens["color"]):
        out.append(f"        const val {name.replace('-', '_')}: Long = {hex_to_argb(value)}")
    out.append("    }")
    out.append("")

    for group in ("space", "radius"):
        out.append(f"    object {group} {{")
        for name, value in tokens[group].items():
            if value.endswith("rem"):
                num = float(value.replace("rem", "")) * 16
            elif value.endswith("px"):
                num = float(value.replace("px", ""))
            else:
                num = float(value)
            out.append(f"        const val {kotlin_ident(group, name)}: Float = {kotlin_float(num)}  // {value}")
        out.append("    }")
        out.append("")

    out.append("    object type {")
    for name, spec in tokens["type"].items():
        key = name.replace("-", "_")
        out.append(f"        object {key} {{")
        out.append(f"            const val sizePx: Float = {kotlin_float(float(spec['size'].replace('rem', '')) * 16)}")
        out.append(f"            const val lineHeightMultiplier: Float = {kotlin_float(float(spec['lineHeight']))}")
        out.append(f"            const val letterSpacingEm: Float = {kotlin_float(float(spec['letterSpacing'].replace('em', '')))}")
        out.append(f"            const val weight: Int = {int(float(spec['weight']))}")
        out.append(f"            const val family: String = \"{spec['family']}\"")
        out.append("        }")
    out.append("    }")
    out.append("")

    out.append("    object font {")
    for name, stack in tokens["font"].items():
        joined = " | ".join(stack)
        out.append(f"        const val {name}: String = \"{joined}\"")
    out.append("    }")
    out.append("}")

    return "\n".join(out) + "\n"


def build_plain_css(tokens: dict) -> str:
    """给非 Tailwind 场景（静态原型、邮箱模板、预览页）用的纯 CSS 变量。

    @theme 是 Tailwind 的 at-rule，浏览器不认，直接引用 tokens.css 会整块失效，
    所以这里另出一份等价的 :root 定义。
    """
    theme = build_css(tokens)
    start = theme.index("@theme static {")
    end = theme.index("}", start)
    body = theme[start + len("@theme static {"): end]
    body = body.replace("  /* static：所有令牌都输出为 CSS 变量，未被 utility 使用也不裁掉 */\n", "")
    head = "/* " + HEADER + " */"
    return head + "\n\n:root {" + body + "}\n"


def build_preview(tokens: dict) -> str:
    color_rows: list[str] = []
    for name, value in flatten(tokens["color"]):
        light = value.upper() in {"#FFFFFF", "#F9F9F9", "#F3F3F3", "#EEEEEE", "#E8E8E8", "#E2E2E2", "#DADADA",
                                  "#C4C7C7", "#E5E2E1", "#DCE0E6", "#DEe3e8".upper()}
        color_rows.append(
            f'<div class="chip"><span class="sw" style="background:{value};'
            f'border-color:{"#0002" if light else value}"></span>'
            f'<b>--color-{name}</b><code>{value}</code></div>'
        )

    type_rows: list[str] = []
    for name, spec in tokens["type"].items():
        key = kebab(name)
        type_rows.append(
            f'<div class="typerow"><div class="tname">--text-{key}<code>{spec["size"]} / {spec["lineHeight"]} / {spec["weight"]}</code></div>'
            f'<div style="font-family:var(--font-{kebab(spec["family"])});font-size:{spec["size"]};'
            f'line-height:{spec["lineHeight"]};letter-spacing:{spec["letterSpacing"]};font-weight:{spec["weight"]}">'
            f'千里江山图 · A Thousand Li</div></div>'
        )

    space_rows = "".join(
        f'<div class="sprow"><code>--spacing-{kebab(n)}</code><span class="bar" style="width:{v};height:12px"></span><em>{v}</em></div>'
        for n, v in tokens["space"].items()
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>设计令牌 · Design Tokens {tokens['version']}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<!-- {HEADER} -->
<link rel="stylesheet" href="tokens.css">
<style>
  body {{ margin:0; padding:var(--spacing-2xl) var(--layout-gutter); background:var(--color-surface);
         color:var(--color-on-surface); font-family:var(--font-sans); }}
  h1 {{ font-family:var(--font-display); font-weight:400; font-size:2.5rem; margin:0 0 .25em; letter-spacing:-.01em }}
  h2 {{ font-family:var(--font-serif); font-size:1.125rem; letter-spacing:.12em; text-transform:uppercase;
        color:var(--color-on-surface-variant); margin:3rem 0 1rem; border-bottom:1px solid var(--color-outline-variant); padding-bottom:.5rem }}
  .meta {{ color:var(--color-on-surface-muted); font-size:.8125rem; margin-bottom:2rem }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:.75rem }}
  .chip {{ display:flex; align-items:center; gap:.6rem; background:var(--color-surface-lowest);
           border:1px solid var(--color-outline-variant); padding:.5rem .7rem; border-radius:8px; font-size:.75rem }}
  .sw {{ width:26px; height:26px; border-radius:6px; border:1px solid; flex:none }}
  .chip b {{ font-weight:500; font-family:var(--font-mono) }}
  .chip code {{ margin-left:auto; color:var(--color-on-surface-muted) }}
  .typerow {{ border-bottom:1px dashed var(--color-outline-variant); padding:.9rem 0 }}
  .tname {{ font-family:var(--font-mono); font-size:.7rem; color:var(--color-on-surface-muted); display:flex; justify-content:space-between; margin-bottom:.35rem }}
  .sprow {{ display:flex; align-items:center; gap:.8rem; font-family:var(--font-mono); font-size:.7rem; margin:.35rem 0 }}
  .bar {{ background:var(--color-accent); display:inline-block }}
  .sprow em {{ color:var(--color-on-surface-muted); font-style:normal }}
  .license {{ display:flex; gap:.5rem; flex-wrap:wrap; margin-top:.5rem }}
  .badge {{ font-size:.6875rem; letter-spacing:.08em; padding:.2rem .5rem; border-radius:999px; color:#fff }}
</style></head>
<body>
  <h1>设计令牌 Design Tokens</h1>
  <div class="meta">v{tokens['version']} · {tokens['meta']['source']} · 生成时间见 git</div>

  <h2>Color</h2>
  <div class="grid">{''.join(color_rows)}</div>

  <h2>授权状态徽标（唯一允许用彩色的地方）</h2>
  <div class="license">
    <span class="badge" style="background:var(--color-license-cc0)">CC0 开放</span>
    <span class="badge" style="background:var(--color-license-pending)">待人工核验</span>
    <span class="badge" style="background:var(--color-license-restricted)">受限 / 不开放</span>
  </div>

  <h2>Type scale</h2>
  {''.join(type_rows)}

  <h2>Spacing</h2>
  {space_rows}

  <h2>Radius</h2>
  <div class="grid">
    {''.join(f'<div class="chip" style="border-radius:{v}"><b>--radius-{kebab(n)}</b><code>{v}</code></div>' for n, v in tokens['radius'].items())}
  </div>
</body></html>
"""


IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
FLOAT_RE = re.compile(r"=\s*(-?\d+)f(?![.\dA-Za-z])")
DECL_RE = re.compile(r"const val ([^:\s]+)\s*:")


def validate_kotlin(source: str) -> None:
    """本机没有 kotlinc，至少把编译器会直接拒掉的两类硬错误挡住：
    数字开头的标识符、以及 4f 这种非法浮点字面量。"""
    problems: list[str] = []
    for ident in DECL_RE.findall(source):
        if not IDENT_RE.match(ident):
            problems.append(f"非法标识符: {ident}")
    for bad in FLOAT_RE.findall(source):
        problems.append(f"非法浮点字面量: {bad}f（应为 {bad}.0f）")
    if problems:
        raise SystemExit("DesignTokens.kt 校验失败：\n  " + "\n  ".join(problems))


def generate() -> dict[Path, str]:
    tokens = json.loads(TOKENS_PATH.read_text(encoding="utf-8"))
    kotlin = build_kotlin(tokens)
    validate_kotlin(kotlin)
    return {
        OUT_CSS: build_css(tokens),
        OUT_KT: kotlin,
        OUT_HTML: build_preview(tokens),
        OUT_PLAIN: build_plain_css(tokens),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只校验，不写盘")
    args = ap.parse_args()

    outputs = generate()
    stale: list[Path] = []
    for path, content in outputs.items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if args.check:
            if current != content:
                stale.append(path)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}  ({len(content)} bytes)")

    if args.check and stale:
        for p in stale:
            print(f"stale: {p.relative_to(ROOT)}", file=sys.stderr)
        print("产物与 tokens.json 不同步，跑 python3 tools/build_design_tokens.py", file=sys.stderr)
        return 1
    if args.check:
        print("tokens.json 与产物一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
