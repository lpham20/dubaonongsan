import { useEffect } from "react";
import { canonicalUrl, compactText, DEFAULT_OG_IMAGE, SITE_NAME } from "../lib/seo";

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
  "meta[name='twitter:title']",
  "meta[name='twitter:description']",
  "meta[name='twitter:image']",
  "meta[property='article:published_time']",
  "link[rel='canonical']"
];

export function SeoHead({
  title,
  description,
  canonical = "/",
  image = DEFAULT_OG_IMAGE,
  type = "website",
  publishedAt,
  schemaJsonLd
}: Props) {
  const fullTitle = title.includes(SITE_NAME) ? title : `${title} | ${SITE_NAME}`;
  const fullDescription = compactText(description, 160);
  const fullCanonical = canonicalUrl(canonical);

  useEffect(() => {
    document.title = fullTitle;
    managedMetaSelectors.forEach((selector) => document.head.querySelector(selector)?.remove());
    upsertMeta("name", "description", fullDescription);
    upsertMeta("property", "og:title", fullTitle);
    upsertMeta("property", "og:description", fullDescription);
    upsertMeta("property", "og:type", type);
    upsertMeta("property", "og:url", fullCanonical);
    upsertMeta("property", "og:image", image);
    upsertMeta("name", "twitter:title", fullTitle);
    upsertMeta("name", "twitter:description", fullDescription);
    upsertMeta("name", "twitter:image", image);
    if (publishedAt) upsertMeta("property", "article:published_time", publishedAt);
    const canonicalTag = document.createElement("link");
    canonicalTag.rel = "canonical";
    canonicalTag.href = fullCanonical;
    document.head.appendChild(canonicalTag);
  }, [fullTitle, fullDescription, fullCanonical, image, publishedAt, type]);

  const schemas = Array.isArray(schemaJsonLd) ? schemaJsonLd : schemaJsonLd ? [schemaJsonLd] : [];

  return (
    <>
      {schemas.map((schema, index) => (
        <script
          key={index}
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
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
