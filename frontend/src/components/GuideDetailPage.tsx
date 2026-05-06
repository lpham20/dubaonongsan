import { useEffect, useMemo, useState } from "react";
import { CalendarClock, Gauge, Sprout } from "./icons";
import { Breadcrumb } from "./Breadcrumb";
import { RelatedForecastWidget } from "./RelatedForecastWidget";
import { SeoHead } from "./SeoHead";
import { fetchGuideDetail, type GuidePost } from "../lib/api";
import { compactText, DEFAULT_OG_IMAGE, guidePath } from "../lib/seo";

const HOWTO_HEADINGS = ["Mục tiêu", "Khi nào áp dụng", "Cách làm tại vườn", "Theo dõi sau khi làm", "Lỗi cần tránh"];

export function GuideDetailPage({ slug }: { slug: string }) {
  const [guide, setGuide] = useState<GuidePost | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setFailed(false);
    fetchGuideDetail(slug, controller.signal)
      .then(setGuide)
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [slug]);

  useEffect(() => {
    if (!guide) return;
    const canonicalPath = guidePath(guide.slug);
    if (window.location.pathname !== canonicalPath) {
      window.history.replaceState(null, "", canonicalPath);
    }
  }, [guide]);

  const schema = useMemo(() => (guide ? buildHowToSchema(guide) : undefined), [guide]);

  if (loading) {
    return <section className="content-page detail-page"><div className="loading">Đang tải hướng dẫn kỹ thuật...</div></section>;
  }

  if (failed || !guide) {
    return (
      <section className="content-page detail-page">
        <SeoHead title="Không tìm thấy hướng dẫn" description="Bài hướng dẫn kỹ thuật không tồn tại hoặc đã được cập nhật." canonical="/huong-dan" />
        <Breadcrumb items={[{ label: "Trang chủ", href: "/" }, { label: "Hướng dẫn", href: "/huong-dan" }, { label: "Không tìm thấy" }]} />
        <h1>Không tìm thấy hướng dẫn</h1>
        <p>Bài hướng dẫn có thể đã được đổi đường dẫn hoặc chưa có trong thư viện.</p>
        <a className="detail-primary-link" href="/huong-dan">Quay lại thư viện hướng dẫn</a>
      </section>
    );
  }

  return (
    <section className="content-page detail-page guide-detail-page">
      <SeoHead
        title={guide.title}
        description={guide.summary}
        canonical={guidePath(guide.slug)}
        image={DEFAULT_OG_IMAGE}
        type="article"
        publishedAt={guide.published_at}
        schemaJsonLd={schema}
      />
      <Breadcrumb items={[{ label: "Trang chủ", href: "/" }, { label: "Hướng dẫn", href: "/huong-dan" }, { label: guide.title }]} />
      <article className="detail-article">
        <header>
          <span className="detail-kicker">
            <Sprout size={17} />
            {guide.category}
          </span>
          <h1>{guide.title}</h1>
          <p>{guide.summary}</p>
          <div className="guide-meta-grid detail-guide-meta">
            <small>
              <CalendarClock size={15} />
              {estimateReadingMinutes(guide.content)} phút đọc
            </small>
            <small>
              <Gauge size={15} />
              {technicalDifficulty(guide.content)}
            </small>
            <small>Cập nhật {formatDate(guide.published_at)}</small>
          </div>
        </header>
        <GuideArticleContent guide={guide} />
        <RelatedForecastWidget text={`${guide.title} ${guide.summary} ${guide.category}`} />
      </article>
    </section>
  );
}

