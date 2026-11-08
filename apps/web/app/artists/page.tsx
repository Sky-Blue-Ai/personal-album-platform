import { asset, href } from "@/lib/paths";
import { artistsByRegion, stats } from "@/lib/works";

export const metadata = { title: "历代巨匠 · 古代艺术名人画展" };

function Group({ region, label, en }: { region: "cn" | "west"; label: string; en: string }) {
  const list = artistsByRegion(region);
  if (!list.length) return null;

  return (
    <section style={{ paddingTop: "var(--spacing-xl)" }}>
      <div className="section-head">
        <h2>{label}</h2>
        <span className="en">{en}</span>
        <span className="rule" />
        <span className="en">{list.length} 位</span>
      </div>

      <div className="artist-grid">
        {list.map((a) => (
          <a className="artist-card" key={a.id} href={href(`/artists/${a.id}/`)}>
            <div className="portrait">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              {a.thumb ? <img src={asset(a.thumb)} alt={`${a.name_zh} 代表作`} referrerPolicy="no-referrer" /> : null}
            </div>
            <div className="artist-meta">
              <h3>{a.name_zh}</h3>
              <div className="en">{a.name_en}</div>
              <div className="mono">{a.count} 件在架 · 第 {a.phase} 期</div>
            </div>
          </a>
        ))}
      </div>
    </section>
  );
}

export default function ArtistsIndex() {
  const s = stats();

  return (
    <main>
      <div className="wrap">
        <section className="hero" style={{ paddingBottom: "var(--spacing-lg)" }}>
          <div className="eyebrow">Masters Index / 历代巨匠索引</div>
          <h1>
            从人到画，
            <br />
            按谱系浏览
          </h1>
          <p className="lede">
            共 {s.artists} 位艺术家、{s.works} 件在架作品。每位只收录开放数据中确有图像的记录，
            点进去可以看到该人全部作品与来源。
          </p>
        </section>

        <Group region="cn" label="中国序列" en="Chinese Masters" />
        <Group region="west" label="西方序列" en="Western Masters" />
      </div>
    </main>
  );
}
