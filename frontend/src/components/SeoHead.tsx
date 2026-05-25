import { useInsertionEffect } from "react";
import { useLanguage } from "../contexts/LanguageContext";
import { safeJsonLd } from "../lib/jsonLd";
import { canonicalUrl, compactText, DEFAULT_OG_IMAGE, SITE_NAME } from "../lib/seo";
import { withLanguagePrefix } from "../lib/localizedRoutes";

type Props = {
  title: string;
  description: string;
  canonical?: string;
  image?: string;
  type?: "website" | "article";
  publishedAt?: string | null;
  schemaJsonLd?: object | object[];
};

const managedMetaSelectors = [
  "meta[name='description']",
  "meta[property='og:title']",
  "meta[property='og:description']",
  "meta[property='og:type']",
  "meta[property='og:url']",
  "meta[property='og:image']",
  "meta[property='og:image:type']",
  "meta[property='og:image:width']",
  "meta[property='og:image:height']",
  "meta[property='og:locale']",
  "meta[name='twitter:title']",
  "meta[name='twitter:description']",
  "meta[name='twitter:image']",
  "meta[property='article:published_time']",
  "link[rel='canonical']",
  "link[rel='alternate'][hreflang]"
];
const JSON_LD_NONCE = "dubaonongsan-jsonld";

export function SeoHead({
  title,
  description,
  canonical = "/",
  image = DEFAULT_OG_IMAGE,
  type = "website",
  publishedAt,
  schemaJsonLd
}: Props) {
  const { language } = useLanguage();
  const fullTitle = title.includes(SITE_NAME) ? title : `${title} | ${SITE_NAME}`;
  const fullDescription = compactText(description, 160);
  const localizedCanonical = withLanguagePrefix(canonical, language);
  const fullCanonical = canonicalUrl(localizedCanonical);
  const alternateVi = canonicalUrl(withLanguagePrefix(canonical, "vi"));
  const alternateEn = canonicalUrl(withLanguagePrefix(canonical, "en"));

  useInsertionEffect(() => {
    document.title = fullTitle;
    managedMetaSelectors.forEach((selector) => {
      document.head.querySelectorAll(selector).forEach((element) => element.remove());
    });
    upsertMeta("name", "description", fullDescription);
    upsertMeta("property", "og:title", fullTitle);
    upsertMeta("property", "og:description", fullDescription);
    upsertMeta("property", "og:type", type);
    upsertMeta("property", "og:url", fullCanonical);
    upsertMeta("property", "og:locale", language === "en" ? "en_US" : "vi_VN");
    upsertMeta("property", "og:image", image);
    upsertMeta("property", "og:image:type", image.endsWith(".webp") ? "image/webp" : "image/jpeg");
    upsertMeta("property", "og:image:width", "1200");
    upsertMeta("property", "og:image:height", "630");
    upsertMeta("name", "twitter:title", fullTitle);
    upsertMeta("name", "twitter:description", fullDescription);
    upsertMeta("name", "twitter:image", image);
    if (publishedAt) upsertMeta("property", "article:published_time", publishedAt);
    const canonicalTag = document.createElement("link");
    canonicalTag.rel = "canonical";
    canonicalTag.href = fullCanonical;
    document.head.appendChild(canonicalTag);
    upsertAlternate("vi", alternateVi);
    upsertAlternate("en", alternateEn);
    upsertAlternate("x-default", alternateVi);
  }, [alternateEn, alternateVi, fullTitle, fullDescription, fullCanonical, image, language, publishedAt, type]);

  const schemas = Array.isArray(schemaJsonLd) ? schemaJsonLd : schemaJsonLd ? [schemaJsonLd] : [];

  return (
    <>
      {schemas.map((schema, index) => (
        <script
          key={index}
          type="application/ld+json"
          nonce={JSON_LD_NONCE}
          dangerouslySetInnerHTML={{ __html: safeJsonLd(schema) }}
        />
      ))}
    </>
  );
}

function upsertMeta(attribute: "name" | "property", key: string, content: string) {
  const meta = document.createElement("meta");
  meta.setAttribute(attribute, key);
  meta.content = content;
  document.head.appendChild(meta);
}

function upsertAlternate(hreflang: string, href: string) {
  const link = document.createElement("link");
  link.rel = "alternate";
  link.hreflang = hreflang;
  link.href = href;
  document.head.appendChild(link);
}
