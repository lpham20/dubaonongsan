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

const SEO_MANAGED_ATTR = "data-marketai-seo";
const JSON_LD_NONCE_FALLBACK = "dubaonongsan-jsonld";

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
    if (publishedAt) {
      upsertMeta("property", "article:published_time", publishedAt);
    } else {
      removeManaged("meta[property='article:published_time']");
    }
    const canonicalTag = upsertManagedLink("link[rel='canonical']");
    canonicalTag.rel = "canonical";
    canonicalTag.href = fullCanonical;
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
          nonce={jsonLdNonce()}
          dangerouslySetInnerHTML={{ __html: safeJsonLd(schema) }}
        />
      ))}
    </>
  );
}

function upsertMeta(attribute: "name" | "property", key: string, content: string) {
  const selector = `meta[${attribute}='${cssEscape(key)}']`;
  const meta = upsertManagedElement<HTMLMetaElement>(selector, () => document.createElement("meta"));
  meta.setAttribute(attribute, key);
  meta.content = content;
}

function upsertAlternate(hreflang: string, href: string) {
  const selector = `link[rel='alternate'][hreflang='${cssEscape(hreflang)}']`;
  const link = upsertManagedLink(selector);
  link.rel = "alternate";
  link.hreflang = hreflang;
  link.href = href;
}

function upsertManagedLink(selector: string) {
  return upsertManagedElement<HTMLLinkElement>(selector, () => document.createElement("link"));
}

function upsertManagedElement<T extends HTMLElement>(selector: string, createElement: () => T): T {
  const managedSelector = `${selector}[${SEO_MANAGED_ATTR}='true']`;
  const existing = document.head.querySelector<T>(managedSelector) ?? document.head.querySelector<T>(selector);
  if (existing) {
    existing.setAttribute(SEO_MANAGED_ATTR, "true");
    return existing;
  }
  const element = createElement();
  element.setAttribute(SEO_MANAGED_ATTR, "true");
  document.head.appendChild(element);
  return element;
}

function removeManaged(selector: string) {
  document.head.querySelectorAll(`${selector}[${SEO_MANAGED_ATTR}='true']`).forEach((element) => element.remove());
}

function cssEscape(value: string) {
  if (typeof CSS !== "undefined" && typeof CSS.escape === "function") {
    return CSS.escape(value);
  }
  return value.replace(/['"\\]/g, "\\$&");
}

function jsonLdNonce() {
  if (typeof document !== "undefined") {
    const configured = document.querySelector<HTMLMetaElement>("meta[name='csp-nonce']")?.content;
    if (configured) return configured;
  }
  return JSON_LD_NONCE_FALLBACK;
}
