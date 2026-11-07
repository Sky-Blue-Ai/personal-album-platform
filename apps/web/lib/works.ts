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
  image: { src: string; thumb: string; width: number; height: number };
};

import raw from "@/data/works.json";

export const works: Work[] = raw as Work[];

export function byRegion(region: "cn" | "west"): Work[] {
  return works.filter((w) => w.region === region);
}

export function getWork(id: string): Work | undefined {
  return works.find((w) => w.id === id);
}

/** 传 / 摹本 标记：Met 等机构对中国书画常标 Unidentified artist，前台必须如实区分 */
export function attributionLabel(w: Work): string | null {
  if (w.attribution === "copy_or_attributed") return "传 · 摹本";
  if (w.attribution === "target_title_match") return "待核归属";
  if (w.attribution === "unidentified_search_hit") return "佚名";
  return null;
}

export function displayTitle(w: Work): string {
  return w.title_zh ?? w.title ?? "无题";
}
