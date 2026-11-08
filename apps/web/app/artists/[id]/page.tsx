import { href } from "@/lib/paths";
import { notFound } from "next/navigation";
import WorkCard, { toCard } from "@/components/WorkCard";
import { artists, getArtist, worksByArtist } from "@/lib/works";

export function generateStaticParams() {
  return artists.map((a) => ({ id: a.id }));
}

export default async function ArtistPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const artist = getArtist(id);
  if (!artist) notFound();

  const list = worksByArtist(id).map(toCard);
  const institutions = [...new Set(worksByArtist(id).map((w) => w.holding).filter(Boolean))];

  return (
    <main>
      <div className="wrap">
        <div className="artist-hero">
          <div className="crumbs">
            <a href={href("/")}>展厅</a> / {artist.region === "cn" ? "中国序列" : "西方序列"} / 艺术家
          </div>
          <h1>{artist.name_zh}</h1>
          <div className="en">{artist.name_en}</div>
          <div className="mono" style={{ marginTop: 12 }}>
            第 {artist.phase} 期 · {list.length} 件在架 · {institutions.join(" / ") || "—"}
          </div>
        </div>

        {list.length ? (
          <div className="grid-works">
            {list.map((c) => (
              <WorkCard key={c.id} card={c} />
            ))}
          </div>
        ) : (
          <div className="empty">这位艺术家暂无在架作品。</div>
        )}
      </div>
    </main>
  );
}
