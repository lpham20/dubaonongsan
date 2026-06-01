import { useEffect, useMemo, useState, type Dispatch, type SetStateAction } from "react";
import { Link } from "react-router-dom";
import { CalendarClock, Gauge, Sprout } from "./icons";
import { Breadcrumb } from "./Breadcrumb";
import { RelatedForecastWidget } from "./RelatedForecastWidget";
import { SeoHead } from "./SeoHead";
import { LoadingSkeleton } from "./LoadingSkeleton";
import { fetchGuideDetail, type GuidePost } from "../lib/api";
import { compactText, DEFAULT_OG_IMAGE, guidePath } from "../lib/seo";
import { useLanguage } from "../contexts/LanguageContext";
import { withLanguagePrefix } from "../lib/localizedRoutes";
import { useFetchOnce } from "../hooks/useFetchOnce";
import { trackEvent } from "../lib/analytics";
import { guideHeadingId } from "../lib/guideMarkdown";

const HOWTO_HEADINGS = [
  "Mục tiêu",
  "Khi nào áp dụng",
  "Cách làm tại vườn",
  "Theo dõi sau khi làm",
  "Lỗi cần tránh",
  "Goal",
  "Objective",
  "When to apply",
  "How to do it in the orchard",
  "Field steps",
  "Follow-up after application",
  "Common mistakes to avoid"
];
const HOWTO_HEADING_SET = new Set(HOWTO_HEADINGS.map((heading) => heading.toLowerCase()));
const SOURCE_LINE_PREFIXES = ["nguồn", "source", "references", "reference"];

type GuideBlock = {
  heading: string;
  id?: string;
  items: GuideContentItem[];
  body: string[];
  bullets: string[];
  tables: string[][][];
  images: { url: string; index: number }[];
};

type GuideContentItem =
  | { type: "subheading"; text: string; id: string; level: 3 | 4 }
  | { type: "paragraph"; text: string }
  | { type: "blockquote"; lines: string[] }
  | { type: "bullets"; items: string[] }
  | { type: "ordered"; items: string[] }
  | { type: "table"; rows: string[][] }
  | { type: "image"; url: string; index: number };

