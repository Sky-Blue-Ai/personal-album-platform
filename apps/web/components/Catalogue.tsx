"use client";

import { useMemo, useState } from "react";
import WorkCard, { type CardModel } from "./WorkCard";

type Props = { cards: CardModel[] };

const FILTERS = [
  { key: "all", label: "全部" },
  { key: "cn", label: "中国" },
  { key: "west", label: "西方" },
] as const;

export default function Catalogue({ cards }: Props) {
  const [q, setQ] = useState("");
  const [region, setRegion] = useState<"all" | "cn" | "west">("all");

  const list = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return cards.filter((c) => {
      if (region !== "all" && c.region !== region) return false;
      if (!needle) return true;
      return [c.title, c.titleAlt, c.artistZh, c.artistEn, c.date]
        .filter(Boolean)
        .some((f) => String(f).toLowerCase().includes(needle));
    });
  }, [cards, q, region]);

  return (
    <>
      <div className="toolbar">
        <label className="search">
          <span>检索</span>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="作者 / 作品名 / 年代 / 馆藏，例如「范宽」「Vermeer」"
            aria-label="检索作品"
          />
          {q ? (
            <button
              onClick={() => setQ("")}
              aria-label="清空"
              style={{ border: 0, background: "none", cursor: "pointer", fontFamily: "var(--font-mono)", color: "var(--color-on-surface-muted)" }}
            >
              清除
            </button>
          ) : null}
        </label>
        <div className="chips">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              className="chip"
              aria-pressed={region === f.key}
              onClick={() => setRegion(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>
        <span className="count">
          {list.length} / {cards.length} 件
        </span>
      </div>

      {list.length === 0 ? (
        <div className="empty">没有匹配的作品。换个词试试，或点「全部」。</div>
      ) : (
        <div className="grid-works">
          {list.map((c) => (
            <WorkCard key={c.id} card={c} />
          ))}
        </div>
      )}
    </>
  );
}
