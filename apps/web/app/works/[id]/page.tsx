import { notFound } from "next/navigation";
import Viewer from "@/components/Viewer";
import { attributionLabel, displayTitle, getWork, works } from "@/lib/works";

export function generateStaticParams() {
  return works.map((w) => ({ id: w.id }));
}

export default async function WorkPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const w = getWork(id);
  if (!w) notFound();

  const badge = attributionLabel(w);

  return (
    <main className="work">
      <div className="wrap">
        <div className="crumbs">
          <a href="/">展厅</a> / {w.region === "cn" ? "中国序列" : "西方序列"} / {w.artist.name_zh}
        </div>
        <div className="work-grid">
          <div>
            <Viewer
              src={w.image.src}
              alt={`${w.artist.name_zh} · ${displayTitle(w)}`}
              width={w.image.width}
              height={w.image.height}
            />
          </div>
          <aside className="info">
            <h1>{displayTitle(w)}</h1>
            {w.title && w.title_zh ? <div className="original">{w.title}</div> : null}
            <div className="artist">
              {w.artist.name_zh} <em>{w.artist.name_en}</em>
            </div>
            {badge ? <div className="original">归属标注：{badge}</div> : null}

            <dl className="facts">
              {w.date ? (
                <div>
                  <dt>年代</dt>
                  <dd>{w.date}</dd>
                </div>
              ) : null}
              {w.medium ? (
                <div>
                  <dt>材质</dt>
                  <dd>{w.medium}</dd>
                </div>
              ) : null}
              {w.dimensions ? (
                <div>
                  <dt>尺寸</dt>
                  <dd style={{ whiteSpace: "pre-line" }}>{w.dimensions}</dd>
                </div>
              ) : null}
              {w.holding ? (
                <div>
                  <dt>藏地</dt>
                  <dd>{w.holding}</dd>
                </div>
              ) : null}
            </dl>

            <div className="credit">
              <div className="label">SOURCE &amp; LICENSE</div>
              <div className="line">
                <b>{w.artist.name_zh}</b> · {w.title ?? displayTitle(w)} · {w.holding}
              </div>
              <div className="line">授权：{w.license} — {w.license_evidence}</div>
              <div className="line">
                来源：
                {w.source_url ? (
                  <a href={w.source_url} target="_blank" rel="noreferrer">
                    {w.source_url}
                  </a>
                ) : (
                  "—"
                )}
              </div>
              <div className="line">机构署名：{w.credit_line}</div>
              <div className="line">获取日期：{w.fetched_at}</div>
              <div className="status">核验状态 {w.verification_status?.toUpperCase()}</div>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}
