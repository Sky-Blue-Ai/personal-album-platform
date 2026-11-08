import { href } from "@/lib/paths";
import { holdings, stats } from "@/lib/works";

export const metadata = { title: "版权与署名 · 古代艺术名人画展" };

export default function About() {
  const s = stats();
  const sources = holdings();

  return (
    <main className="work">
      <div className="wrap">
        <div className="crumbs">
          <a href={href("/")}>展厅</a> / 版权与署名
        </div>

        <div className="prose">
          <h1>版权与署名说明</h1>

          <p>
            本站展示的画作原作均已进入公有领域。所使用图片取自博物馆开放数据项目，
            授权状态为 CC0（Creative Commons Zero）或公有领域标识（Public Domain Mark）。
            即使 CC0 不强制要求署名，本站仍在每件作品页固定展示「作者 · 作品 · 来源机构」，
            并保留机构原始 credit line——这既是署名权的合规要求，也是内容可信度的基础。
          </p>

          <h2>归属标注</h2>
          <p>
            部分中国书画在机构元数据中被标注为「佚名」或「传」某家。这类作品在页面上以
            「传 · 摹本」「佚名」「归属待考」三种标记如实呈现，不作为原作展示。
            检索命中不等于归属成立：Met 的一件标为「传倪瓒」的作品，可能只是后人临仿。
          </p>

          <h2>授权核验</h2>
          <p>
            本站把「授权」当作逐张图片的事实，而不是逐位艺术家的属性。每条图像记录都要
            打开原始来源页、看到 CC0 或公有领域标识，才由人工改成 <code>verified</code>；
            未核验的记录不会进入前台内容视图。当前收录 {s.works} 件作品，其中 {s.verified} 件
            已完成核验，{s.pending} 件仍在待核验状态——页面上以「待核验」徽标区分。
          </p>

          <h2>数据来源</h2>
          <p>
            {sources.map((h) => `${h.name}（${h.count} 件）`).join("、")}。
            每件作品的详情页给出直达原始记录页面的链接。
          </p>

          <h2>联系</h2>
          <p>
            发现授权标注有误、署名缺失或图片使用不当，请联系站点维护者，我们会在核实后立即下架或更正。
          </p>
        </div>
      </div>
    </main>
  );
}
