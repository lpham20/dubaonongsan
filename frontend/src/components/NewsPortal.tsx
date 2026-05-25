import {
  Activity,
  BarChart3,
  CalendarDays,
  ExternalLink,
  Newspaper,
  RefreshCw,
  Search,
  Tags,
  TrendingDown,
  TrendingUp
} from "./icons";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useLocation } from "react-router-dom";
import { FreshnessBanner } from "./FreshnessBanner";
import { SeoHead } from "./SeoHead";
import {
  fetchAvailableVarieties,
  fetchDailyPriceBoard,
  fetchRegions,
  fetchTickerPrices,
  reportLocalPrice,
  type CropType,
  type NewsArticle,
  type PricePoint,
  type Region,
  type Variety
} from "../lib/api";
import { newsPath } from "../lib/seo";
import { useLanguage } from "../contexts/LanguageContext";
import { withLanguagePrefix } from "../lib/localizedRoutes";
import { cropLabel } from "../lib/displayLabels";

type Props = {
  articles: NewsArticle[];
  canScrape: boolean;
  busy: boolean;
  onScrape: () => void;
  activeView: NewsView;
  onViewChange: (view: NewsView) => void;
  onOpenAnalytics: (crop: CropType) => void;
};

type NewsView = "latest" | "sau_rieng" | "ca_phe" | "ho_tieu";

type NewsTopic =
  | "Tất cả"
  | "Giá nông sản"
  | "Cà phê"
  | "Sầu riêng"
  | "Hồ tiêu"
  | "Lúa"
  | "Phân bón - vật tư"
  | "Xuất khẩu"
  | "Chính sách"
  | "Tin khác";

type SortMode = "impact" | "newest" | "watch";

type RankedArticle = {
  article: NewsArticle;
  topic: NewsTopic;
  impact: string;
  relation: string;
  score: number;
  dateValue: number;
};

type TickerItem = {
  label: string;
  value: string;
  change: string;
  tone: "up" | "down";
};

type PriceNewsCrop = Exclude<NewsView, "latest">;

const PRICE_VIEW_META: Record<PriceNewsCrop, { title: string; cropName: string; forecastLabel: string }> = {
  sau_rieng: {
    title: "Giá sầu riêng",
    cropName: "sầu riêng",
    forecastLabel: "dự báo giá sầu riêng"
  },
  ca_phe: {
    title: "Giá cà phê",
    cropName: "cà phê",
    forecastLabel: "dự báo giá cà phê"
  },
  ho_tieu: {
    title: "Giá hồ tiêu",
    cropName: "hồ tiêu",
    forecastLabel: "dự báo giá hồ tiêu"
  }
};

const TOPICS: NewsTopic[] = [
  "Tất cả",
  "Giá nông sản",
  "Cà phê",
  "Sầu riêng",
  "Hồ tiêu",
  "Lúa",
  "Phân bón - vật tư",
  "Xuất khẩu",
  "Chính sách",
  "Tin khác"
];

const SORT_OPTIONS: { value: SortMode; label: string }[] = [
  { value: "impact", label: "Tác động giá" },
  { value: "newest", label: "Mới nhất" },
  { value: "watch", label: "Cần theo dõi" }
];

const NEWS_VIEW_TABS: { value: NewsView; label: string }[] = [
  { value: "latest", label: "Tin tức mới nhất" },
  { value: "sau_rieng", label: "Giá sầu riêng" },
  { value: "ca_phe", label: "Giá cà phê" },
  { value: "ho_tieu", label: "Giá hồ tiêu" }
];

const NEWS_PAGE_SIZE = 8;
const VIEW_SEO: Record<NewsView, { title: string; description: string; canonical: string }> = {
  latest: {
    title: "Tin tức thị trường nông sản, phân bón và chính sách mới nhất",
    description:
      "Bản tin nông nghiệp mới nhất về giá nông sản, phân bón, vật tư, xuất khẩu và chính sách có thể ảnh hưởng tới thị trường.",
    canonical: "/tin-tuc"
  },
  sau_rieng: {
    title: "Tin giá sầu riêng - cập nhật giá hôm nay",
    description:
      "Tin tức giá sầu riêng theo vùng trồng, giá Ri6, Monthong, Sầu Chuồng Bò và bản tin xuất khẩu sầu riêng mới nhất.",
    canonical: "/tin-tuc/gia-sau-rieng"
  },
  ca_phe: {
    title: "Tin giá cà phê - cập nhật giá hôm nay",
    description:
      "Tin tức giá cà phê Robusta và Arabica tại Tây Nguyên, Đắk Lắk, Lâm Đồng. Bản tin xuất khẩu, tồn kho và chính sách cà phê mới nhất.",
    canonical: "/tin-tuc/gia-ca-phe"
  },
  ho_tieu: {
    title: "Tin giá hồ tiêu - cập nhật giá hôm nay",
    description:
      "Tin tức giá hồ tiêu Đắk Lắk, Đắk Nông, Bà Rịa - Vũng Tàu. Cập nhật xuất khẩu, tồn kho và chính sách hồ tiêu mới nhất.",
    canonical: "/tin-tuc/gia-ho-tieu"
  }
};
const PRICE_DISCLAIMER =
  "Giá dự báo được tổng hợp từ dữ liệu thị trường và xử lý bằng mô hình AI, chỉ mang tính tham khảo — thực tế có thể dao động theo từng vùng và từng thời điểm. Bạn biết giá tại địa phương mình? Chia sẻ để giúp bà con nông dân khác cùng nắm thông tin tốt hơn! (Dubaonongsan cung cấp giá dự báo với mục đích tham khảo và không chịu trách nhiệm đối với các quyết định giao dịch phát sinh từ thông tin này.)";

const FALLBACK_NEWS_TICKER: TickerItem[] = [
  { label: "Cà phê Robusta", value: "87.800 đ/kg", change: "+1,2%", tone: "up" },
  { label: "Sầu riêng Ri6", value: "86.000 đ/kg", change: "+0,8%", tone: "up" },
  { label: "Hồ tiêu đen", value: "145.000 đ/kg", change: "+0,9%", tone: "up" },
  { label: "Lúa OM 5451", value: "7.800 đ/kg", change: "-0,2%", tone: "down" },
  { label: "Urea hạt đục", value: "12.400 đ/kg", change: "-0,4%", tone: "down" }
];

function newsViewLabel(value: NewsView, copy: { latest: string; durian: string; coffee: string; pepper: string }) {
  if (value === "sau_rieng") return copy.durian;
  if (value === "ca_phe") return copy.coffee;
  if (value === "ho_tieu") return copy.pepper;
  return copy.latest;
}

