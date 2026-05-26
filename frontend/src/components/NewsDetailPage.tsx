import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { CalendarDays, ExternalLink, Newspaper } from "./icons";
import { Breadcrumb } from "./Breadcrumb";
import { RelatedForecastWidget } from "./RelatedForecastWidget";
import { SeoHead } from "./SeoHead";
import { fetchNews, fetchNewsDetail, type NewsArticle } from "../lib/api";
import { compactText, DEFAULT_OG_IMAGE, newsPath } from "../lib/seo";
import { useLanguage } from "../contexts/LanguageContext";
import { withLanguagePrefix } from "../lib/localizedRoutes";

export function NewsDetailPage({ slug }: { slug: string }) {
  const { language } = useLanguage();
  const [article, setArticle] = useState<NewsArticle | null>(null);
  const [related, setRelated] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 20_000);
    setLoading(true);
    setFailed(false);
    setArticle(null);
    fetchNewsDetail(slug, controller.signal, language)
      .then(setArticle)
      .catch((err) => {
        if (err?.name === "AbortError") {
          if (!controller.signal.aborted) setFailed(true);
          return;
        }
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
  }, [language, slug, retryKey]);

  useEffect(() => {
    if (!article) return;
    const controller = new AbortController();
    fetchNews(controller.signal, language)
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
  }, [article, language]);

  const articleSchema = useMemo(() => {
    if (!article) return undefined;
    const copy = newsDetailCopy[language];
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
        name: copy.publisher,
        logo: {
          "@type": "ImageObject",
            url: "https://dubaonongsan.com/og-cover.jpg"
        }
      }
    };
  }, [article, language]);

  if (loading) {
    const copy = newsDetailCopy[language];
    return (
      <section className="content-page detail-page">
        <Breadcrumb items={[{ label: copy.home, href: "/" }, { label: copy.news, href: "/tin-tuc" }]} />
        <div className="loading">{copy.loading}</div>
      </section>
    );
  }

  if (failed || !article) {
    const copy = newsDetailCopy[language];
    return (
      <section className="content-page detail-page">
        <SeoHead title={copy.errorTitle} description={copy.errorDescription} canonical={`/tin-tuc/${slug}`} />
        <Breadcrumb items={[{ label: copy.home, href: "/" }, { label: copy.news, href: "/tin-tuc" }, { label: copy.errorCrumb }]} />
        <h1>{copy.errorTitle}</h1>
        <p>{copy.errorBody}</p>
        <div className="detail-error-actions">
          <button type="button" className="detail-primary-link" onClick={() => setRetryKey((value) => value + 1)}>
            {copy.retry}
          </button>
          <Link className="detail-secondary-link" to={withLanguagePrefix("/tin-tuc", language)}>
            {copy.backToNews}
          </Link>
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
      <Breadcrumb items={[{ label: newsDetailCopy[language].home, href: "/" }, { label: newsDetailCopy[language].news, href: "/tin-tuc" }, { label: article.category }]} />
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
            <span>{formatDate(article.published_at || article.scraped_at, language)}</span>
            <span>{article.source_name}</span>
          </div>
        </header>
        {article.image_url ? (
          <img
            className="detail-hero-image"
            src={article.image_url}
            alt={language === "en" ? `Illustration: ${article.title}` : `Ảnh minh họa: ${article.title}`}
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
        {related.length ? <RelatedNews articles={related} language={language} /> : null}
        <a className="detail-primary-link" href={article.source_url} target="_blank" rel="noreferrer">
          {language === "en" ? `Read the original article at ${article.source_name}` : `Đọc bài gốc tại ${article.source_name}`}
          <ExternalLink size={16} />
        </a>
      </article>
    </section>
  );
}

function RelatedNews({ articles, language }: { articles: NewsArticle[]; language: "vi" | "en" }) {
  return (
    <aside aria-label={language === "en" ? "Related news" : "Tin liên quan"} className="related-news">
      <h2>{language === "en" ? "Related news" : "Tin liên quan"}</h2>
      <ul>
        {articles.map((item) => (
          <li key={item.article_id}>
            <Link to={withLanguagePrefix(newsPath(item), language)}>{item.title}</Link>
            <small>{item.category} · {formatDate(item.published_at || item.scraped_at, language)}</small>
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

function formatDate(value: string | null, language: "vi" | "en" = "vi") {
  if (!value) return language === "en" ? "Updating" : "Đang cập nhật";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return language === "en" ? "Updating" : "Đang cập nhật";
  return new Intl.DateTimeFormat(language === "en" ? "en-US" : "vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" }).format(date);
}

const newsDetailCopy = {
  vi: {
    home: "Trang chủ",
    news: "Tin tức",
    publisher: "Dự báo nông sản",
    loading: "Đang tải bài tin...",
    errorTitle: "Không tải được bài tin",
    errorDescription: "Đường truyền yếu hoặc bài tin tạm thời không khả dụng. Vui lòng thử lại.",
    errorCrumb: "Không tải được",
    errorBody: "Mạng có thể đang chậm hoặc bài tin tạm thời chưa sẵn sàng. Bạn có thể thử lại sau vài giây.",
    retry: "Thử lại",
    backToNews: "Quay lại bản tin thị trường"
  },
  en: {
    home: "Home",
    news: "News",
    publisher: "Agri Price Forecast",
    loading: "Loading this article...",
    errorTitle: "Could not load this article",
    errorDescription: "The connection is slow or this article is temporarily unavailable. Please try again.",
    errorCrumb: "Could not load",
    errorBody: "The network may be slow or the article may not be ready yet. Please try again in a few seconds.",
    retry: "Try again",
    backToNews: "Back to market news"
  }
} as const;