export function GuideDetailPage({ slug }: { slug: string }) {
  const { language } = useLanguage();
  const [guide, setGuide] = useState<GuidePost | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [retryKey, setRetryKey] = useState(0);

  useFetchOnce({
    deps: [language, slug, retryKey],
    load: (signal) => fetchGuideDetail(slug, signal, language),
    onData: setGuide,
    onError: () => setFailed(true),
    onFinally: () => setLoading(false),
    onReset: () => {
      setLoading(true);
      setFailed(false);
      setGuide(null);
    }
  });

  const schema = useMemo(() => (guide ? buildHowToSchema(guide, language) : undefined), [guide, language]);

  useEffect(() => {
    if (!guide?.post_id) return;
    trackEvent("guide_post_viewed", {
      post_id: guide.post_id,
      category: guide.category
    });
  }, [guide?.category, guide?.post_id]);

  if (loading) {
    const copy = guideDetailCopy[language];
    return (
      <section className="content-page detail-page">
        <Breadcrumb items={[{ label: copy.home, href: "/" }, { label: copy.guides, href: "/huong-dan" }]} />
        <LoadingSkeleton variant="article" label={copy.loading} rows={5} />
      </section>
    );
  }

  if (failed || !guide) {
    const copy = guideDetailCopy[language];
    return (
      <section className="content-page detail-page">
        <SeoHead title={copy.errorTitle} description={copy.errorDescription} canonical={`/huong-dan/${slug}`} />
        <Breadcrumb items={[{ label: copy.home, href: "/" }, { label: copy.guides, href: "/huong-dan" }, { label: copy.errorCrumb }]} />
        <h1>{copy.errorTitle}</h1>
        <p>{copy.errorBody}</p>
        <div className="detail-error-actions">
          <button type="button" className="detail-primary-link" onClick={() => setRetryKey((value) => value + 1)}>
            {copy.retry}
          </button>
          <Link className="detail-secondary-link" to={withLanguagePrefix("/huong-dan", language)}>
            {copy.backToGuides}
          </Link>
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
      <Breadcrumb items={[{ label: guideDetailCopy[language].home, href: "/" }, { label: guideDetailCopy[language].guides, href: "/huong-dan" }, { label: guide.title }]} />
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
              {language === "en" ? `${estimateReadingMinutes(guide.content)} min read` : `${estimateReadingMinutes(guide.content)} phút đọc`}
            </small>
            <small>
              <Gauge size={15} />
              {technicalDifficulty(guide.content, language)}
            </small>
            <small>{language === "en" ? "Updated " : "Cập nhật "}{formatDate(guide.published_at, language)}</small>
          </div>
        </header>
        <GuideArticleContent guide={guide} language={language} />
        <RelatedForecastWidget text={`${guide.title} ${guide.summary} ${guide.category}`} />
      </article>
    </section>
  );
}

function GuideArticleContent({ guide, language }: { guide: GuidePost; language: "vi" | "en" }) {
  const blocks = safeParseGuideBlocks(guide, language);
  const [failedImages, setFailedImages] = useState<Set<number>>(() => new Set());
  return (
    <div className="detail-body guide-detail-body">
      {blocks.map((block) => (
        <section key={block.heading}>
          <h2 id={block.id}>{block.heading}</h2>
          {block.items.map((item, index) => renderGuideItem(item, index, guide, block.heading, failedImages, setFailedImages, language))}
        </section>
      ))}
    </div>
  );
}

function renderGuideItem(
  item: GuideContentItem,
  index: number,
  guide: GuidePost,
  heading: string,
  failedImages: Set<number>,
  setFailedImages: Dispatch<SetStateAction<Set<number>>>,
  language: "vi" | "en"
) {
  if (item.type === "subheading") {
    const HeadingTag = item.level === 4 ? "h4" : "h3";
    return <HeadingTag id={item.id} key={index}>{renderInlineMarkdown(item.text, language)}</HeadingTag>;
  }
  if (item.type === "paragraph") return <p key={index}>{renderInlineMarkdown(item.text, language)}</p>;
  if (item.type === "blockquote") {
    return (
      <blockquote key={index}>
        {item.lines.map((line, lineIndex) => (
          <p key={`${lineIndex}-${line}`}>{renderInlineMarkdown(line, language)}</p>
        ))}
      </blockquote>
    );
  }
  if (item.type === "bullets") {
    return (
      <ul key={index}>
        {item.items.map((bullet, bulletIndex) => (
          <li key={`${bulletIndex}-${bullet}`}>{renderInlineMarkdown(bullet, language)}</li>
        ))}
      </ul>
    );
  }
  if (item.type === "ordered") {
    return (
      <ol key={index}>
        {item.items.map((orderedItem, orderedIndex) => (
          <li key={`${orderedIndex}-${orderedItem}`}>{renderInlineMarkdown(orderedItem, language)}</li>
        ))}
      </ol>
    );
  }
  if (item.type === "table") return renderMarkdownTable(item.rows, index, language);
  if (failedImages.has(item.index)) return null;
  return (
    <img
      key={index}
      src={`/api/v1/content/guide-images/${guide.post_id}/${item.index}`}
      alt={language === "en" ? `Guide image: ${guide.title} - ${heading}` : `Ảnh hướng dẫn: ${guide.title} - ${heading}`}
      loading="lazy"
      decoding="async"
      width="860"
      height="480"
      onError={() => setFailedImages((current) => new Set(current).add(item.index))}
    />
  );
}

function buildHowToSchema(guide: GuidePost, language: "vi" | "en" = "vi") {
  const steps = safeParseGuideBlocks(guide, language)
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
    dateModified: guide.published_at,
    keywords: guide.tags,
    totalTime: `PT${estimateReadingMinutes(guide.content)}M`,
    supply: relatedSupplies(guide).map((name) => ({ "@type": "HowToSupply", name })),
    step: steps
  };
}