function newsSeoEn(value: NewsView, copy: { seoLatestTitle: string; seoLatestDescription: string }) {
  const seo: Record<NewsView, { title: string; description: string; canonical: string }> = {
    latest: {
      title: copy.seoLatestTitle,
      description: copy.seoLatestDescription,
      canonical: "/tin-tuc"
    },
    sau_rieng: {
      title: "Durian price news and market updates",
      description: "Latest durian price news by production area, variety, export flow and market demand.",
      canonical: "/tin-tuc/gia-sau-rieng"
    },
    ca_phe: {
      title: "Coffee price news and market updates",
      description: "Latest Robusta and Arabica coffee price news, exports, inventory and policy updates.",
      canonical: "/tin-tuc/gia-ca-phe"
    },
    ho_tieu: {
      title: "Pepper price news and market updates",
      description: "Latest black pepper price news, export updates, inventory signals and policy changes.",
      canonical: "/tin-tuc/gia-ho-tieu"
    }
  };
  return seo[value] ?? seo.latest;
}

function topicLabel(topic: NewsTopic, language: "vi" | "en") {
  if (language === "vi") return topic;
  const labels: Record<NewsTopic, string> = {
    "Tất cả": "All",
    "Cà phê": "Coffee",
    "Sầu riêng": "Durian",
    "Hồ tiêu": "Pepper",
    "Lúa": "Rice",
    "Giá nông sản": "Crop prices",
    "Phân bón - vật tư": "Fertilizer & inputs",
    "Xuất khẩu": "Exports",
    "Chính sách": "Policy",
    "Tin khác": "Other"
  };
  return labels[topic] ?? topic;
}

function sortLabel(value: SortMode, language: "vi" | "en") {
  if (language === "vi") return SORT_OPTIONS.find((item) => item.value === value)?.label ?? value;
  if (value === "newest") return "Newest";
  if (value === "impact") return "Impact";
  return "Related";
}

function relationLabel(value: string) {
  const normalized = normalize(value);
  if (normalized.includes("gia")) return "Price";
  if (normalized.includes("xuat khau")) return "Exports";
  if (normalized.includes("phan bon")) return "Inputs";
  if (normalized.includes("chinh sach")) return "Policy";
  return "Market";
}

