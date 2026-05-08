import {
  ArrowRight,
  BarChart3,
  Bell,
  BookOpenCheck,
  ChevronDown,
  Clock3,
  Coffee,
  Newspaper,
  Search,
  ShieldAlert,
  Sprout,
  TrendingDown,
  TrendingUp
} from "./icons";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { FreshnessBanner } from "./FreshnessBanner";
import { SeoHead } from "./SeoHead";
import { fetchTickerPrices, type CropType, type GuidePost, type NewsArticle, type PricePoint } from "../lib/api";
import { newsPath } from "../lib/seo";

type Props = {
  news: NewsArticle[];
  guides: GuidePost[];
  onOpenAnalytics: (crop: CropType) => void;
  onOpenNews: () => void;
  onOpenGuides: () => void;
};

type MarketCard = {
  label: string;
  sublabel: string;
  value: string;
  change: string;
  tone: "up" | "down";
  points: number[];
};

type TickerItem = {
  label: string;
  value: string;
  change: string;
  tone: "up" | "down";
};

type HomeTickerState = {
  coffee: PricePoint[];
  durian: PricePoint[];
  pepper: PricePoint[];
  rice: PricePoint[];
};

const fallbackTicker: TickerItem[] = [
  { label: "Cà phê Robusta Tây Nguyên", value: "87.800 đ/kg", change: "+1,2%", tone: "up" },
  { label: "Sầu riêng Ri6 Tiền Giang", value: "86.000 đ/kg", change: "+0,8%", tone: "up" },
  { label: "Hồ tiêu Đắk Lắk", value: "145.000 đ/kg", change: "+0,9%", tone: "up" },
  { label: "Lúa OM 5451 Đồng Tháp", value: "7.800 đ/kg", change: "-0,2%", tone: "down" },
  { label: "Sầu Thái Dona", value: "104.000 đ/kg", change: "-0,6%", tone: "down" },
  { label: "Urea hạt đục", value: "12.400 đ/kg", change: "-0,4%", tone: "down" },
  { label: "USD/VND xuất khẩu", value: "25.480", change: "+0,1%", tone: "up" }
] ;

const fallbackMarketCards: MarketCard[] = [
  {
    label: "Cà phê Robusta",
    sublabel: "Tây Nguyên",
    value: "87.800 đ/kg",
    change: "+1,2%",
    tone: "up",
    points: [42, 43, 43, 45, 47, 46, 48, 50, 51, 53, 55]
  },
  {
    label: "Sầu riêng Ri6",
    sublabel: "ĐBSCL",
    value: "86.000 đ/kg",
    change: "+0,8%",
    tone: "up",
    points: [38, 37, 39, 41, 40, 43, 42, 44, 46, 45, 47]
  },
  {
    label: "Sầu Thái Dona",
    sublabel: "Đông Nam Bộ",
    value: "104.000 đ/kg",
    change: "-0,6%",
    tone: "down",
    points: [64, 63, 62, 60, 61, 58, 57, 56, 55, 54, 53]
  },
  {
    label: "Hồ tiêu đen",
    sublabel: "Đông Nam Bộ",
    value: "145.000 đ/kg",
    change: "+0,9%",
    tone: "up",
    points: [48, 49, 48, 50, 51, 53, 52, 54, 55, 57, 58]
  },
  {
    label: "Lúa OM 5451",
    sublabel: "ĐBSCL",
    value: "7.800 đ/kg",
    change: "-0,2%",
    tone: "down",
    points: [34, 35, 34, 33, 34, 32, 31, 32, 30, 30, 29]
  },
  {
    label: "Lúa ST25",
    sublabel: "Cần Thơ",
    value: "10.800 đ/kg",
    change: "+0,7%",
    tone: "up",
    points: [36, 37, 38, 37, 39, 40, 41, 40, 42, 43, 44]
  },
  {
    label: "Tiêu đen",
    sublabel: "Lâm Đồng",
    value: "145.000 đ/kg",
    change: "+1,4%",
    tone: "up",
    points: [50, 51, 50, 52, 53, 52, 54, 55, 56, 55, 58]
  },
  {
    label: "Tiêu trắng",
    sublabel: "Đồng Nai",
    value: "208.000 đ/kg",
    change: "+0,6%",
    tone: "up",
    points: [62, 61, 63, 64, 65, 64, 66, 67, 68, 67, 69]
  }
];

