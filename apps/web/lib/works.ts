export type Work = {
  id: string;
  artist: { name_zh: string; name_en: string };
  region: "cn" | "west";
  phase: number;
  title_zh: string | null;
  title: string | null;
  date: string | null;
  medium: string | null;
  dimensions: string | null;
  holding: string | null;
  attribution: string | null;
  target_match: string | null;
  license: string | null;
  license_evidence: string | null;
  source_url: string | null;
  credit_line: string | null;
  fetched_at: string | null;
  verification_status: string | null;
  provider?: string | null;
  provider_object_id?: string | null;
  image: { src: string | null; thumb: string | null; width?: number; height?: number; external?: boolean };
};

import raw from "@/data/works.json";

export const works: Work[] = (raw as Work[]).filter((w) => Boolean(w.image?.thumb));

export const REGION_LABEL: Record<string, string> = { cn: "中国序列", west: "西方序列" };

export function displayTitle(w: Work): string {
  return w.title_zh ?? w.title ?? "无题";
}

/** 传 / 摹本 标记：机构对中国书画常标 Unidentified artist，前台必须如实区分 */
export function attributionLabel(w: Work): string | null {
  if (w.attribution === "copy_or_attributed") return "传 · 摹本";
  if (w.attribution === "target_title_match") return "归属待考";
  if (w.attribution === "unidentified_search_hit") return "佚名";
  return null;
}

/** 授权徽标：三态是发布门禁在前台的投影 */
export function licenseBadge(w: Work): { text: string; tone: "cc0" | "pending" | "restricted" } {
  if (w.verification_status !== "verified") return { text: "待核验", tone: "pending" };
  if (w.license === "CC0") return { text: "CC0 开放", tone: "cc0" };
  if (w.license === "PDM") return { text: "公有领域", tone: "cc0" };
  if (w.license === "FAITHFUL_COPY") return { text: "忠实副本", tone: "cc0" };
  return { text: "授权受限", tone: "restricted" };
}

export function getWork(id: string): Work | undefined {
  return works.find((w) => w.id === id);
}

export function artistIdOfWork(w: Work): string {
  return w.id.slice(0, w.id.lastIndexOf("-"));
}

export function worksByArtist(artistId: string): Work[] {
  return works.filter((w) => artistIdOfWork(w) === artistId);
}

export type ArtistEntry = {
  id: string;
  name_zh: string;
  name_en: string;
  region: "cn" | "west";
  phase: number;
  count: number;
  /** 代表作缩略图：优先本地大图那张，否则取第一张有图的 */
  thumb: string | null;
};

export const artists: ArtistEntry[] = (() => {
  const map = new Map<string, ArtistEntry>();
  for (const w of works) {
    const id = artistIdOfWork(w);
    const thumb = w.image.thumb;
    const entry = map.get(id);
    if (entry) {
      entry.count += 1;
      // 本地大图（非外链缩略图）拿来做头像更清楚
      if (!entry.thumb || (!w.image.external && thumb)) entry.thumb = thumb ?? entry.thumb;
    } else {
      map.set(id, {
        id,
        name_zh: w.artist.name_zh,
        name_en: w.artist.name_en,
        region: w.region,
        phase: w.phase,
        count: 1,
        thumb: thumb ?? null,
      });
    }
  }
  return [...map.values()].sort((a, b) => b.count - a.count);
})();

/** 索引页用：中国 / 西方分组，组内按作品数降序 */
export function artistsByRegion(region: "cn" | "west"): ArtistEntry[] {
  return artists.filter((a) => a.region === region);
}

export function getArtist(id: string): ArtistEntry | undefined {
  return artists.find((a) => a.id === id);
}

export function holdings(): { name: string; count: number }[] {
  const map = new Map<string, number>();
  for (const w of works) {
    const key = w.holding ?? "未标注机构";
    map.set(key, (map.get(key) ?? 0) + 1);
  }
  return [...map.entries()].map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count);
}

export function stats() {
  const verified = works.filter((w) => w.verification_status === "verified").length;
  return {
    works: works.length,
    artists: artists.length,
    verified,
    pending: works.length - verified,
    cn: works.filter((w) => w.region === "cn").length,
    west: works.filter((w) => w.region === "west").length,
  };
}

/** 策展专题：第 1 期的三条中西并置线索（选品见飞书文档第 3 期） */
export const DOSSIERS = [
  {
    slug: "scrolls",
    num: "DOSSIER 01",
    title: "长卷的时间性",
    note: "横向延展铺陈时间，对照单点透视的瞬间",
    names: ["张择端", "黄公望", "王希孟"],
  },
  {
    slug: "portrait",
    num: "DOSSIER 02",
    title: "肖像与自我",
    note: "从宫廷图绘到市民阶层，凝视的主体在移动",
    names: ["伦勃朗", "维米尔", "顾恺之（传）"],
  },
  {
    slug: "nature",
    num: "DOSSIER 03",
    title: "自然作为母题",
    note: "山水的「可游可居」与风景的「如画」传统",
    names: ["范宽", "郭熙", "莫奈"],
  },
] as const;

export function searchWorks(list: Work[], q: string): Work[] {
  const needle = q.trim().toLowerCase();
  if (!needle) return list;
  return list.filter((w) =>
    [w.title, w.title_zh, w.artist.name_zh, w.artist.name_en, w.date, w.holding, w.medium]
      .filter(Boolean)
      .some((field) => String(field).toLowerCase().includes(needle)),
  );
}
