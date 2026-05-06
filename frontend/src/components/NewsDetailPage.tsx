import { useEffect, useMemo, useState } from "react";
import { CalendarDays, ExternalLink, Newspaper } from "./icons";
import { Breadcrumb } from "./Breadcrumb";
import { RelatedForecastWidget } from "./RelatedForecastWidget";
import { SeoHead } from "./SeoHead";
import { fetchNewsDetail, type NewsArticle } from "../lib/api";
import { compactText, DEFAULT_OG_IMAGE, newsPath } from "../lib/seo";

export function NewsDetailPage({ slug }: { slug: string }) {
  const [article, setArticle] = useState<NewsArticle | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setFailed(false);
    fetchNewsDetail(slug, controller.signal)
      .then(setArticle)
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [slug]);

  const articleSchema = useMemo(() => {
    if (!article) return undefined;
    return {
      "@context": "https://schema.org",
      "@type": "NewsArticle",
      headline: article.title,
      description: compactText(article.summary || article.excerpt || article.title, 180),
      image: article.image_url || DEFAULT_OG_IMAGE,
      datePublished: article.published_at || article.scraped_at,
      dateModified: article.scraped_at,
      mainEntityOfPage: newsPath(article),
      author: {
        "@type": "Organization",
        name: article.source_name
      },
      publisher: {
        "@type": "Organization",
        name: "Dự báo nông sản",
        logo: {
          "@type": "ImageObject",
            url: "https://dubaonongsan.com/og-cover.jpg"
        }
      }
    };
  }, [article]);

  if (loading) {
    return <section className="content-page detail-page"><div className="loading">Đang tải bài tin...</div></section>;
  }

  if (failed || !article) {
    return (
      <section className="content-page detail-page">
        <SeoHead title="Không tìm thấy bài tin" description="Bài tin bạn đang tìm không tồn tại hoặc đã được cập nhật." canonical="/tin-tuc" />
        <Breadcrumb items={[{ label: "Trang chủ", href: "/" }, { label: "Tin tức", href: "/tin-tuc" }, { label: "Không tìm thấy" }]} />
        <h1>Không tìm thấy bài tin</h1>
        <p>Bài tin có thể đã được cập nhật hoặc không còn nằm trong kho dữ liệu.</p>
        <a className="detail-primary-link" href="/tin-tuc">Quay lại bản tin thị trường</a>
      </section>
    );
  }

  const body = article.excerpt || article.summary;

  return (
    <section className="content-page detail-page news-detail-page">
      <SeoHead
        title={article.title}
        description={article.summary || article.excerpt || article.title}
        canonical={newsPath(article)}
        image={article.image_url || DEFAULT_OG_IMAGE}
        type="article"
        publishedAt={article.published_at || article.scraped_at}
        schemaJsonLd={articleSchema}
      />
      <Breadcrumb items={[{ label: "Trang chủ", href: "/" }, { label: "Tin tức", href: "/tin-tuc" }, { label: article.category }]} />
      <article className="detail-article">
        <header>
          <span className="detail-kicker">
            <Newspaper size={17} />
            {article.category}
          </span>
          <h1>{article.title}</h1>
          <p>{article.summary}</p>
          <div className="detail-meta">
            <CalendarDays size={16} />
            <span>{formatDate(article.published_at || article.scraped_at)}</span>
            <span>{article.source_name}</span>
          </div>
        </header>
        {article.image_url ? (
          <img
            className="detail-hero-image"
            src={article.image_url}
            alt={`Ảnh minh họa: ${article.title}`}
            loading="eager"
            width="960"
            height="540"
          />
        ) : null}
        <div className="detail-body">
          {body.split(/\n+/).filter(Boolean).map((paragraph, index) => (
            <p key={index}>{paragraph}</p>
          ))}
        </div>
        <RelatedForecastWidget text={`${article.title} ${article.summary} ${article.category}`} />
        <a className="detail-primary-link" href={article.source_url} target="_blank" rel="noreferrer">
          Đọc bài gốc tại {article.source_name}
          <ExternalLink size={16} />
        </a>
      </article>
    </section>
  );
}

function formatDate(value: string | null) {
  if (!value) return "Đang cập nhật";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Đang cập nhật";
  return new Intl.DateTimeFormat("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" }).format(date);
}