function safeParseGuideBlocks(guide: GuidePost, language: "vi" | "en" = "vi") {
  try {
    const blocks = parseGuideBlocks(guide.content);
    return blocks.length ? blocks : [{ heading: language === "en" ? "Technical note" : "Ghi chú kỹ thuật", items: [{ type: "paragraph" as const, text: guide.summary }], body: [guide.summary], bullets: [], tables: [], images: [] }];
  } catch {
    const fallbackText = guide.summary || guide.title;
    return [{ heading: language === "en" ? "Technical note" : "Ghi chú kỹ thuật", items: [{ type: "paragraph" as const, text: fallbackText }], body: [fallbackText], bullets: [], tables: [], images: [] }];
  }
}

function parseGuideBlocks(content: string): GuideBlock[] {
  const blocks: GuideBlock[] = [];
  let current: GuideBlock | null = null;
  let activeTable: string[][] | null = null;
  let activeBullets: string[] | null = null;
  let activeOrdered: string[] | null = null;
  let activeQuote: string[] | null = null;
  let imageIndex = 0;
  const lines = content
    .replace(/\r\n/g, "\n")
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => !SOURCE_LINE_PREFIXES.some((prefix) => line.toLowerCase().startsWith(prefix)));

  for (const line of lines) {
    if (!line) {
      activeTable = null;
      activeBullets = null;
      activeOrdered = null;
      activeQuote = null;
      continue;
    }
    const heading = normalizeGuideHeading(line);
    if (heading) {
      if (heading.level <= 2 || !current) {
        current = { heading: heading.text, id: heading.id, items: [], body: [], bullets: [], tables: [], images: [] };
        blocks.push(current);
      } else {
        const subheadingLevel = heading.level >= 4 ? 4 : 3;
        current.items.push({ type: "subheading", text: heading.text, id: heading.id, level: subheadingLevel });
        current.body.push(heading.text);
      }
      activeTable = null;
      activeBullets = null;
      activeOrdered = null;
      activeQuote = null;
      continue;
    }
    if (!current) {
      current = { heading: "Ghi chú kỹ thuật", items: [], body: [], bullets: [], tables: [], images: [] };
      blocks.push(current);
    }
    if (line.startsWith("|")) {
      const cells = parseTableRow(line);
      if (cells.length && !cells.every((cell) => /^:?-{3,}:?$/.test(cell))) {
        if (!activeTable) {
          activeTable = [];
          current.tables.push(activeTable);
          current.items.push({ type: "table", rows: activeTable });
        }
        activeTable.push(cells);
      }
      activeBullets = null;
      activeOrdered = null;
      activeQuote = null;
      continue;
    }
    activeTable = null;
    if (line.startsWith("IMAGE::")) {
      const image = { url: line.slice("IMAGE::".length).trim(), index: imageIndex++ };
      current.images.push(image);
      current.items.push({ type: "image", ...image });
      activeBullets = null;
      activeOrdered = null;
      activeQuote = null;
      continue;
    }
    if (line.startsWith(">")) {
      const quote = line.replace(/^>+\s*/, "").trim();
      if (quote) {
        current.body.push(quote);
        if (!activeQuote) {
          activeQuote = [];
          current.items.push({ type: "blockquote", lines: activeQuote });
        }
        activeQuote.push(quote);
      }
      activeBullets = null;
      activeOrdered = null;
      continue;
    }
    const orderedMatch = line.match(/^\d+\.\s+(.*)$/);
    if (orderedMatch) {
      const value = orderedMatch[1].trim();
      current.bullets.push(value);
      if (!activeOrdered) {
        activeOrdered = [];
        current.items.push({ type: "ordered", items: activeOrdered });
      }
      activeOrdered.push(value);
      activeBullets = null;
      activeQuote = null;
      continue;
    }
    if (line.startsWith("- ")) {
      const value = line.slice(2).trim();
      current.bullets.push(value);
      if (!activeBullets) {
        activeBullets = [];
        current.items.push({ type: "bullets", items: activeBullets });
      }
      activeBullets.push(value);
      activeOrdered = null;
      activeQuote = null;
      continue;
    }
    current.body.push(line);
    current.items.push({ type: "paragraph", text: line });
    activeBullets = null;
    activeOrdered = null;
    activeQuote = null;
  }
  return blocks;
}

