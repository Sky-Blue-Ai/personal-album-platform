import { notFound } from "next/navigation";
import Viewer from "@/components/Viewer";
import WorkCard, { toCard } from "@/components/WorkCard";
import {
  artistIdOfWork,
  attributionLabel,
  displayTitle,
  getWork,
  licenseBadge,
  works,
  worksByArtist,
} from "@/lib/works";

export function generateStaticParams() {
  return works.map((w) => ({ id: w.id }));
}

export default async function WorkPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const w = getWork(id);
  if (!w) notFound();

  const attr = attributionLabel(w);
  const lic = licenseBadge(w);
  const artistId = artistIdOfWork(w);
  const siblings = worksByArtist(artistId)
    .filter((x) => x.id !== w.id)
    .slice(0, 4)
    .map(toCard);

  return (
    <main className="work">
      <div className="wrap">
        <div className="crumbs">
          <a href="/">展厅</a> / {w.region === "cn" ? "中国序列" : "西方序列"} /{" "}
          <a href={`/artists/${artistId}/`}>{w.artist.name_zh}</a>
        </div>

        <div className="work-grid">
          <div>
            {w.image.src ? (
              <Viewer
                src={w.image.src}
                alt={`${w.artist.name_zh} · ${displayTitle(w)}`}
                width={w.image.width ?? 0}
                height={w.image.height ?? 0}
              />
            ) : (
              <div className="viewer" style={{ display: "grid", placeItems: "center" }}>
                <span className="mono">图像暂不可用</span>
              </div>
            )}
            {w.image.external ? (
              <div className="mono" style={{ marginTop: 8, fontSize: ".625rem" }}>
                图像直接引自机构 CDN（未切片）。生产版由自家 IIIF 瓦片服务出图。
              </div>
            ) : null}
          </div>

          <aside className="info">
            <div className="tags" style={{ marginBottom: 10 }}>
              <span className={`badge ${lic.tone}`}>{lic.text}</span>
              {attr ? <span className="badge attr">{attr}</span> : null}
            </div>

            <h1>{displayTitle(w)}</h1>
            {w.title && w.title_zh ? <div className="original">{w.title}</div> : null}

            <div className="artist">
              <a href={`/artists/${artistId}/`}>{w.artist.name_zh}</a>{" "}
              <em>{w.artist.name_en}</em>
            </div>

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
              {w.attribution ? (
                <div>
                  <dt>归属</dt>
                  <dd>{attr}</dd>
                </div>
              ) : null}
            </dl>

            <div className="credit">
              <div className="label">SOURCE &amp; LICENSE</div>
              <div className="line">
                <b>{w.artist.name_zh}</b> · {w.title ?? displayTitle(w)}
                {w.holding ? ` · ${w.holding}` : ""}
              </div>
              <div className="line">
                授权：{w.license}
                {w.license_evidence ? ` — ${w.license_evidence}` : ""}
              </div>
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
              <div className="line">机构署名：{w.credit_line ?? "—"}</div>
              <div className="line">获取日期：{w.fetched_at ?? "—"}</div>
              <div className="line" style={{ marginTop: 8 }}>
                <span className={`badge ${lic.tone}`}>核验状态 {w.verification_status}</span>
              </div>
            </div>
          </aside>
        </div>

        {siblings.length ? (
          <section style={{ marginTop: "var(--spacing-2xl)" }}>
            <div className="eyebrow">同一作者 / More by {w.artist.name_en}</div>
            <div className="grid-works" style={{ paddingTop: "var(--spacing-md)" }}>
              {siblings.map((c) => (
                <WorkCard key={c.id} card={c} />
              ))}
            </div>
          </section>
        ) : null}
      </div>
    </main>
  );
}
