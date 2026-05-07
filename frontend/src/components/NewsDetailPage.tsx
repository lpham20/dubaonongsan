import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { CalendarDays, ExternalLink, Newspaper } from "./icons";
import { Breadcrumb } from "./Breadcrumb";
import { RelatedForecastWidget } from "./RelatedForecastWidget";
import { SeoHead } from "./SeoHead";
import { fetchNews, fetchNewsDetail, type NewsArticle } from "../lib/api";
import { compactText, DEFAULT_OG_IMAGE, newsPath } from "../lib/seo";

export function NewsDetailPage({ slug }: { slug: string }) {
  const [article, setArticle] = useState<NewsArticle | null>(null);
  const [related, setRelated] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 8000);
    setLoading(true);
    setFailed(false);
    setArticle(null);
    fetchNewsDetail(slug, controller.signal)
      .then(setArticle)
      .catch((err) => {
        if (err?.name === "AbortError") {
          if (!controller.signal.aborted) setFailed(true);
          return;
        }
        console.error("[NewsDetailPage] fetch failed", { slug, err });
        if (!controller.signal.aborted) setFailed(true);
      })
      .finally(() => {
        window.clearTimeout(timeoutId);
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => {
      window.clearTimeout(timeoutId);
      controller.abort();
    };
  }, [slug, retryKey]);

  useEffect(() => {
    if (!article) return;
    const controller = new AbortController();
    fetchNews(controller.signal)
      .then((items) => {
        const articleText = normalizeTopicText(`${article.title} ${article.summary} ${article.category}`);
        setRelated(
          items
            .filter((item) => item.article_id !== article.article_id)
            .filter((item) => {
              if (item.category === article.category) return true;
              const text = normalizeTopicText(`${item.title} ${item.summary} ${item.category}`);
              return ["ca phe", "sau rieng", "ho tieu", "lua", "phan bon", "xuat khau", "chinh sach"].some(
                (term) => articleText.includes(term) && text.includes(term)
              );
            })
            .slice(0, 5)
        );
      })
      .catch(() => {
        if (!controller.signal.aborted) setRelated([]);
      });
    return () => controller.abort();
  }, [article]);

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
    return (
      <section className="content-page detail-page">
        <Breadcrumb items={[{ label: "Trang chủ", href: "/" }, { label: "Tin tức", href: "/tin-tuc" }]} />
        <div className="loading">Đang tải bài tin...</div>
      </section>
    );
  }

  if (failed || !article) {
    return (
      <section className="content-page detail-page">
        <SeoHead title="Không tải được bài tin" description="Đường truyền yếu hoặc bài tin tạm thời không khả dụng. Vui lòng thử lại." canonical={`/tin-tuc/${slug}`} />
        <Breadcrumb items={[{ label: "Trang chủ", href: "/" }, { label: "Tin tức", href: "/tin-tuc" }, { label: "Không tải được" }]} />
        <h1>Không tải được bài tin</h1>
        <p>Mạng có thể đang chậm hoặc bài tin tạm thời chưa sẵn sàng. Bạn có thể thử lại sau vài giây.</p>
        <div className="detail-error-actions">
          <button type="button" className="detail-primary-link" onClick={() => setRetryKey((value) => value + 1)}>
            Thử lại
          </button>
          <Link className="detail-secondary-link" to="/tin-tuc">Quay lại bản tin thị trường</Link>
        </div>
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
            fetchPriority="high"
            decoding="async"
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
        {related.length ? <RelatedNews articles={related} /> : null}
        <a className="detail-primary-link" href={article.source_url} target="_blank" rel="noreferrer">
          Đọc bài gốc tại {article.source_name}
          <ExternalLink size={16} />
        </a>
      </article>
    </section>
  );
}

function RelatedNews({ articles }: { articles: NewsArticle[] }) {
  return (
    <aside aria-label="Tin liên quan" className="related-news">
      <h2>Tin liên quan</h2>
      <ul>
        {articles.map((item) => (
          <li key={item.article_id}>
            <Link to={newsPath(item)}>{item.title}</Link>
            <small>{item.category} · {formatDate(item.published_at || item.scraped_at)}</small>
          </li>
        ))}
      </ul>
    </aside>
  );
}

function normalizeTopicText(value: string) {
  return value
    .toLocaleLowerCase("vi-VN")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function formatDate(value: string | null) {
  if (!value) return "Đang cập nhật";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Đang cập nhật";
  return new Intl.DateTimeFormat("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" }).format(date);
}