function normalizeGuideHeading(line: string) {
  if (HOWTO_HEADING_SET.has(line.toLowerCase())) return { text: line, id: guideHeadingId(line), level: 2 as const };
  const match = line.match(/^(#{1,6})\s+(.+)$/);
  if (!match) return null;
  const level = Math.min(Math.max(match[1].length, 2), 4) as 2 | 3 | 4;
  const rawText = match[2].trim();
  const text = rawText
    .replace(/^\d+(?:\.\d+)?\.\s*/, "")
    .trim();
  return text ? { text, id: guideHeadingId(rawText), level } : null;
}

function parseTableRow(line: string) {
  return line
    .split("|")
    .map((cell) => cell.trim())
    .filter(Boolean);
}

function renderMarkdownTable(table: string[][], index: number, language: "vi" | "en") {
  if (!table.length) return null;
  const [head, ...rows] = table;
  return (
    <div className="guide-markdown-table" key={`table-${index}`}>
      <table>
        <thead>
          <tr>{head.map((cell) => <th key={cell}>{renderInlineMarkdown(cell, language)}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={`${rowIndex}-${row.join("|")}`}>
              {head.map((_, cellIndex) => <td key={cellIndex}>{renderInlineMarkdown(row[cellIndex] ?? "", language)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function renderInlineMarkdown(text: string, language: "vi" | "en" = "vi") {
  const cleaned = text.replace(/^\[[ xX]\]\s*/, "");
  const parts = cleaned.split(/(\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))/g).filter(Boolean);
  return parts.map((part, index) => {
    const link = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (link) {
      const [, label, href] = link;
      return href.startsWith("#") ? (
        <a href={href} key={`${part}-${index}`}>{label}</a>
      ) : href.startsWith("/") ? (
        <Link to={withLanguagePrefix(href, language)} key={`${part}-${index}`}>{label}</Link>
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

function technicalDifficulty(content: string, language: "vi" | "en" = "vi") {
  const normalized = content.toLowerCase();
  const score = ["phun", "bệnh", "sâu", "liều", "ppm", "nấm", "cắt tỉa", "xử lý"].filter((term) => normalized.includes(term)).length;
  if (language === "en") {
    if (score >= 4) return "Difficulty: advanced";
    if (score >= 2) return "Difficulty: intermediate";
    return "Difficulty: basic";
  }
  if (score >= 4) return "Độ khó: nâng cao";
  if (score >= 2) return "Độ khó: trung bình";
  return "Độ khó: cơ bản";
}

function formatDate(value: string, language: "vi" | "en" = "vi") {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return language === "en" ? "updating" : "Đang cập nhật";
  return new Intl.DateTimeFormat(language === "en" ? "en-US" : "vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" }).format(date);
}

const guideDetailCopy = {
  vi: {
    home: "Trang chủ",
    guides: "Hướng dẫn",
    loading: "Đang tải hướng dẫn kỹ thuật...",
    errorTitle: "Không tải được hướng dẫn",
    errorDescription: "Đường truyền yếu hoặc bài hướng dẫn tạm thời không khả dụng. Vui lòng thử lại.",
    errorCrumb: "Không tải được",
    errorBody: "Mạng có thể đang chậm hoặc bài viết tạm thời chưa sẵn sàng. Bạn có thể thử lại sau vài giây.",
    retry: "Thử lại",
    backToGuides: "Quay lại thư viện hướng dẫn"
  },
  en: {
    home: "Home",
    guides: "Guides",
    loading: "Loading the technical guide...",
    errorTitle: "Could not load this guide",
    errorDescription: "The connection is slow or this guide is temporarily unavailable. Please try again.",
    errorCrumb: "Could not load",
    errorBody: "The network may be slow or the article may not be ready yet. Please try again in a few seconds.",
    retry: "Try again",
    backToGuides: "Back to the guide library"
  }
} as const;
