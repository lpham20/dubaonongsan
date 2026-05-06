import type { CropType, NewsArticle } from "./api";

export const SITE_ORIGIN = "https://dubaonongsan.com";
export const SITE_NAME = "Dự báo nông sản";
export const DEFAULT_OG_IMAGE = `${SITE_ORIGIN}/og-cover.jpg`;

export const cropSeoLabels: Record<CropType, string> = {
  sau_rieng: "sầu riêng",
  ca_phe: "cà phê",
  ho_tieu: "hồ tiêu",
  lua: "lúa"
};

export function slugFromText(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 120) || "bai-viet";
}

export function slugFromUrl(url: string, fallback = "bai-viet") {
  try {
    const parsed = new URL(url);
    const tail = parsed.pathname.split("/").filter(Boolean).at(-1) || fallback;
    return slugFromText(tail.replace(/\.(html?|aspx?)$/i, ""));
  } catch {
    return slugFromText(fallback);
  }
}

export function newsSlug(article: NewsArticle) {
  return `${article.article_id}-${slugFromUrl(article.source_url, article.title)}`;
}

export function newsPath(article: NewsArticle) {
  return `/tin-tuc/${newsSlug(article)}`;
}

export function publicGuideSlug(slug: string) {
  return slug.replace(/^hai[-_]?nong-+/i, "");
}

export function guidePath(slug: string) {
  return `/huong-dan/${publicGuideSlug(slug)}`;
}

export function forecastPath(crop: CropType) {
  return `/du-bao-gia/${crop}`;
}

export function categoryPath(category: string) {
  return `/tin-tuc/category/${slugFromText(category)}`;
}

export function canonicalUrl(path: string) {
  return `${SITE_ORIGIN}${path.startsWith("/") ? path : `/${path}`}`;
}

export function compactText(value: string, maxLength = 160) {
  const cleaned = value.replace(/\s+/g, " ").trim();
  if (cleaned.length <= maxLength) return cleaned;
  const boundary = cleaned.lastIndexOf(" ", maxLength - 1);
  return `${cleaned.slice(0, boundary > 70 ? boundary : maxLength).trim()}...`;
}
