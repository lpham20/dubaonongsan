import { Link } from "react-router-dom";
import { useLanguage } from "../contexts/LanguageContext";
import { safeJsonLd } from "../lib/jsonLd";
import { canonicalUrl } from "../lib/seo";
import { withLanguagePrefix } from "../lib/localizedRoutes";

type Item = {
  label: string;
  href?: string;
};

export function Breadcrumb({ items }: { items: Item[] }) {
  const { language } = useLanguage();
  const schema = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.label,
      item: item.href ? canonicalUrl(withLanguagePrefix(item.href, language)) : undefined
    }))
  };

  return (
    <>
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <ol>
          {items.map((item, index) => (
            <li key={`${item.label}-${index}`}>
              {item.href ? <Link to={withLanguagePrefix(item.href, language)}>{item.label}</Link> : <span>{item.label}</span>}
            </li>
          ))}
        </ol>
      </nav>
      <script type="application/ld+json" nonce="dubaonongsan-jsonld" dangerouslySetInnerHTML={{ __html: safeJsonLd(schema) }} />
    </>
  );
}
