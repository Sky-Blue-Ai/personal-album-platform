/** @type {import('next').NextConfig} */
// GitHub Pages 项目站点挂在 /<repo>/ 下，构建时用 NEXT_PUBLIC_BASE_PATH 指定；
// 本地与自托管保持根路径，此时两项都是空字符串。
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

const nextConfig = {
  output: "export",
  images: { unoptimized: true },
  trailingSlash: true,
  basePath,
  assetPrefix: basePath || undefined,
};

export default nextConfig;
