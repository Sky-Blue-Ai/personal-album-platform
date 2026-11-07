import { attributionLabel, byRegion, displayTitle, works } from "@/lib/works";

function Card({ w }: { w: ReturnType<typeof byRegion>[number] }) {
  const badge = attributionLabel(w);
  return (
    <a className="card" href={`/works/${w.id}/`}>
      <div className="frame">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={w.image.thumb} alt={`${w.artist.name_zh} · ${displayTitle(w)}`} loading="lazy" />
        {badge ? <span className="badge">{badge}</span> : null}
      </div>
      <h3>{displayTitle(w)}</h3>
      <div className="by">{w.artist.name_zh}</div>
      {w.title_zh && w.title ? <div className="orig">{w.title}</div> : null}
    </a>
  );
}

function Section({
  id,
  title,
  en,
  list,
}: {
  id: string;
  title: string;
  en: string;
  list: ReturnType<typeof byRegion>;
}) {
  return (
    <section className="section" id={id}>
      <div className="section-head">
        <h2>{title}</h2>
        <span className="en">{en}</span>
        <span className="rule" />
        <span className="en">{list.length} 件</span>
      </div>
      <div className="grid">
        {list.map((w) => (
          <Card key={w.id} w={w} />
        ))}
      </div>
    </section>
  );
}

export default function Home() {
  const cn = byRegion("cn");
  const west = byRegion("west");
  return (
    <main>
      <div className="wrap">
        <div className="hero">
          <h1>
            两个传统，
            <br />
            同一双看画的眼睛
          </h1>
          <p>
            从范宽、郭熙到伦勃朗、维米尔，全部作品取自大都会博物馆、克利夫兰艺术博物馆等机构的开放数据。
            每件作品都可放大到细节，并附上原始来源链接、授权标识与机构署名——看得清，也查得到。
          </p>
          <div className="meta">
            {works.length} WORKS · 第 1 期 · 数据取自开放接口，图片核验状态：PENDING
          </div>
        </div>

        <Section id="cn" title="中国序列" en="Chinese Painting" list={cn} />
        <Section id="west" title="西方序列" en="Western Painting" list={west} />
      </div>
    </main>
  );
}