function GuideArticleContent({ guide }: { guide: GuidePost }) {
  const blocks = parseGuideBlocks(guide.content);
  return (
    <div className="detail-body guide-detail-body">
      {blocks.map((block) => (
        <section key={block.heading}>
          <h2>{block.heading}</h2>
          {block.body.map((paragraph, index) => (
            <p key={index}>{paragraph}</p>
          ))}
          {block.bullets.length ? (
            <ul>
              {block.bullets.map((bullet) => (
                <li key={bullet}>{bullet}</li>
              ))}
            </ul>
          ) : null}
          {block.images.map((image) => (
            <img
              key={image.index}
              src={`/api/v1/content/guide-images/${guide.post_id}/${image.index}`}
              alt={`Ảnh hướng dẫn: ${guide.title} - ${block.heading}`}
              loading="lazy"
              width="860"
              height="480"
              onError={(event) => {
                event.currentTarget.style.display = "none";
              }}
            />
          ))}
        </section>
      ))}
    </div>
  );
}

function buildHowToSchema(guide: GuidePost) {
  const steps = parseGuideBlocks(guide.content)
    .filter((block) => block.body.length || block.bullets.length)
    .slice(0, 8)
    .map((block) => ({
      "@type": "HowToStep",
      name: block.heading,
      text: compactText([...block.body, ...block.bullets].join(" "), 360)
    }));

  return {
    "@context": "https://schema.org",
    "@type": "HowTo",
    name: guide.title,
    description: guide.summary,
    image: DEFAULT_OG_IMAGE,
    datePublished: guide.published_at,
    totalTime: `PT${estimateReadingMinutes(guide.content)}M`,
    supply: relatedSupplies(guide).map((name) => ({ "@type": "HowToSupply", name })),
    step: steps
  };
}

function parseGuideBlocks(content: string) {
  const blocks: { heading: string; body: string[]; bullets: string[]; images: { url: string; index: number }[] }[] = [];
  let current: { heading: string; body: string[]; bullets: string[]; images: { url: string; index: number }[] } | null = null;
  let imageIndex = 0;
  const lines = content
    .split(/\n+/)
    .map((line) => line.trim())
    .filter((line) => line && !line.toLowerCase().startsWith("nguồn"));

  for (const line of lines) {
    if (HOWTO_HEADINGS.includes(line)) {
      current = { heading: line, body: [], bullets: [], images: [] };
      blocks.push(current);
      continue;
    }
    if (!current) {
      current = { heading: "Ghi chú kỹ thuật", body: [], bullets: [], images: [] };
      blocks.push(current);
    }
    if (line.startsWith("IMAGE::")) current.images.push({ url: line.slice("IMAGE::".length), index: imageIndex++ });
    else if (line.startsWith("- ")) current.bullets.push(line.slice(2));
    else current.body.push(line);
  }
  return blocks;
}

function relatedSupplies(guide: GuidePost) {
  const text = `${guide.title} ${guide.summary} ${guide.content}`.toLowerCase();
  const supplies = new Set<string>();
  if (text.includes("bệnh") || text.includes("nấm")) supplies.add("Sổ ghi nhận sâu bệnh");
  if (text.includes("tỉa") || text.includes("cắt")) supplies.add("Kéo cắt tỉa đã khử trùng");
  if (text.includes("tưới") || text.includes("nước")) supplies.add("Thiết bị đo ẩm đất");
  if (!supplies.size) supplies.add("Sổ theo dõi vườn");
  return Array.from(supplies);
}

function estimateReadingMinutes(content: string) {
  const words = content.replace(/IMAGE::\S+/g, "").trim().split(/\s+/).filter(Boolean).length;
  return Math.max(2, Math.ceil(words / 230));
}

function technicalDifficulty(content: string) {
  const normalized = content.toLowerCase();
  const score = ["phun", "bệnh", "sâu", "liều", "ppm", "nấm", "cắt tỉa", "xử lý"].filter((term) => normalized.includes(term)).length;
  if (score >= 4) return "Độ khó: nâng cao";
  if (score >= 2) return "Độ khó: trung bình";
  return "Độ khó: cơ bản";
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Đang cập nhật";
  return new Intl.DateTimeFormat("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" }).format(date);
}