const fallbackNews: NewsArticle[] = [
  {
    article_id: -1,
    source_name: "Bản tin thị trường",
    source_url: "#",
    title: "Cà phê giữ vùng giá cao, doanh nghiệp xuất khẩu theo dõi sát biến động USD",
    summary:
      "Giá cà phê tiếp tục được hỗ trợ bởi nhu cầu xuất khẩu, trong khi biến động tỷ giá và chi phí logistics vẫn là biến số cần theo dõi.",
    excerpt: null,
    category: "Cà phê",
    image_url: "/coffee-hero-photo.jpg",
    published_at: null,
    scraped_at: new Date().toISOString()
  },
  {
    article_id: -2,
    source_name: "Bản tin thị trường",
    source_url: "#",
    title: "Sầu riêng vào nhịp thu hoạch mới, chênh lệch giá theo vùng bắt đầu nới rộng",
    summary:
      "Nguồn cung tăng dần tại một số vùng trồng, khiến giá cần được đọc theo giống, độ già trái và khả năng đi đơn xuất khẩu.",
    excerpt: null,
    category: "Sầu riêng",
    image_url: "/durian-hero-photo.jpg",
    published_at: null,
    scraped_at: new Date().toISOString()
  }
];

export function HomePage({ news, guides, onOpenAnalytics, onOpenNews, onOpenGuides }: Props) {
  const [liveTicker, setLiveTicker] = useState<HomeTickerState>({ coffee: [], durian: [], pepper: [], rice: [] });
  const [searchQuery, setSearchQuery] = useState("");
  const articles = useMemo(() => rankHomeArticles(news.length ? news : fallbackNews), [news]);
  const lead = articles[0];
  const leadImageUrl = lead.image_url || "/coffee-hero-photo.jpg";
  const leadWebpUrl = localWebpSource(leadImageUrl);
  const marketAlerts = articles.slice(1, 6);
  const guidePreview = guides.slice(0, 3);
  const tickerItems = useMemo(() => buildTickerItems(liveTicker), [liveTicker]);
  const dataCards = useMemo(() => buildMarketCards(liveTicker), [liveTicker]);

  useEffect(() => {
    let active = true;

    Promise.all([
      fetchTickerPrices("ca_phe"),
      fetchTickerPrices("sau_rieng"),
      fetchTickerPrices("ho_tieu"),
      fetchTickerPrices("lua")
    ])
      .then(([coffee, durian, pepper, rice]) => {
        if (active) {
          setLiveTicker({ coffee, durian, pepper, rice });
        }
      })
      .catch(() => {
        if (active) {
          setLiveTicker({ coffee: [], durian: [], pepper: [], rice: [] });
        }
      });

    return () => {
      active = false;
    };
  }, []);

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = searchQuery.trim();
    if (query) {
      window.location.href = `/tin-tuc?q=${encodeURIComponent(query)}`;
    }
  }

  return (
    <section className="home-page finance-home">
      <SeoHead
        title="Dự báo giá nông sản & hướng dẫn kỹ thuật Việt Nam"
        description="Cập nhật giá cà phê, sầu riêng, hồ tiêu, lúa hằng ngày. Dự báo 30 ngày theo vùng trồng, bản tin thị trường và hướng dẫn kỹ thuật nông nghiệp."
        canonical="/"
        schemaJsonLd={{
          "@context": "https://schema.org",
          "@type": "WebPage",
          name: "Dự báo nông sản",
          url: "https://dubaonongsan.com/",
          description: "Nền tảng tin tức, kỹ thuật và dự báo giá nông sản Việt Nam",
          speakable: {
            "@type": "SpeakableSpecification",
            cssSelector: [".home-market-hero h1", ".home-market-hero p"]
          }
        }}
      />
      <PriceTicker items={tickerItems} />

      <section className="home-market-hero">
        <div className="home-hero-copy">
          <span className="home-kicker">
            <Sprout size={18} />
            Dự báo nông sản
          </span>
          <h1>Nền tảng tri thức và dự báo thị trường nông nghiệp toàn diện</h1>

          <form className="home-quick-search" role="search" onSubmit={handleSearch}>
            <Search size={19} />
            <input
              name="q"
              aria-label="Tìm nhanh cây trồng hoặc tin thị trường"
              placeholder="Tìm nhanh: cà phê, sầu riêng, phân bón..."
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
            />
            <button className="home-search-filter" type="submit">
              Tìm tin
            </button>
            <button className="home-search-filter" type="button" onClick={onOpenNews}>
              Tin thị trường
              <ChevronDown size={15} />
            </button>
          </form>

          <div className="home-hero-actions">
            <button type="button" onClick={() => onOpenAnalytics("sau_rieng")}>
              Dự báo sầu riêng
              <ArrowRight size={17} />
            </button>
            <button type="button" onClick={() => onOpenAnalytics("ca_phe")}>
              Dự báo cà phê
              <ArrowRight size={17} />
            </button>
            <button type="button" onClick={() => onOpenAnalytics("ho_tieu")}>
              Dự báo hồ tiêu
              <ArrowRight size={17} />
            </button>
            <button type="button" onClick={() => onOpenAnalytics("lua")}>
              Dự báo lúa
              <ArrowRight size={17} />
            </button>
          </div>
        </div>

        <aside className="home-hero-terminal" aria-label="Tóm tắt thị trường">
          <div>
            <span>Bàn dữ liệu</span>
            <strong>4 nhóm dữ liệu đang theo dõi</strong>
          </div>
          <dl>
            <div>
              <dt>Giá nông sản</dt>
              <dd>Cà phê, sầu riêng, hồ tiêu, lúa</dd>
            </div>
            <div>
              <dt>Vật tư</dt>
              <dd>Phân bón, chi phí đầu vào</dd>
            </div>
            <div>
              <dt>Tin tác động</dt>
              <dd>Xuất khẩu, chính sách, thời tiết</dd>
            </div>
          </dl>
        </aside>
      </section>

      <div className="market-card-freshness">
        <FreshnessBanner />
      </div>

      <section className="market-card-grid" aria-label="Biến động giá nông sản">
        {dataCards.map((card) => (
          <article className={`market-data-card ${card.tone}`} key={card.label}>
            <div className="market-card-head">
              <span>{card.label}</span>
              {card.tone === "up" ? <TrendingUp size={18} /> : <TrendingDown size={18} />}
            </div>
            <strong className="num">{card.value}</strong>
            <div className="market-card-meta">
              <small>{card.sublabel}</small>
              <em className="num">{card.change}</em>
            </div>
            <Sparkline points={card.points} tone={card.tone} />
          </article>
        ))}
      </section>

      <section className="home-intel-grid">
        <article className="lead-market-story">
          <div className="lead-market-image">
            <picture>
              {leadWebpUrl ? <source srcSet={leadWebpUrl} type="image/webp" /> : null}
              <img
                src={leadImageUrl}
                alt={`Ảnh minh họa: ${lead.title}`}
                fetchPriority="high"
                decoding="async"
                width="800"
                height="450"
                onError={(event) => {
                  event.currentTarget.src = "/coffee-hero-photo.jpg";
                }}
              />
            </picture>
          </div>
          <div className="lead-market-copy">
            <span className="story-label">
              <Newspaper size={16} />
              Tin tiêu điểm
            </span>
            <h2>{displayTitle(lead.title, 96)}</h2>
            <p>{displayTitle(lead.summary || lead.excerpt || "Bản tin đang được cập nhật.", 190)}</p>
            <div className="story-meta">
              <Clock3 size={15} />
              <span>{formatDate(lead.published_at || lead.scraped_at)}</span>
              <span>{lead.source_name}</span>
            </div>
            <Link className="story-link" to={lead.source_url === "#" ? "/tin-tuc" : newsPath(lead)}>
              Đọc bản tin
              <ArrowRight size={16} />
            </Link>
          </div>
        </article>

        <aside className="market-alert-panel">
          <div className="panel-heading">
            <ShieldAlert size={18} />
            <h2>Cảnh báo thị trường</h2>
          </div>
          <div className="alert-list">
            {marketAlerts.map((item) => (
              <Link to={item.source_url === "#" ? "/tin-tuc" : newsPath(item)} key={item.article_id}>
                <span>{item.category || "Thị trường"}</span>
                <strong>{displayTitle(item.title, 74)}</strong>
                <small>{formatDate(item.published_at || item.scraped_at)}</small>
              </Link>
            ))}
          </div>
          <button type="button" onClick={onOpenNews}>
            Xem toàn bộ bản tin
            <ArrowRight size={16} />
          </button>
        </aside>
      </section>

      <section className="home-ops-strip">
        <button type="button" onClick={() => onOpenAnalytics("sau_rieng")}>
          <BarChart3 size={20} />
          <span>Dự báo giá</span>
          <strong>Mô hình 30/90/180 ngày</strong>
        </button>
        <button type="button" onClick={onOpenNews}>
          <Bell size={20} />
          <span>Bản tin thị trường</span>
          <strong>Tin giá, phân bón, chính sách</strong>
        </button>
        <button type="button" onClick={onOpenGuides}>
          <BookOpenCheck size={20} />
          <span>Quy trình kỹ thuật</span>
          <strong>{guidePreview.length ? `${guidePreview.length} hướng dẫn mới` : "Cẩm nang canh tác"}</strong>
        </button>
        <button type="button" onClick={() => onOpenAnalytics("ca_phe")}>
          <Coffee size={20} />
          <span>Hồ sơ hàng hóa</span>
          <strong>Cà phê, sầu riêng, hồ tiêu, lúa</strong>
        </button>
      </section>
    </section>
  );
}

