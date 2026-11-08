import { href } from "@/lib/paths";
import type { Metadata } from "next";
import "./globals.css";
import { stats } from "@/lib/works";

export const metadata: Metadata = {
  title: "古代艺术名人画展 · 中西双线",
  description:
    "公有领域名作的线上展厅：中西双线对照浏览，作品页提供高清缩放与可追溯的来源、授权与署名信息。",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const s = stats();

  return (
    <html lang="zh-CN">
      <body>
        <header className="site-header">
          <div className="wrap inner">
            <a className="brand" href={href("/")}>
              古代艺术名人画展
              <small>PUBLIC DOMAIN GALLERY</small>
            </a>
            <nav className="nav">
              <a href={href("/")}>展厅</a>
              <a href={href("/artists/")}>艺术家</a>
              <a href={href("/about/")}>版权与署名</a>
            </nav>
          </div>
        </header>

        {children}

        <footer className="site-footer">
          <div className="wrap cols">
            <div>
              图片均取自博物馆开放数据（CC0 / 公有领域），仅用于非商业展示。
              <br />
              每件作品保留原始来源、授权标识与机构署名，署名权不因 CC0 而免除。
            </div>
            <div className="mono">
              MET OPEN ACCESS · CMA OPEN ACCESS · WIKIMEDIA
              <br />
              {s.works} WORKS · {s.verified} VERIFIED · {s.pending} PENDING
              <br />
              IIIF READY · SOURCE-TRACEABLE
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
