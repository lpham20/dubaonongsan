import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { CalendarClock, Gauge, Sprout } from "./icons";
import { Breadcrumb } from "./Breadcrumb";
import { RelatedForecastWidget } from "./RelatedForecastWidget";
import { SeoHead } from "./SeoHead";
import { fetchGuideDetail, type GuidePost } from "../lib/api";
import { compactText, DEFAULT_OG_IMAGE, guidePath } from "../lib/seo";

const HOWTO_HEADINGS = ["Mục tiêu", "Khi nào áp dụng", "Cách làm tại vườn", "Theo dõi sau khi làm", "Lỗi cần tránh"];

type GuideBlock = {
  heading: string;
  body: string[];
  bullets: string[];
  tables: string[][][];
  images: { url: string; index: number }[];
};

export function GuideDetailPage({ slug }: { slug: string }) {
  const [guide, setGuide] = useState<GuidePost | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 8000);
    setLoading(true);
    setFailed(false);
    setGuide(null);
    fetchGuideDetail(slug, controller.signal)
      .then(setGuide)
      .catch((err) => {
        if (err?.name === "AbortError") {
          if (!controller.signal.aborted) setFailed(true);
          return;
        }
        console.error("[GuideDetailPage] fetch failed", { slug, err });
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

  const schema = useMemo(() => (guide ? buildHowToSchema(guide) : undefined), [guide]);

  if (loading) {
    return (
      <section className="content-page detail-page">
        <Breadcrumb items={[{ label: "Trang chủ", href: "/" }, { label: "Hướng dẫn", href: "/huong-dan" }]} />
        <div className="loading">Đang tải hướng dẫn kỹ thuật...</div>
      </section>
    );
  }

  if (failed || !guide) {
    return (
      <section className="content-page detail-page">
        <SeoHead title="Không tải được hướng dẫn" description="Đường truyền yếu hoặc bài hướng dẫn tạm thời không khả dụng. Vui lòng thử lại." canonical={`/huong-dan/${slug}`} />
        <Breadcrumb items={[{ label: "Trang chủ", href: "/" }, { label: "Hướng dẫn", href: "/huong-dan" }, { label: "Không tải được" }]} />
        <h1>Không tải được hướng dẫn</h1>
        <p>Mạng có thể đang chậm hoặc bài viết tạm thời chưa sẵn sàng. Bạn có thể thử lại sau vài giây.</p>
        <div className="detail-error-actions">
          <button type="button" className="detail-primary-link" onClick={() => setRetryKey((value) => value + 1)}>
            Thử lại
          </button>
          <Link className="detail-secondary-link" to="/huong-dan">Quay lại thư viện hướng dẫn</Link>
        </div>
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
  const blocks = safeParseGuideBlocks(guide);
  return (
    <div className="detail-body guide-detail-body">
      {blocks.map((block) => (
        <section key={block.heading}>
          <h2>{block.heading}</h2>
          {block.body.map((paragraph, index) => (
            <p key={index}>{renderInlineMarkdown(paragraph)}</p>
          ))}
          {block.tables.map((table, index) => renderMarkdownTable(table, index))}
          {block.bullets.length ? (
            <ul>
              {block.bullets.map((bullet) => (
                <li key={bullet}>{renderInlineMarkdown(bullet)}</li>
              ))}
            </ul>
          ) : null}
          {block.images.map((image) => (
            <img
              key={image.index}
              src={`/api/v1/content/guide-images/${guide.post_id}/${image.index}`}
              alt={`Ảnh hướng dẫn: ${guide.title} - ${block.heading}`}
              loading="lazy"
              decoding="async"
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
  const steps = safeParseGuideBlocks(guide)
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

function safeParseGuideBlocks(guide: GuidePost) {
  try {
    const blocks = parseGuideBlocks(guide.content);
    return blocks.length ? blocks : [{ heading: "Ghi chú kỹ thuật", body: [guide.summary], bullets: [], tables: [], images: [] }];
  } catch (err) {
    console.error("[GuideDetailPage] parse failed", { slug: guide.slug, err });
    return [{ heading: "Ghi chú kỹ thuật", body: [guide.summary || guide.title], bullets: [], tables: [], images: [] }];
  }
}

function parseGuideBlocks(content: string) {
  const blocks: GuideBlock[] = [];
  let current: GuideBlock | null = null;
  let activeTable: string[][] | null = null;
  let imageIndex = 0;
  const lines = content
    .split(/\n+/)
    .map((line) => line.trim())
    .filter((line) => line && !line.toLowerCase().startsWith("nguồn"));

  for (const line of lines) {
    const heading = normalizeGuideHeading(line);
    if (heading) {
      current = { heading, body: [], bullets: [], tables: [], images: [] };
      blocks.push(current);
      activeTable = null;
      continue;
    }
    if (!current) {
      current = { heading: "Ghi chú kỹ thuật", body: [], bullets: [], tables: [], images: [] };
      blocks.push(current);
    }
    if (line.startsWith("|")) {
      const cells = parseTableRow(line);
      if (cells.length && !cells.every((cell) => /^:?-{3,}:?$/.test(cell))) {
        if (!activeTable) {
          activeTable = [];
          current.tables.push(activeTable);
        }
        activeTable.push(cells);
      }
      continue;
    }
    activeTable = null;
    if (line.startsWith("IMAGE::")) current.images.push({ url: line.slice("IMAGE::".length), index: imageIndex++ });
    else if (line.startsWith("- ")) current.bullets.push(line.slice(2));
    else current.body.push(line);
  }
  return blocks;
}

function normalizeGuideHeading(line: string) {
  if (HOWTO_HEADINGS.includes(line)) return line;
  if (!line.startsWith("#")) return null;
  const heading = line
    .replace(/^#{2,3}\s+/, "")
    .replace(/^\d+(?:\.\d+)?\.\s*/, "")
    .trim();
  return heading || null;
}

function parseTableRow(line: string) {
  return line
    .split("|")
    .map((cell) => cell.trim())
    .filter(Boolean);
}

function renderMarkdownTable(table: string[][], index: number) {
  if (!table.length) return null;
  const [head, ...rows] = table;
  return (
    <div className="guide-markdown-table" key={`table-${index}`}>
      <table>
        <thead>
          <tr>{head.map((cell) => <th key={cell}>{renderInlineMarkdown(cell)}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={`${rowIndex}-${row.join("|")}`}>
              {head.map((_, cellIndex) => <td key={cellIndex}>{renderInlineMarkdown(row[cellIndex] ?? "")}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function renderInlineMarkdown(text: string) {
  const cleaned = text.replace(/^\[[ xX]\]\s*/, "");
  const parts = cleaned.split(/(\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))/g).filter(Boolean);
  return parts.map((part, index) => {
    const link = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (link) {
      const [, label, href] = link;
      return href.startsWith("/") ? (
        <Link to={href} key={`${part}-${index}`}>{label}</Link>
      ) : (
        <a href={href} key={`${part}-${index}`} target="_blank" rel="noreferrer">{label}</a>
      );
    }
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={`${part}-${index}`}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
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
