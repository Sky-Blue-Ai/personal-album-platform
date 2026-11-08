/**
 * GitHub Pages 部署在子路径（/personal-album-platform/）下，静态导出时
 * next 只会给 /_next 资源加前缀，页面里手写的 <a href> 和 data 里的图片路径不会。
 * 所以这里统一收口：内部链接用 href()，图片用 asset()。
 *
 * 正常构建（根路径）时 BASE 为空字符串，两者都是恒等函数。
 */
export const BASE = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

export function href(path: string): string {
  if (!path.startsWith("/")) return path;
  return `${BASE}${path}`;
}

export function asset(path: string | null | undefined): string {
  if (!path) return "";
  if (/^https?:/i.test(path)) return path;
  return `${BASE}${path}`;
}
