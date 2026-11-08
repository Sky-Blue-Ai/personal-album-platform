"use client";

import { useMemo, useState } from "react";
import WorkCard, { type CardModel } from "./WorkCard";

export type ArtistOption = { id: string; name: string; count: number; region: "cn" | "west" };
type Props = { cards: CardModel[]; artists: ArtistOption[] };

const FILTERS = [
  { key: "all", label: "全部" },
  { key: "cn", label: "中国" },
  { key: "west", label: "西方" },
] as const;

export default function Catalogue({ cards, artists }: Props) {
  const [q, setQ] = useState("");
  const [region, setRegion] = useState<"all" | "cn" | "west">("all");
  const [artist, setArtist] = useState("all");

  const list = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return cards.filter((c) => {
      if (region !== "all" && c.region !== region) return false;
      if (artist !== "all" && c.artistId !== artist) return false;
      if (!needle) return true;
      return [c.title, c.titleAlt, c.artistZh, c.artistEn, c.date]
        .filter(Boolean)
        .some((f) => String(f).toLowerCase().includes(needle));
    });
  }, [cards, q, region, artist]);

  const cn = artists.filter((a) => a.region === "cn");
  const west = artists.filter((a) => a.region === "west");

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

        <label className="visually-hidden" htmlFor="artist-filter">按作者筛选</label>
        <select
          id="artist-filter"
          className="select"
          value={artist}
          onChange={(e) => setArtist(e.target.value)}
        >
          <option value="all">全部作者（{artists.length}）</option>
          <optgroup label="中国序列">
            {cn.map((a) => (
              <option key={a.id} value={a.id}>{a.name}（{a.count}）</option>
            ))}
          </optgroup>
          <optgroup label="西方序列">
            {west.map((a) => (
              <option key={a.id} value={a.id}>{a.name}（{a.count}）</option>
            ))}
          </optgroup>
        </select>
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
