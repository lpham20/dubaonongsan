import { Link } from "react-router-dom";
import { safeJsonLd } from "../lib/jsonLd";
import { canonicalUrl } from "../lib/seo";

type Item = {
  label: string;
  href?: string;
};

export function Breadcrumb({ items }: { items: Item[] }) {
  const schema = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.label,
      item: item.href ? canonicalUrl(item.href) : undefined
    }))
  };

  return (
    <>
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <ol>
          {items.map((item, index) => (
            <li key={`${item.label}-${index}`}>
              {item.href ? <Link to={item.href}>{item.label}</Link> : <span>{item.label}</span>}
            </li>
          ))}
        </ol>
      </nav>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: safeJsonLd(schema) }} />
    </>
  );
}
