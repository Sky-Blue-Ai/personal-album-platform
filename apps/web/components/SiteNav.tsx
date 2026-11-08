"use client";

import { usePathname } from "next/navigation";
import { BASE, href } from "@/lib/paths";

const TABS = [
  // 作品详情属于「展厅」这一支
  { path: "/", label: "展厅", match: (p: string) => p === "/" || p === "" || p.startsWith("/works") },
  { path: "/artists/", label: "艺术家", match: (p: string) => p.startsWith("/artists") },
  { path: "/about/", label: "版权与署名", match: (p: string) => p.startsWith("/about") },
];

export default function SiteNav() {
  const raw = usePathname() || "/";
  // 子路径部署时 pathname 可能带 basePath，先剥掉再比
  const current = BASE && raw.startsWith(BASE) ? raw.slice(BASE.length) || "/" : raw;
  const isHome = current === "/" || current === "";

  function goBack() {
    // 直接打开链接时没有上一页，退回展厅
    if (typeof window !== "undefined" && window.history.length > 1) window.history.back();
    else window.location.href = href("/");
  }

  return (
    <div className="nav-wrap">
      {!isHome ? (
        <button type="button" className="back-btn" onClick={goBack} aria-label="返回上一页" title="返回上一页">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
               strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M15 5 8 12l7 7" />
          </svg>
        </button>
      ) : null}

      <nav className="nav" aria-label="主导航">
        {TABS.map((t) => (
          <a
            key={t.path}
            href={href(t.path)}
            aria-current={t.match(current) ? "page" : undefined}
          >
            {t.label}
          </a>
        ))}
      </nav>
    </div>
  );
}
