export default function About() {
  return (
    <main className="work">
      <div className="wrap">
        <div className="crumbs">
          <a href="/">展厅</a> / 版权与署名
        </div>
        <div style={{ maxWidth: 760 }}>
          <h1 style={{ fontSize: 30, fontWeight: 500, marginBottom: 20 }}>版权与署名说明</h1>
          <div style={{ lineHeight: 2, fontSize: 14.5, color: "var(--ink-2)" }}>
            <p>
              本站展示的画作原作均已进入公有领域。所使用图片取自博物馆开放数据项目，
              其授权状态为 CC0（Creative Commons Zero）或公有领域标识（Public Domain Mark）。
            </p>
            <p>
              即使 CC0 不强制要求署名，本站仍在每件作品页固定展示「作者 · 作品 · 来源机构」，
              并保留机构原始 credit line。这既是署名权的合规要求，也是内容可信度的基础。
            </p>
            <p>
              部分中国书画在机构元数据中被标注为「佚名」或「传」某家，
              这类作品在页面上以「传 · 摹本」「佚名」「待核归属」等标记呈现，不作为原作展示。
            </p>
            <p>
              当前版本所有图片的核验状态为 PENDING——即已从开放接口取得并记录来源与授权标识，
              但仍待逐张人工复核后发布。发现问题请联系站点维护者。
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
