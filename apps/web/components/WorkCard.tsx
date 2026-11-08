import type { Work } from "@/lib/works";
import { artistIdOfWork, attributionLabel, displayTitle, licenseBadge } from "@/lib/works";
import Thumb from "./Thumb";
import { asset, href } from "@/lib/paths";

export type CardModel = {
  id: string;
  title: string;
  titleAlt: string | null;
  artistId: string;
  artistZh: string;
  artistEn: string;
  date: string | null;
  thumb: string;
  licenseText: string;
  licenseTone: "cc0" | "pending" | "restricted";
  attribution: string | null;
  region: "cn" | "west";
};

/** 作品 → 卡片所需的最小字段：客户端组件只吃这个，避免把整包元数据塞进 bundle */
export function toCard(w: Work): CardModel {
  const lb = licenseBadge(w);
  return {
    id: w.id,
    title: displayTitle(w),
    titleAlt: w.title_zh && w.title && w.title !== w.title_zh ? w.title : null,
    artistId: artistIdOfWork(w),
    artistZh: w.artist.name_zh,
    artistEn: w.artist.name_en,
    date: w.date,
    thumb: asset(w.image.thumb),
    licenseText: lb.text,
    licenseTone: lb.tone,
    attribution: attributionLabel(w),
    region: w.region,
  };
}

export default function WorkCard({ card }: { card: CardModel }) {
  return (
    <a className="card" href={href(`/works/${card.id}/`)}>
      <div className="frame">
        <Thumb src={card.thumb} alt={`${card.artistZh} · ${card.title}`} />
      </div>
      <h3>{card.title}</h3>
      <div className="by">
        {card.artistZh}
        {card.date ? <span style={{ color: "var(--color-on-surface-muted)" }}> · {card.date}</span> : null}
      </div>
      {card.titleAlt ? <div className="orig">{card.titleAlt}</div> : null}
      <div className="tags">
        <span className={`badge ${card.licenseTone}`}>{card.licenseText}</span>
        {card.attribution ? <span className="badge attr">{card.attribution}</span> : null}
      </div>
    </a>
  );
}