function PriceTicker({ items }: { items: TickerItem[] }) {
  const repeated = [...items, ...items];

  return (
    <div className="home-price-ticker" aria-label="Dải băng giá nông sản">
      <div className="home-price-ticker-label">
        Giá trực tuyến
      </div>
      <div className="home-price-track">
        <div className="home-price-content">
          {repeated.map((item, index) => (
            <span key={`${item.label}-${index}`}>
              <strong>{item.label}</strong>
              <b>{item.value}</b>
              <em className={item.tone}>{item.change}</em>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function Sparkline({ points, tone }: { points: number[]; tone: "up" | "down" }) {
  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = Math.max(max - min, 1);
  const coords = points
    .map((point, index) => {
      const x = (index / (points.length - 1)) * 120;
      const y = 38 - ((point - min) / range) * 30;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const area = `0,42 ${coords} 120,42`;

  return (
    <svg className={`sparkline ${tone}`} viewBox="0 0 120 42" role="img" aria-label="Biểu đồ biến động nhỏ">
      <polygon points={area} />
      <polyline points={coords} />
    </svg>
  );
}

function buildTickerItems(live: HomeTickerState): TickerItem[] {
  if (!live.coffee.length && !live.durian.length && !live.pepper.length && !live.rice.length) return fallbackTicker;

  return [
    pointToTicker(live.coffee, "Cà phê Robusta", ["Robusta", "Culi", "Arabica"]) ?? fallbackTicker[0],
    pointToTicker(live.durian, "Sầu riêng", ["Ri6", "Dona", "Thái", "Musang", "Black Thorn"]) ?? fallbackTicker[1],
    pointToTicker(live.pepper, "Hồ tiêu", ["Tiêu đen", "Tiêu trắng", "Tiêu đỏ"]) ?? fallbackTicker[2],
    pointToTicker(live.rice, "Lúa", ["OM", "Đài thơm", "Nàng Hoa", "Jasmine"]) ?? fallbackTicker[3],
    fallbackTicker[5],
    fallbackTicker[6]
  ];
}

function buildMarketCards(live: HomeTickerState): MarketCard[] {
  if (!live.coffee.length && !live.durian.length && !live.pepper.length && !live.rice.length) return fallbackMarketCards;

  return [
    pointToCard(live.coffee, fallbackMarketCards[0], ["Robusta", "Culi"]),
    pointToCard(live.durian, fallbackMarketCards[1], ["Ri6", "Sầu"]),
    pointToCard(live.durian, fallbackMarketCards[2], ["Dona", "Thái", "Musang", "Black Thorn"]),
    pointToCard(live.pepper, fallbackMarketCards[3], ["Tiêu đen", "Tiêu trắng", "Tiêu đỏ"]),
    pointToCard(live.rice, fallbackMarketCards[4], ["OM", "Đài thơm", "Nàng Hoa", "Jasmine"]),
    pointToCard(live.rice, fallbackMarketCards[5], ["ST25"]),
    pointToCard(live.pepper, fallbackMarketCards[6], ["Tiêu đen"]),
    pointToCard(live.pepper, fallbackMarketCards[7], ["Tiêu trắng"])
  ];
}

function pointToTicker(points: PricePoint[], fallbackLabel: string, keywords: string[]): TickerItem | null {
  const selected = selectSeries(points, keywords);
  if (!selected.length) return null;
  const latest = selected[0];
  const change = computeChange(selected);
  const location = latest.province || latest.region;

  return {
    label: `${latest.variety || fallbackLabel}${location ? ` ${location}` : ""}`,
    value: formatPrice(pointPrice(latest)),
    change: formatChange(change),
    tone: change >= 0 ? "up" : "down"
  };
}

function pointToCard(points: PricePoint[], fallback: MarketCard, keywords: string[]): MarketCard {
  const selected = selectSeries(points, keywords);
  if (!selected.length) return fallback;
  const latest = selected[0];
  const change = computeChange(selected);
  const sparklinePoints = selected
    .slice(0, 11)
    .reverse()
    .map(pointPrice)
    .filter((value) => value > 0);

  return {
    label: latest.variety || fallback.label,
    sublabel: latest.province || latest.region || fallback.sublabel,
    value: formatPrice(pointPrice(latest)),
    change: formatChange(change),
    tone: change >= 0 ? "up" : "down",
    points: sparklinePoints.length >= 3 ? sparklinePoints : fallback.points
  };
}

function selectSeries(points: PricePoint[], keywords: string[]) {
  const normalizedKeywords = keywords.map((keyword) => normalizeText(keyword));
  const matched = points.filter((point) => {
    const name = normalizeText(point.variety);
    return normalizedKeywords.some((keyword) => name.includes(keyword));
  });
  return (matched.length ? matched : points)
    .filter((point) => pointPrice(point) > 0)
    .sort((left, right) => new Date(right.timestamp).getTime() - new Date(left.timestamp).getTime());
}

function pointPrice(point: PricePoint) {
  const min = point.min_price_vnd ?? point.max_price_vnd ?? 0;
  const max = point.max_price_vnd ?? point.min_price_vnd ?? 0;
  return Math.round((min + max) / 2);
}

function computeChange(points: PricePoint[]) {
  if (points.length < 2) return 0;
  const latest = pointPrice(points[0]);
  const previous = pointPrice(points[Math.min(points.length - 1, 10)]);
  if (!previous) return 0;
  return ((latest - previous) / previous) * 100;
}

function formatPrice(value: number) {
  return `${Math.round(value).toLocaleString("vi-VN")} đ/kg`;
}

function formatChange(value: number) {
  if (!Number.isFinite(value) || Math.abs(value) < 0.05) return "0,0%";
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toLocaleString("vi-VN", { maximumFractionDigits: 1 })}%`;
}

function normalizeText(value: string | null | undefined) {
  return (value || "")
    .toLocaleLowerCase("vi-VN")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function rankHomeArticles(articles: NewsArticle[]) {
  return [...articles].sort((left, right) => {
    const timeDiff = articleTime(right) - articleTime(left);
    if (timeDiff !== 0) return timeDiff;
    return homeArticleScore(right) - homeArticleScore(left);
  });
}

function homeArticleScore(article: NewsArticle) {
  const text = normalizeText(`${article.title} ${article.summary} ${article.category}`);
  const dateValue = new Date(article.published_at || article.scraped_at).getTime();
  let score = recencyScore(dateValue);
  if (hasAny(text, ["gia", "thi truong", "xuat khau"])) score += 120;
  if (hasAny(text, ["ca phe", "sau rieng", "phan bon", "chinh sach"])) score += 80;
  if (hasAny(text, ["tang", "giam", "trung quoc", "han", "mua", "han man"])) score += 45;
  if (article.category === "Ảnh hưởng giá") score += 30;
  if (article.image_url) score += 16;
  return score;
}

function recencyScore(dateValue: number) {
  if (!Number.isFinite(dateValue)) return 0;
  const ageHours = Math.max(0, (Date.now() - dateValue) / 36e5);
  if (ageHours <= 8) return 180;
  if (ageHours <= 24) return 120;
  if (ageHours <= 72) return 45;
  if (ageHours <= 168) return 12;
  return 0;
}

function hasAny(text: string, terms: string[]) {
  return terms.some((term) => text.includes(term));
}

function articleTime(article: NewsArticle) {
  const value = new Date(article.published_at || article.scraped_at).getTime();
  return Number.isFinite(value) ? value : 0;
}

function displayTitle(title: string, maxLength: number) {
  const cleaned = title.replace(/\s+/g, " ").trim();
  if (cleaned.length <= maxLength) return cleaned;
  const boundary = cleaned.lastIndexOf(" ", maxLength - 1);
  return `${cleaned.slice(0, boundary > 42 ? boundary : maxLength).trim()}...`;
}

function localWebpSource(src: string) {
  if (!src.startsWith("/") || !src.endsWith(".jpg")) return null;
  return src.replace(/\.jpg$/i, ".webp");
}

function formatDate(value: string | null) {
  if (!value) return "Đang cập nhật";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Đang cập nhật";
  return new Intl.DateTimeFormat("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" }).format(date);
}
