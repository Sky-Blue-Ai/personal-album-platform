import Catalogue from "@/components/Catalogue";
import { toCard } from "@/components/WorkCard";
import { DOSSIERS, artists, holdings, stats, works } from "@/lib/works";

export default function Home() {
  const s = stats();
  const schools = holdings().slice(0, 4);
  const masters = artists.slice(0, 4);
  const cards = works.map(toCard);

  return (
    <main>
      <div className="wrap">
        <section className="hero">
          <div className="eyebrow">Catalogue Raisonné Index / 跨文明典藏索引</div>
          <h1>
            两个传统，
            <br />
            同一双看画的眼睛
          </h1>
          <p className="lede">
            从范宽、郭熙到伦勃朗、维米尔，全部作品取自大都会博物馆、克利夫兰艺术博物馆等机构的开放数据。
            每件作品都标注原始来源、授权标识与机构署名，并可放大到细节——看得清，也查得到。
          </p>
          <div className="stat-row">
            <div className="stat">
              <b>{s.works}</b>
              <span className="mono">件作品</span>
            </div>
            <div className="stat">
              <b>{s.artists}</b>
              <span className="mono">位艺术家</span>
            </div>
            <div className="stat">
              <b>
                {s.cn} / {s.west}
              </b>
              <span className="mono">中国 / 西方</span>
            </div>
            <div className="stat">
              <b>{s.verified}</b>
              <span className="mono">已核验授权</span>
            </div>
          </div>
        </section>

        <section className="dim-section">
          <div className="dim-grid">
            <div className="dim">
              <div className="num">DIMENSION I</div>
              <h3>分期与地域</h3>
              <ul>
                <li>
                  <span>第 1 期 · 中国</span>
                  <em>{s.cn}</em>
                </li>
                <li>
                  <span>第 1 期 · 西方</span>
                  <em>{s.west}</em>
                </li>
                <li>
                  <span>待核验授权</span>
                  <em>{s.pending}</em>
                </li>
              </ul>
            </div>

            <div className="dim">
              <div className="num">DIMENSION II</div>
              <h3>收藏机构源</h3>
              <ul>
                {schools.map((h) => (
                  <li key={h.name}>
                    <span>{h.name}</span>
                    <em>{h.count}</em>
                  </li>
                ))}
              </ul>
            </div>

            <div className="dim">
              <div className="num">DIMENSION III</div>
              <h3>历代巨匠</h3>
              <ul>
                {masters.map((a) => (
                  <li key={a.id}>
                    <a href={`/artists/${a.id}/`}>{a.name_zh}</a>
                    <em>{a.count}</em>
                  </li>
                ))}
              </ul>
            </div>

            <div className="dim">
              <div className="num">DIMENSION IV</div>
              <h3>策展专题</h3>
              <ul>
                {DOSSIERS.map((d) => (
                  <li key={d.slug}>
                    <span>{d.title}</span>
                    <em>{d.num.replace("DOSSIER ", "#")}</em>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        <Catalogue cards={cards} />
      </div>
    </main>
  );
}