export function NewsPortal({ articles, canScrape, busy, onScrape, activeView, onViewChange, onOpenAnalytics }: Props) {
  const { language } = useLanguage();
  const pageCopy = language === "en"
    ? {
        heroKicker: "Agricultural news",
        heroTitle: "Market news for agricultural prices, fertilizer and policy",
        refreshing: "Fetching news",
        refresh: "Fetch latest news",
        navLabel: "Choose news section",
        latest: "Latest news",
        durian: "Durian prices",
        coffee: "Coffee prices",
        pepper: "Pepper prices",
        seoLatestTitle: "Latest agricultural market, fertilizer and policy news",
        seoLatestDescription: "Fresh agricultural news on crop prices, fertilizer, inputs, exports and policy changes that can affect the market.",
        tickerLabel: "Agricultural price ticker"
      }
    : {
        heroKicker: "Tin tức nông nghiệp",
        heroTitle: "Bản tin thị trường nông sản, phân bón và chính sách ngành",
        refreshing: "Đang lấy tin",
        refresh: "Lấy tin mới",
        navLabel: "Chọn mục tin tức",
        latest: "Tin tức mới nhất",
        durian: "Giá sầu riêng",
        coffee: "Giá cà phê",
        pepper: "Giá hồ tiêu",
        seoLatestTitle: "Tin tức thị trường nông sản, phân bón và chính sách mới nhất",
        seoLatestDescription: "Bản tin nông nghiệp mới nhất về giá nông sản, phân bón, vật tư, xuất khẩu và chính sách có thể ảnh hưởng tới thị trường.",
        tickerLabel: "Dải băng giá nông sản"
      };
  const location = useLocation();
  const [activeTopic, setActiveTopic] = useState<NewsTopic>(topicFromPath);
  const [sortMode, setSortMode] = useState<SortMode>("newest");
  const [query, setQuery] = useState(() => new URLSearchParams(window.location.search).get("q") ?? "");
  const [newsPage, setNewsPage] = useState(1);
  const [tickerData, setTickerData] = useState<Record<CropType, PricePoint[]>>({
    ca_phe: [],
    sau_rieng: [],
    ho_tieu: [],
    lua: []
  });
  const [priceBoards, setPriceBoards] = useState<Record<PriceNewsCrop, PricePoint[]>>({
    ca_phe: [],
    sau_rieng: [],
    ho_tieu: []
  });
  const [priceBoardLoading, setPriceBoardLoading] = useState(false);
  const activePriceCrop = activeView === "latest" ? null : activeView;

  const rankedArticles = useMemo(() => {
    return articles.map((article) => {
      const dateValue = new Date(article.published_at ?? article.scraped_at).getTime();
      return {
        article,
        topic: detectTopic(article),
        impact: detectImpact(article),
        relation: detectRelation(article),
        score: newsScore(article),
        dateValue: Number.isFinite(dateValue) ? dateValue : 0
      };
    });
  }, [articles]);

  const filteredArticles = useMemo(() => {
    const normalizedQuery = normalize(query);
    const sorted = rankedArticles
      .filter(({ article, topic }) => {
        const matchesTopic = activeTopic === "Tất cả" || topic === activeTopic;
        const searchable = normalize(`${article.title} ${article.summary} ${article.category} ${article.source_name}`);
        return matchesTopic && (!normalizedQuery || searchable.includes(normalizedQuery));
      })
      .sort((a, b) => sortArticles(a, b, sortMode));

    return sorted;
  }, [activeTopic, query, rankedArticles, sortMode]);

  const newestFeaturedArticles = useMemo(() => {
    const normalizedQuery = normalize(query);
    return rankedArticles
      .filter(({ article, topic }) => {
        const matchesTopic = activeTopic === "Tất cả" || topic === activeTopic;
        const searchable = normalize(`${article.title} ${article.summary} ${article.category} ${article.source_name}`);
        return matchesTopic && (!normalizedQuery || searchable.includes(normalizedQuery));
      })
      .sort((a, b) => sortArticles(a, b, "newest"))
      .slice(0, 2);
  }, [activeTopic, query, rankedArticles]);

  const hero = newestFeaturedArticles[0];
  const featuredIds = useMemo(
    () => new Set(newestFeaturedArticles.map((item) => item.article.article_id)),
    [newestFeaturedArticles]
  );
  const secondaryArticles = filteredArticles.filter((item) => !featuredIds.has(item.article.article_id));
  const quickReads = secondaryArticles.slice(0, 4);
  const rest = secondaryArticles.slice(4);
  const pageCount = Math.max(1, Math.ceil(rest.length / NEWS_PAGE_SIZE));
  const activePage = Math.min(newsPage, pageCount);
  const pagedRest = rest.slice((activePage - 1) * NEWS_PAGE_SIZE, activePage * NEWS_PAGE_SIZE);
  const marketWatch = buildMarketWatch(rankedArticles, language);
  const digest = buildDigest(filteredArticles, language);
  const tickerItems = useMemo(() => buildNewsTicker(tickerData), [tickerData]);
  const seo = language === "en"
    ? newsSeoEn(activeView, pageCopy)
    : VIEW_SEO[activeView] ?? VIEW_SEO.latest;

  useEffect(() => {
    const nextQuery = new URLSearchParams(location.search).get("q") ?? "";
    setQuery((current) => (current === nextQuery ? current : nextQuery));
  }, [location.search]);

  useEffect(() => {
    setNewsPage(1);
  }, [activeTopic, query, sortMode]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const next = query.trim();
      const url = new URL(window.location.href);
      if (next) {
        url.searchParams.set("q", next);
      } else {
        url.searchParams.delete("q");
      }
      window.history.replaceState({}, "", url.toString());
    }, 500);
    return () => window.clearTimeout(timer);
  }, [query]);

  function reloadPriceBoard(cropToLoad: PriceNewsCrop, signal?: AbortSignal) {
    setPriceBoardLoading(true);
    return fetchDailyPriceBoard(cropToLoad, signal)
      .then((rows) => {
        setPriceBoards((current) => ({ ...current, [cropToLoad]: rows }));
      })
      .catch(() => {
        if (!signal?.aborted) {
          setPriceBoards((current) => ({ ...current, [cropToLoad]: [] }));
        }
      })
      .finally(() => {
        if (!signal?.aborted) setPriceBoardLoading(false);
      });
  }

  useEffect(() => {
    let active = true;

    Promise.all([
      fetchTickerPrices("ca_phe"),
      fetchTickerPrices("sau_rieng"),
      fetchTickerPrices("ho_tieu"),
      fetchTickerPrices("lua")
    ])
      .then(([coffee, durian, pepper, rice]) => {
        if (active) setTickerData({ ca_phe: coffee, sau_rieng: durian, ho_tieu: pepper, lua: rice });
      })
      .catch(() => {
        if (active) setTickerData({ ca_phe: [], sau_rieng: [], ho_tieu: [], lua: [] });
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!activePriceCrop) return;
    const controller = new AbortController();
    void reloadPriceBoard(activePriceCrop, controller.signal);

    return () => controller.abort();
  }, [activePriceCrop]);

  return (
    <section className="content-page news-page finance-news-page">
      <SeoHead
        title={seo.title}
        description={seo.description}
        canonical={seo.canonical}
      />
      <NewsPriceTicker items={tickerItems} />

      {activeView === "latest" ? (
        <div className="content-hero news-hero">
          <div>
            <span>
              <Newspaper size={18} />
              {pageCopy.heroKicker}
            </span>
            <h1>{pageCopy.heroTitle}</h1>
          </div>
          {canScrape ? (
            <button type="button" className="news-refresh-button" onClick={onScrape} disabled={busy}>
              <RefreshCw size={16} />
              {busy ? pageCopy.refreshing : pageCopy.refresh}
            </button>
          ) : null}
        </div>
      ) : null}

      <nav className="news-view-tabs" aria-label={pageCopy.navLabel}>
        {NEWS_VIEW_TABS.map((view) => (
          <button
            type="button"
            className={`news-view-tab ${activeView === view.value ? "active" : ""}`}
            aria-current={activeView === view.value ? "page" : undefined}
            key={view.value}
            onClick={() => onViewChange(view.value)}
          >
            {newsViewLabel(view.value, pageCopy)}
          </button>
        ))}
      </nav>

      {activePriceCrop ? (
        <PriceBoardSection
          crop={activePriceCrop}
          rows={priceBoards[activePriceCrop]}
          loading={priceBoardLoading}
          onOpenAnalytics={onOpenAnalytics}
          onReported={() => reloadPriceBoard(activePriceCrop)}
        />
      ) : (
      <>
      <div className="news-toolbar">
        <div className="news-topic-tabs" aria-label={language === "en" ? "Filter news by topic" : "Lọc tin theo chủ đề"}>
          {TOPICS.map((topic) => (
            <button
              type="button"
              className={topic === activeTopic ? "active" : ""}
              key={topic}
              onClick={() => setActiveTopic(topic)}
            >
              {topicLabel(topic, language)}
              <small>{topicCount(rankedArticles, topic)}</small>
            </button>
          ))}
        </div>
        <div className="news-tools">
          <label className="news-search">
            <Search size={16} />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={language === "en" ? "Search by crop, price, exports..." : "Tìm theo cây trồng, giá, xuất khẩu..."}
            />
          </label>
          <div className="news-sort" aria-label={language === "en" ? "Sort news" : "Sắp xếp tin tức"}>
            {SORT_OPTIONS.map((option) => (
              <button
                type="button"
                className={sortMode === option.value ? "active" : ""}
                key={option.value}
                onClick={() => setSortMode(option.value)}
              >
                {sortLabel(option.value, language)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {digest.length ? (
        <section className="news-digest-panel">
          <div>
            <BarChart3 size={18} />
            <h2>{language === "en" ? "Today at a glance" : "Tóm tắt nhanh hôm nay"}</h2>
          </div>
          <ul>
            {digest.slice(0, 2).map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {hero ? (
        <div className="news-market-layout">
          <div className="news-lead-stack">
            {newestFeaturedArticles.map((item) => (
              <LeadNewsCard item={item} key={item.article.article_id} />
            ))}
          </div>

          <aside className="news-side-stack">
            <section className="news-brief-panel">
              <div>
                <TrendingUp size={17} />
                <h3>{language === "en" ? "Price-moving news" : "Tin ảnh hưởng giá"}</h3>
              </div>
              {quickReads.slice(0, 4).map(({ article, topic, impact }) => (
                <Link to={withLanguagePrefix(newsPath(article), language)} key={article.article_id}>
                  <span>{topicLabel(topic, language)}</span>
                  <div className="news-alert-title">
                    <strong>{displayTitle(article.title, 76)}</strong>
                    <TrendSparkline topic={topic} impact={impact} />
                  </div>
                  <small>
                    {impact} · {formatDate(article.published_at ?? article.scraped_at)}
                  </small>
                </Link>
              ))}
            </section>

            <section className="market-watch-panel">
              <div>
                <Tags size={17} />
                <h3>{language === "en" ? "Market watch" : "Theo dõi thị trường"}</h3>
              </div>
              {marketWatch.map((item) => (
                <button
                  type="button"
                  className={activeTopic === item.topic ? "active" : ""}
                  key={item.topic}
                  onClick={() => setActiveTopic(item.topic)}
                >
                  <span>{topicLabel(item.topic, language)}</span>
                  <strong>{item.count}</strong>
                  <small>{item.note}</small>
                </button>
              ))}
            </section>
          </aside>
        </div>
      ) : (
        <div className="news-empty">{language === "en" ? "No stories match the current filters." : "Không có tin phù hợp với bộ lọc hiện tại."}</div>
      )}

      {rest.length ? (
        <>
        <div className="news-archive-heading">
          <h2>Kho tin thị trường</h2>
          <span>
            Hiển thị {(activePage - 1) * NEWS_PAGE_SIZE + 1}-{Math.min(activePage * NEWS_PAGE_SIZE, rest.length)} / {rest.length} tin
          </span>
        </div>
        <div className="news-list">
          {pagedRest.map(({ article, topic, impact, relation }) => (
            <article className="news-row-card" key={article.article_id}>
              <NewsImage article={article} />
              <div>
                <div className="news-meta-line">
                  <span>{topic}</span>
                  <ImpactBadge impact={impact} />
                </div>
                <h3>{displayTitle(article.title, 92)}</h3>
                <p>{article.summary}</p>
                <RelatedTag relation={relation} />
                <div className="news-source-row">
                  <small>{article.source_name}</small>
                  <small className="num">{formatDate(article.published_at ?? article.scraped_at)}</small>
                  <Link to={withLanguagePrefix(newsPath(article), language)}>
                    Xem chi tiết
                    <ExternalLink size={14} />
                  </Link>
                </div>
              </div>
            </article>
          ))}
        </div>
        {pageCount > 1 ? (
          <nav className="news-pagination" aria-label="Phân trang tin tức">
            {paginationItems(activePage, pageCount).map((item, index) =>
              item === "..." ? (
                <span key={`gap-${index}`}>...</span>
              ) : (
                <button
                  type="button"
                  className={item === activePage ? "active" : ""}
                  key={item}
                  onClick={() => setNewsPage(item)}
                >
                  {item}
                </button>
              )
            )}
          </nav>
        ) : null}
        </>
      ) : null}
      </>
      )}
    </section>
  );
}

function PriceBoardSection({
  crop,
  rows,
  loading,
  onOpenAnalytics,
  onReported
}: {
  crop: PriceNewsCrop;
  rows: PricePoint[];
  loading: boolean;
  onOpenAnalytics: (crop: CropType) => void;
  onReported: () => Promise<void>;
}) {
  const { language } = useLanguage();
  const meta = PRICE_VIEW_META[crop];
  const cropName = cropLabel(crop, language);
  const [reportOpen, setReportOpen] = useState(false);
  const displayRows = rows
    .filter((row) => priceValue(row) > 0)
    .sort((left, right) => {
      const provinceCompare = (left.province ?? left.region).localeCompare(right.province ?? right.region, "vi");
      if (provinceCompare !== 0) return provinceCompare;
      const varietyCompare = left.variety.localeCompare(right.variety, "vi");
      if (varietyCompare !== 0) return varietyCompare;
      return (left.quality_grade ?? "").localeCompare(right.quality_grade ?? "", "vi");
    });
  const latestDate = displayRows.length
    ? displayRows.reduce((latest, row) => (new Date(row.timestamp).getTime() > new Date(latest).getTime() ? row.timestamp : latest), displayRows[0].timestamp)
    : new Date().toISOString();
  const provinceCount = new Set(displayRows.map((row) => row.province ?? row.region)).size;
  const varietyCount = new Set(displayRows.map((row) => row.variety)).size;

  return (
    <section className="news-price-board">
      <div className="news-price-board-header">
        <div>
          <span>{language === "en" ? "Agricultural price board" : "Bảng giá nông sản"}</span>
          <h2>{language === "en" ? `${cropName} prices today, ${formatDate(latestDate)}` : `${meta.title} hôm nay ngày ${formatDate(latestDate)}`}</h2>
          <p>
            {language === "en" ? `Latest ${cropName.toLowerCase()} prices by variety and province from the system data.` : `Tổng hợp giá ${meta.cropName} theo giống và vùng/tỉnh trong dữ liệu mới nhất của hệ thống.`}
          </p>
          <FreshnessBanner />
        </div>
        <div className="price-board-kpis">
          <span>
            <strong>{displayRows.length}</strong>
            {language === "en" ? "price rows" : "dòng giá"}
          </span>
          <span>
            <strong>{provinceCount}</strong>
            {language === "en" ? "areas/provinces" : "vùng/tỉnh"}
          </span>
          <span>
            <strong>{varietyCount}</strong>
            {language === "en" ? "varieties" : "loại giống"}
          </span>
        </div>
      </div>

      <PriceReportNotice onOpen={() => setReportOpen(true)} />

      {loading ? (
        <div className="news-price-empty">{language === "en" ? "Loading the latest price board..." : "Đang tải bảng giá mới nhất..."}</div>
      ) : displayRows.length ? (
        <>
          <div className="news-price-table-wrap">
            <table className="news-price-table">
              <thead>
                <tr>
                  <th>{language === "en" ? "Province/area" : "Tỉnh/vùng"}</th>
                  <th>{language === "en" ? "Variety" : "Loại giống"}</th>
                  <th>{language === "en" ? "Grade" : "Loại"}</th>
                  <th>{language === "en" ? "Low price" : "Giá thấp"}</th>
                  <th>{language === "en" ? "High price" : "Giá cao"}</th>
                  <th>{language === "en" ? "Updated" : "Cập nhật"}</th>
                  <th>{language === "en" ? "Farmer quote" : "Báo giá nông dân"}</th>
                </tr>
              </thead>
              <tbody>
                {displayRows.map((row, index) => (
                  <tr key={`${row.timestamp}-${row.region}-${row.variety}-${row.quality_grade ?? "all"}-${index}`}>
                    <td>
                      <strong>{row.province ?? row.region}</strong>
                      {row.province && row.region !== row.province ? <small>{row.region}</small> : null}
                    </td>
                    <td><span lang={languageForCropName(row.variety)}>{row.variety}</span></td>
                    <td>{row.quality_grade ?? (language === "en" ? "Market standard" : "Chuẩn thị trường")}</td>
                    <td className="num">{formatMoney(row.min_price_vnd ?? row.max_price_vnd)}</td>
                    <td className="num">{formatMoney(row.max_price_vnd ?? row.min_price_vnd)}</td>
                    <td className="num">{formatDate(row.timestamp)}</td>
                    <td>
                      {row.farmer_report_price_vnd ? (
                        <>
                          <strong>{formatMoney(row.farmer_report_price_vnd)}</strong>
                          <small>
                            {row.farmer_report_quality_grade ?? (language === "en" ? "Reference price" : "Giá tham khảo")} · {row.farmer_reported_at ? formatDate(row.farmer_reported_at) : ""}
                          </small>
                        </>
                      ) : (
                        <small>{language === "en" ? "No quote yet" : "Chưa có báo giá"}</small>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="news-price-card-list" aria-label={language === "en" ? `${cropName} price cards` : `Bảng giá ${meta.cropName} dạng thẻ`}>
            {displayRows.map((row, index) => (
              <article className="news-price-card" key={`card-${row.timestamp}-${row.region}-${row.variety}-${row.quality_grade ?? "all"}-${index}`}>
                <div className="news-price-card-head">
                  <div>
                    <strong>{row.province ?? row.region}</strong>
                    {row.province && row.region !== row.province ? <small>{row.region}</small> : null}
                  </div>
                  <span className="num">{formatDate(row.timestamp)}</span>
                </div>
                <div className="news-price-card-meta">
                  <span lang={languageForCropName(row.variety)}>{row.variety}</span>
                  <span>{row.quality_grade ?? (language === "en" ? "Market standard" : "Chuẩn thị trường")}</span>
                </div>
                <div className="news-price-card-range">
                  <span>
                    <small>{language === "en" ? "Low price" : "Giá thấp"}</small>
                    <b className="num">{formatMoney(row.min_price_vnd ?? row.max_price_vnd)}</b>
                  </span>
                  <span>
                    <small>{language === "en" ? "High price" : "Giá cao"}</small>
                    <b className="num">{formatMoney(row.max_price_vnd ?? row.min_price_vnd)}</b>
                  </span>
                </div>
                <div className="news-price-card-footer">
                  {row.farmer_report_price_vnd ? (
                    <>
                      <span>{language === "en" ? "Farmer quote" : "Báo giá nông dân"}</span>
                      <strong className="num">{formatMoney(row.farmer_report_price_vnd)}</strong>
                      <small>
                        {row.farmer_report_quality_grade ?? (language === "en" ? "Reference price" : "Giá tham khảo")}{row.farmer_reported_at ? ` · ${formatDate(row.farmer_reported_at)}` : ""}
                      </small>
                    </>
                  ) : (
                    <small>{language === "en" ? "No farmer quote yet" : "Chưa có báo giá nông dân"}</small>
                  )}
                </div>
              </article>
            ))}
          </div>
        </>
      ) : (
        <div className="news-price-empty">
          {language === "en" ? "No clean price board is available for this section yet. The system will add it after the next data scans." : "Chưa có bảng giá đủ sạch cho mục này. Hệ thống sẽ bổ sung sau các lần quét dữ liệu tiếp theo."}
        </div>
      )}

      <button type="button" className="news-forecast-link" onClick={() => onOpenAnalytics(crop)}>
        {language === "en" ? `View ${cropName.toLowerCase()} forecast` : `Xem ${meta.forecastLabel}`}
        <ExternalLink size={15} />
      </button>
      {reportOpen ? (
        <PriceReportModal
          crop={crop}
          onClose={() => setReportOpen(false)}
          onSaved={async () => {
            await onReported();
            setReportOpen(false);
          }}
        />
      ) : null}
    </section>
  );
}

function PriceReportNotice({ onOpen }: { onOpen: () => void }) {
  const { language } = useLanguage();
  return (
    <div className="price-report-notice">
      <div className="price-report-notice-body">
        <strong>{language === "en" ? "Reference price note" : "Lưu ý giá tham khảo"}</strong>
        <p>{language === "en" ? "Prices are aggregated from market data and AI-assisted cleaning, intended as quick regional references." : "Giá được tổng hợp từ dữ liệu thị trường và mô hình AI, dùng để tham khảo nhanh theo vùng."}</p>
        <details>
          <summary>{language === "en" ? "Read full note" : "Xem lưu ý đầy đủ"}</summary>
          <p>{language === "en" ? "Actual transaction prices can differ by grade, volume, logistics, payment terms and buyer requirements. Please confirm locally before making a sale." : PRICE_DISCLAIMER}</p>
        </details>
      </div>
      <button type="button" onClick={onOpen}>
        {language === "en" ? "Report price" : "Báo giá"}
      </button>
    </div>
  );
}

function PriceReportModal({
  crop,
  onClose,
  onSaved
}: {
  crop: PriceNewsCrop;
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const { language } = useLanguage();
  const [regions, setRegions] = useState<Region[]>([]);
  const [varieties, setVarieties] = useState<Variety[]>([]);
  const [regionId, setRegionId] = useState<number>(0);
  const [varietyId, setVarietyId] = useState<number>(0);
  const [price, setPrice] = useState("");
  const [grade, setGrade] = useState(language === "en" ? "User-reported price" : "Giá người dùng báo");
  const [reporterName, setReporterName] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchRegions(crop, controller.signal)
      .then((payload) => {
        setRegions(payload);
        setRegionId(payload[0]?.region_id ?? 0);
      })
      .catch(() => setMessage(language === "en" ? "Could not load the area list." : "Không tải được danh sách vùng."));
    return () => controller.abort();
  }, [crop]);

  useEffect(() => {
    if (!regionId) {
      setVarieties([]);
      setVarietyId(0);
      return;
    }
    const controller = new AbortController();
    fetchAvailableVarieties(crop, regionId, controller.signal)
      .then((payload) => {
        setVarieties(payload);
        setVarietyId(payload[0]?.variety_id ?? 0);
      })
      .catch(() => setMessage(language === "en" ? "Could not load the variety list." : "Không tải được danh sách loại nông sản."));
    return () => controller.abort();
  }, [crop, regionId]);

  async function submitReport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedPrice = Number(price.replace(/[^\d]/g, ""));
    if (!regionId || !varietyId) {
      setMessage(language === "en" ? "Please choose an area and variety." : "Vui lòng chọn vùng và loại nông sản.");
      return;
    }
    if (!Number.isFinite(normalizedPrice) || normalizedPrice <= 0) {
      setMessage(language === "en" ? "Please enter a valid price." : "Vui lòng nhập giá hợp lệ.");
      return;
    }

    setBusy(true);
    setMessage(null);
    try {
      await reportLocalPrice({
        crop_type: crop,
        region_id: regionId,
        variety_id: varietyId,
        price_vnd: normalizedPrice,
        quality_grade: grade.trim() || (language === "en" ? "User-reported price" : "Giá người dùng báo"),
        reporter_name: reporterName.trim() || null,
        note: note.trim() || null
      });
      await onSaved();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : language === "en" ? "Could not save this price report." : "Không lưu được giá vừa báo.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="price-report-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <div className="price-report-modal" role="dialog" aria-modal="true" aria-label={language === "en" ? "Local price report" : "Báo giá địa phương"} onMouseDown={(event) => event.stopPropagation()}>
        <div className="price-report-modal-head">
          <div>
            <span>{language === "en" ? cropLabel(crop, language) : PRICE_VIEW_META[crop].title}</span>
            <h3>{language === "en" ? "Report a local price" : "Báo giá tại địa phương"}</h3>
          </div>
          <button type="button" onClick={onClose} aria-label={language === "en" ? "Close" : "Đóng"}>×</button>
        </div>
        <form onSubmit={(event) => void submitReport(event)}>
          <label>
            {language === "en" ? "Area/province" : "Vùng/tỉnh"}
            <select value={regionId} onChange={(event) => setRegionId(Number(event.target.value))}>
              {regions.map((region) => (
                <option value={region.region_id} key={region.region_id}>
                  {region.province ?? region.region_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            {language === "en" ? "Variety" : "Loại nông sản"}
            <select value={varietyId} onChange={(event) => setVarietyId(Number(event.target.value))}>
              {varieties.map((variety) => (
                <option value={variety.variety_id} key={variety.variety_id}>
                  {variety.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            {language === "en" ? "Current price (VND/kg)" : "Giá hiện tại (đ/kg)"}
            <input value={price} onChange={(event) => setPrice(event.target.value)} inputMode="numeric" placeholder={language === "en" ? "Example: 85000" : "Ví dụ: 85000"} />
          </label>
          <label>
            {language === "en" ? "Grade" : "Loại hàng"}
            <input value={grade} onChange={(event) => setGrade(event.target.value)} placeholder={language === "en" ? "Example: grade 1, bulk, premium..." : "Ví dụ: loại 1, xô, đẹp..."} />
          </label>
          <label>
            {language === "en" ? "Reporter name (optional)" : "Tên người báo giá (không bắt buộc)"}
            <input value={reporterName} onChange={(event) => setReporterName(event.target.value)} />
          </label>
          <label>
            {language === "en" ? "Notes (optional)" : "Ghi chú (không bắt buộc)"}
            <textarea value={note} onChange={(event) => setNote(event.target.value)} rows={3} placeholder={language === "en" ? "Price source, market/dealer, product condition..." : "Nguồn giá, chợ/đại lý, điều kiện hàng..."} />
          </label>
          {message ? <p className="price-report-message">{message}</p> : null}
          <div className="price-report-actions">
            <button type="button" onClick={onClose}>{language === "en" ? "Cancel" : "Hủy"}</button>
            <button type="submit" disabled={busy}>{busy ? (language === "en" ? "Saving..." : "Đang lưu...") : (language === "en" ? "Save price" : "Lưu giá")}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

function paginationItems(activePage: number, pageCount: number) {
  const pages = new Set<number>([1, pageCount, activePage - 1, activePage, activePage + 1]);
  const validPages = Array.from(pages)
    .filter((page) => page >= 1 && page <= pageCount)
    .sort((a, b) => a - b);
  const items: Array<number | "..."> = [];
  validPages.forEach((page) => {
    const previous = items[items.length - 1];
    if (typeof previous === "number" && page - previous > 1) {
      items.push("...");
    }
    items.push(page);
  });
  return items;
}

function topicFromPath(): NewsTopic {
  let pathname = window.location.pathname;
  try {
    pathname = decodeURIComponent(pathname);
  } catch {
    pathname = window.location.pathname;
  }
  const slug = pathname.split("/").filter(Boolean).at(-1) ?? "";
  const map: Record<string, NewsTopic> = {
    "ca-phe": "Cà phê",
    "sau-rieng": "Sầu riêng",
    "ho-tieu": "Hồ tiêu",
    "lua": "Lúa",
    "phan-bon-vat-tu": "Phân bón - vật tư",
    "xuat-khau": "Xuất khẩu",
    "chinh-sach": "Chính sách",
    "tin-khac": "Tin khác"
  };
  return map[slug] ?? "Tất cả";
}

function LeadNewsCard({ item }: { item: RankedArticle }) {
  const { language } = useLanguage();
  return (
    <article className="news-lead">
      <NewsImage article={item.article} />
      <div className="news-lead-copy">
        <div className="news-meta-line">
          <span>{topicLabel(item.topic, language)}</span>
          <ImpactBadge impact={item.impact} />
        </div>
        <h2>{displayTitle(item.article.title, 86)}</h2>
        <p>{displayTitle(item.article.summary, 150)}</p>
        <RelatedTag relation={item.relation} />
        <div className="news-source-row">
          <small>{item.article.source_name}</small>
          <small>
            <CalendarDays size={14} />
            {formatDate(item.article.published_at ?? item.article.scraped_at)}
          </small>
        </div>
        <Link to={withLanguagePrefix(newsPath(item.article), language)}>
          {language === "en" ? "Read story" : "Đọc bản tin"}
          <ExternalLink size={16} />
        </Link>
      </div>
    </article>
  );
}

function NewsImage({ article }: { article: NewsArticle }) {
  const imageUrl = normalizeNewsImageUrl(article.image_url);
  const logoUrl = sourceLogoUrl(article.source_url);
  const [imageFailed, setImageFailed] = useState(false);
  const [logoFailed, setLogoFailed] = useState(false);
  const hasOriginalImage = Boolean(imageUrl && !imageFailed);

  useEffect(() => {
    setImageFailed(false);
  }, [imageUrl]);

  useEffect(() => {
    setLogoFailed(false);
  }, [logoUrl]);

  return (
    <div className={`news-thumb ${hasOriginalImage ? "" : "source-logo-mode"}`}>
      {hasOriginalImage ? (
        <img
          src={imageUrl}
          alt={`Ảnh minh họa: ${article.title}`}
          loading="lazy"
          decoding="async"
          width="320"
          height="180"
          onError={() => setImageFailed(true)}
        />
      ) : (
        <div className="source-logo-card">
          <span className="source-logo-mark">
            {logoUrl && !logoFailed ? (
              <img
                src={logoUrl}
                alt={`Logo ${article.source_name}`}
                loading="lazy"
                decoding="async"
                width="64"
                height="64"
                onError={() => setLogoFailed(true)}
              />
            ) : (
              <strong>{sourceInitials(article.source_name)}</strong>
            )}
          </span>
          <small>{article.source_name}</small>
        </div>
      )}
    </div>
  );
}

function ImpactBadge({ impact }: { impact: string }) {
  const { language } = useLanguage();
  return (
    <em className={`impact-badge ${impact === "Tác động giá cao" ? "high" : ""}`}>
      <Activity size={12} />
      {language === "en" ? (impact === "Tác động giá cao" ? "High price impact" : "Market note") : impact}
    </em>
  );
}

function RelatedTag({ relation }: { relation: string }) {
  const { language } = useLanguage();
  return <small className="related-tag">{language === "en" ? "Related" : "Liên quan"}: {language === "en" ? relationLabel(relation) : relation}</small>;
}

function topicCount(items: { topic: NewsTopic }[], topic: NewsTopic) {
  if (topic === "Tất cả") return items.length;
  return items.filter((item) => item.topic === topic).length;
}

function sortArticles(a: RankedArticle, b: RankedArticle, sortMode: SortMode) {
  if (sortMode === "newest") return b.dateValue - a.dateValue;
  if (sortMode === "watch") {
    const impactDiff = impactWeight(b.impact) - impactWeight(a.impact);
    if (impactDiff !== 0) return impactDiff;
    return b.dateValue - a.dateValue;
  }
  return featuredScore(b) - featuredScore(a);
}

function featuredScore(item: RankedArticle) {
  return impactWeight(item.impact) * 300 + recencyScore(item.dateValue) + item.score;
}

function recencyScore(dateValue: number) {
  if (!dateValue) return 0;
  const ageHours = Math.max(0, (Date.now() - dateValue) / 36e5);
  if (ageHours <= 8) return 180;
  if (ageHours <= 24) return 120;
  if (ageHours <= 72) return 45;
  if (ageHours <= 168) return 12;
  return 0;
}

function buildDigest(items: RankedArticle[], language: "vi" | "en") {
  const lines: string[] = [];
  const highImpact = items.filter((item) => item.impact === "Tác động giá cao").length;
  const topTopics = TOPICS.filter((topic) => topic !== "Tất cả")
    .map((topic) => ({ topic, count: items.filter((item) => item.topic === topic).length }))
    .filter((item) => item.count > 0)
    .sort((a, b) => b.count - a.count)
    .slice(0, 3);

  if (highImpact) {
    lines.push(language === "en"
      ? `${highImpact} stories are flagged as likely to affect prices or input costs.`
      : `${highImpact} tin đang được xếp vào nhóm có thể tác động mạnh tới giá hoặc chi phí đầu vào.`);
  }
  if (topTopics.length) {
    lines.push(language === "en"
      ? `Leading topics: ${topTopics.map((item) => `${topicLabel(item.topic, language).toLowerCase()} (${item.count})`).join(", ")}.`
      : `Chủ đề nổi bật: ${topTopics.map((item) => `${item.topic.toLowerCase()} (${item.count})`).join(", ")}.`);
  }
  if (items[0]) lines.push(language === "en" ? `Start with: ${displayTitle(items[0].article.title, 95)}` : `Tin cần đọc trước: ${displayTitle(items[0].article.title, 95)}`);
  return lines.slice(0, 3);
}

function buildMarketWatch(items: RankedArticle[], language: "vi" | "en") {
  return (TOPICS.filter((topic) => topic !== "Tất cả") as Exclude<NewsTopic, "Tất cả">[])
    .map((topic) => {
      const related = items.filter((item) => item.topic === topic);
      const high = related.filter((item) => item.impact === "Tác động giá cao").length;
      return {
        topic,
        count: related.length,
        note: high
          ? language === "en" ? `${high} high-impact stories` : `${high} tin tác động cao`
          : language === "en" ? "No major movement yet" : "Chưa có biến động lớn"
      };
    })
    .filter((item) => item.count > 0)
    .sort((a, b) => b.count - a.count)
    .slice(0, 5);
}

function NewsPriceTicker({ items }: { items: TickerItem[] }) {
  const repeated = [...items, ...items, ...items];

  return (
    <div className="news-price-ticker" aria-label="Dải băng giá nông sản">
      <span>
        Giá trực tuyến
      </span>
      <div>
        <div>
          {repeated.map((item, index) => (
            <strong key={`${item.label}-${index}`}>
              {item.label}
              <b className="num">{item.value}</b>
              <em className={item.tone}>{item.change}</em>
            </strong>
          ))}
        </div>
      </div>
    </div>
  );
}

function TrendSparkline({ topic, impact }: { topic: NewsTopic; impact: string }) {
  const tone = impact === "Tác động giá cao" && topic !== "Phân bón - vật tư" ? "up" : "down";
  const points = tone === "up" ? [18, 19, 17, 21, 22, 24, 23, 26] : [28, 27, 25, 26, 23, 22, 21, 19];
  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = Math.max(max - min, 1);
  const coords = points
    .map((point, index) => {
      const x = (index / (points.length - 1)) * 72;
      const y = 26 - ((point - min) / range) * 20;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg className={`news-mini-sparkline ${tone}`} viewBox="0 0 72 30" aria-hidden="true">
      <polyline points={coords} />
      {tone === "up" ? <TrendingUp size={12} x={56} y={2} /> : <TrendingDown size={12} x={56} y={14} />}
    </svg>
  );
}

function buildNewsTicker(data: Record<CropType, PricePoint[]>): TickerItem[] {
  const coffee = pointToTicker(data.ca_phe, "Cà phê Robusta", ["robusta", "culi", "arabica"]);
  const durian = pointToTicker(data.sau_rieng, "Sầu riêng", ["ri6", "dona", "thai", "musang", "black thorn"]);
  const pepper = pointToTicker(data.ho_tieu, "Hồ tiêu", ["tieu den", "tieu trang", "tieu do"]);
  const rice = pointToTicker(data.lua, "Lúa", ["om", "dai thom", "nang hoa", "jasmine"]);
  return [
    coffee ?? FALLBACK_NEWS_TICKER[0],
    durian ?? FALLBACK_NEWS_TICKER[1],
    pepper ?? FALLBACK_NEWS_TICKER[2],
    rice ?? FALLBACK_NEWS_TICKER[3],
    FALLBACK_NEWS_TICKER[4]
  ];
}

function pointToTicker(points: PricePoint[], fallbackLabel: string, keywords: string[]) {
  const selected = selectTickerSeries(points, keywords);
  if (!selected.length) return null;
  const latest = selected[0];
  const change = computeTickerChange(selected);
  return {
    label: latest.variety || fallbackLabel,
    value: formatTickerPrice(pointPrice(latest)),
    change: formatTickerChange(change),
    tone: change >= 0 ? "up" : "down"
  } satisfies TickerItem;
}

function selectTickerSeries(points: PricePoint[], keywords: string[]) {
  const normalizedKeywords = keywords.map((keyword) => normalize(keyword));
  const matched = points.filter((point) => normalizedKeywords.some((keyword) => normalize(point.variety).includes(keyword)));
  return (matched.length ? matched : points)
    .filter((point) => pointPrice(point) > 0)
    .sort((left, right) => new Date(right.timestamp).getTime() - new Date(left.timestamp).getTime());
}

function pointPrice(point: PricePoint) {
  const min = point.min_price_vnd ?? point.max_price_vnd ?? 0;
  const max = point.max_price_vnd ?? point.min_price_vnd ?? 0;
  return Math.round((min + max) / 2);
}

function computeTickerChange(points: PricePoint[]) {
  if (points.length < 2) return 0;
  const latest = pointPrice(points[0]);
  const previous = pointPrice(points[Math.min(points.length - 1, 8)]);
  if (!previous) return 0;
  return ((latest - previous) / previous) * 100;
}

function formatTickerPrice(value: number) {
  return `${Math.round(value).toLocaleString("vi-VN")} đ/kg`;
}

function formatTickerChange(value: number) {
  if (!Number.isFinite(value) || Math.abs(value) < 0.05) return "0,0%";
  return `${value > 0 ? "+" : ""}${value.toLocaleString("vi-VN", { maximumFractionDigits: 1 })}%`;
}

function detectTopic(article: NewsArticle): NewsTopic {
  const text = normalize(`${article.title} ${article.summary} ${article.category}`);
  if (hasAny(text, ["ca phe", "robusta", "arabica"])) return "Cà phê";
  if (hasAny(text, ["sau rieng", "durian"])) return "Sầu riêng";
  if (hasAny(text, ["ho tieu", "tieu den", "tieu trang", "pepper"])) return "Hồ tiêu";
  if (hasAny(text, ["lua", "gao", "rice", "om 5451", "dai thom", "jasmine"])) return "Lúa";
  if (hasAny(text, ["phan bon", "vat tu", "thuoc bao ve thuc vat", "ure", "dap", "kali", "npk"])) {
    return "Phân bón - vật tư";
  }
  if (hasAny(text, ["xuat khau", "trung quoc", "thi truong", "don hang", "kim ngach"])) return "Xuất khẩu";
  if (hasAny(text, ["chinh sach", "bo nong nghiep", "nghi dinh", "thong tu", "quy dinh", "ma so vung trong"])) {
    return "Chính sách";
  }
  if (hasAny(text, ["gia", "thi truong", "nong san"])) return "Giá nông sản";
  return "Tin khác";
}

function detectImpact(article: NewsArticle) {
  const text = normalize(`${article.title} ${article.summary} ${article.category}`);
  if (
    hasAny(text, [
      "gia",
      "tang",
      "giam",
      "xuat khau",
      "phan bon",
      "chinh sach",
      "trung quoc",
      "thi truong",
      "han",
      "mua"
    ])
  ) {
    return "Tác động giá cao";
  }
  if (hasAny(text, ["ky thuat", "san xuat", "canh tac", "thu hoach"])) return "Theo dõi";
  return "Thông tin nền";
}

function detectRelation(article: NewsArticle) {
  const topic = detectTopic(article);
  if (topic === "Cà phê" || topic === "Sầu riêng" || topic === "Hồ tiêu" || topic === "Lúa") {
    return `dự báo giá ${topic.toLowerCase()}`;
  }
  if (topic === "Phân bón - vật tư") return "chi phí đầu vào";
  if (topic === "Xuất khẩu") return "nhu cầu thị trường";
  if (topic === "Chính sách") return "quy định sản xuất - xuất khẩu";
  if (topic === "Tin khác") return "bối cảnh ngành";
  return "giá nông sản";
}

function newsScore(article: NewsArticle) {
  const text = normalize(`${article.title} ${article.summary} ${article.category}`);
  let score = 0;
  if (hasAny(text, ["gia", "thi truong", "xuat khau"])) score += 120;
  if (hasAny(text, ["ca phe", "sau rieng", "ho tieu", "lua", "gao", "phan bon", "chinh sach"])) score += 80;
  if (hasAny(text, ["anh huong", "tang", "giam", "trung quoc"])) score += 45;
  if (article.image_url) score += 16;
  return score;
}

function impactWeight(impact: string) {
  if (impact === "Tác động giá cao") return 3;
  if (impact === "Theo dõi") return 2;
  return 1;
}

function hasAny(text: string, terms: string[]) {
  return terms.some((term) => text.includes(term));
}

function sourceLogoUrl(url: string) {
  const domain = sourceDomain(url);
  return domain ? `https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=128` : "";
}

function normalizeNewsImageUrl(value: string | null | undefined) {
  const raw = value?.trim();
  if (!raw) return "";
  if (raw.startsWith("//")) return `https:${raw}`;
  if (raw.startsWith("/")) return raw;
  try {
    const url = new URL(raw);
    return url.protocol === "http:" || url.protocol === "https:" ? url.toString() : "";
  } catch {
    return "";
  }
}

function sourceDomain(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

function sourceInitials(sourceName: string) {
  return sourceName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part.charAt(0).toLocaleUpperCase("vi-VN"))
    .join("");
}

function displayTitle(title: string, maxLength = 90) {
  const cleaned = title
    .replace(/\s+/g, " ")
    .replace(/\s+(Đây là|Trong đó|Với vai trò|Việt Nam và|Theo đó)\b.*$/i, "")
    .trim();
  if (cleaned.length <= maxLength) return cleaned;
  const boundary = cleaned.lastIndexOf(" ", maxLength - 1);
  return `${cleaned.slice(0, boundary > 42 ? boundary : maxLength).trim()}...`;
}

function normalize(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase();
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString("vi-VN");
}

function priceValue(point: PricePoint) {
  return Math.max(point.min_price_vnd ?? 0, point.max_price_vnd ?? 0);
}

function formatMoney(value: number | null | undefined) {
  if (!value) return "-";
  return `${Math.round(value).toLocaleString("vi-VN")} đ/kg`;
}

function languageForCropName(value: string) {
  return /robusta|arabica|black thorn|musang|st25/i.test(value) ? "en" : "vi";
}
