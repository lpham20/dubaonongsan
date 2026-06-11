import {
  ArrowRight,
} from "./icons";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { FreshnessBanner } from "./FreshnessBanner";
import { SeoHead } from "./SeoHead";
import {
  fetchTickerPrices,
  fetchUsdVndRate,
  type CropType,
  type GuidePost,
  type NewsArticle,
  type PricePoint,
  type UsdVndRate
} from "../lib/api";
import { guidePath, newsPath } from "../lib/seo";
import { useLanguage } from "../contexts/LanguageContext";
import { withLanguagePrefix } from "../lib/localizedRoutes";

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
  const { language } = useLanguage();
  const copy = language === "en"
    ? {
        seoTitle: "Vietnam agricultural price forecasts and technical farming guides",
        seoDescription: "Daily coffee, durian, pepper and rice prices, 30-day regional forecasts, market news and practical farming guides for Vietnam.",
        siteName: "Agri Price Forecast",
        schemaDescription: "Vietnam agricultural market forecasts, farming guides and news",
        kicker: "Agri Price Forecast",
        heroTitle: "Market intelligence and practical farming knowledge in one place",
        searchLabel: "Search crops or market news",
        searchPlaceholder: "Search: coffee, durian, fertilizer...",
        searchButton: "Search news",
        marketNews: "Market news",
        forecastDurian: "Durian forecast",
        forecastCoffee: "Coffee forecast",
        forecastPepper: "Pepper forecast",
        forecastRice: "Rice forecast",
        dataDesk: "Data desk",
        trackedGroups: "4 data groups tracked",
        agriPrices: "Crop prices",
        inputs: "Inputs",
        fertilizerAndCosts: "Fertilizer and input costs",
        impactNews: "Impact news",
        impactNewsDesc: "Exports, policy and weather",
        featured: "Featured story",
        updating: "The market brief is being updated.",
        readNews: "Read story",
        alerts: "Market alerts",
        market: "Market",
        allNews: "View all news",
        priceForecast: "Price forecasts",
        forecastModel: "30/90/180-day models",
        marketBrief: "Market brief",
        guideWorkflows: "Technical workflows",
        newGuides: (count: number) => (count ? `${count} new guides` : "Production guide library"),
        commodityProfiles: "Commodity profiles",
        commodityList: "Coffee, durian, pepper, rice",
        livePrices: "Today prices"
      }
    : {
        seoTitle: "Dự báo giá nông sản & hướng dẫn kỹ thuật Việt Nam",
        seoDescription: "Cập nhật giá cà phê, sầu riêng, hồ tiêu, lúa hằng ngày. Dự báo 30 ngày theo vùng trồng, bản tin thị trường và hướng dẫn kỹ thuật nông nghiệp.",
        siteName: "Dự báo nông sản",
        schemaDescription: "Nền tảng tin tức, kỹ thuật và dự báo giá nông sản Việt Nam",
        kicker: "Dự báo nông sản",
        heroTitle: "Nền tảng tri thức và dự báo thị trường nông nghiệp toàn diện",
        searchLabel: "Tìm nhanh cây trồng hoặc tin thị trường",
        searchPlaceholder: "Tìm nhanh: cà phê, sầu riêng, phân bón...",
        searchButton: "Tìm tin",
        marketNews: "Tin thị trường",
        forecastDurian: "Dự báo sầu riêng",
        forecastCoffee: "Dự báo cà phê",
        forecastPepper: "Dự báo hồ tiêu",
        forecastRice: "Dự báo lúa",
        dataDesk: "Bàn dữ liệu",
        trackedGroups: "4 nhóm dữ liệu đang theo dõi",
        agriPrices: "Giá nông sản",
        inputs: "Vật tư",
        fertilizerAndCosts: "Phân bón, chi phí đầu vào",
        impactNews: "Tin tác động",
        impactNewsDesc: "Xuất khẩu, chính sách, thời tiết",
        featured: "Tin tiêu điểm",
        updating: "Bản tin đang được cập nhật.",
        readNews: "Đọc bản tin",
        alerts: "Cảnh báo thị trường",
        market: "Thị trường",
        allNews: "Xem toàn bộ bản tin",
        priceForecast: "Dự báo giá",
        forecastModel: "Mô hình 30/90/180 ngày",
        marketBrief: "Bản tin thị trường",
        guideWorkflows: "Quy trình kỹ thuật",
        newGuides: (count: number) => (count ? `${count} hướng dẫn mới` : "Cẩm nang canh tác"),
        commodityProfiles: "Hồ sơ hàng hóa",
        commodityList: "Cà phê, sầu riêng, hồ tiêu, lúa",
        livePrices: "Giá hôm nay"
      };
  const [liveTicker, setLiveTicker] = useState<HomeTickerState>({ coffee: [], durian: [], pepper: [], rice: [] });
  const [usdVndRate, setUsdVndRate] = useState<UsdVndRate | null>(null);
  const articles = useMemo(() => rankHomeArticles(news.length ? news : fallbackNews), [news]);
  const lead = articles[0];
  const leadImageUrl = lead.image_url || "/coffee-hero-photo.jpg";
  const leadWebpUrl = localWebpSource(leadImageUrl);
  const marketAlerts = articles.slice(1, 5);
  const guidePreview = guides.slice(0, 3);
  const tickerItems = useMemo(() => buildTickerItems(liveTicker, usdVndRate, language), [language, liveTicker, usdVndRate]);
  const dataCards = useMemo(() => buildMarketCards(liveTicker, language), [language, liveTicker]);
  const boardCards = dataCards.slice(0, 4);
  const movers = useMemo(() => splitMovers(dataCards), [dataCards]);
  const newsColumns = useMemo(() => buildNewsColumns(articles.slice(1, 7)), [articles]);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();

    Promise.all([
      fetchTickerPrices("ca_phe", controller.signal),
      fetchTickerPrices("sau_rieng", controller.signal),
      fetchTickerPrices("ho_tieu", controller.signal),
      fetchTickerPrices("lua", controller.signal)
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

    fetchUsdVndRate(controller.signal)
      .then((rate) => {
        if (active) setUsdVndRate(rate);
      })
      .catch(() => {
        if (active) setUsdVndRate(null);
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, []);

  return (
    <section className="home-page paper">
      <SeoHead
        title={copy.seoTitle}
        description={copy.seoDescription}
        canonical="/"
        schemaJsonLd={{
          "@context": "https://schema.org",
          "@type": "WebPage",
          name: copy.siteName,
          url: "https://dubaonongsan.com/",
          description: copy.schemaDescription,
          speakable: {
            "@type": "SpeakableSpecification",
            cssSelector: [".p-lead .p-headline", ".p-lead .p-dek"]
          }
        }}
      />

      <PriceTicker items={tickerItems} />

      <div className="p-wrap">
        <section className="p-lead">
          <article className="main">
            <div className="p-kicker">
              <span className="bar" />
              {copy.featured}{lead.category ? ` · ${lead.category}` : ""}
            </div>
            <h1 className="p-headline">{displayTitle(lead.title || copy.heroTitle, 110)}</h1>
            <p className="p-dek">{displayTitle(lead.summary || lead.excerpt || copy.updating, 210)}</p>
            <Link to={withLanguagePrefix(lead.source_url === "#" ? "/tin-tuc" : newsPath(lead), language)}>
              <picture>
                {leadWebpUrl ? <source srcSet={leadWebpUrl} type="image/webp" /> : null}
                <img
                  className="p-figure"
                  src={leadImageUrl}
                  alt={`Ảnh minh họa: ${lead.title}`}
                  fetchPriority="high"
                  decoding="async"
                  width="960"
                  height="480"
                  onError={(event) => {
                    if (event.currentTarget.dataset.fallbackApplied === "true") {
                      event.currentTarget.style.display = "none";
                      return;
                    }
                    event.currentTarget.dataset.fallbackApplied = "true";
                    event.currentTarget.src = "/coffee-hero-photo.jpg";
                  }}
                />
              </picture>
            </Link>
            <div className="p-byline">
              <b>{language === "en" ? "Market bulletin" : "Bản tin thị trường"}</b>
              <span className="dot" />
              <span>{lead.source_name}</span>
              <span className="dot" />
              <span>{formatDate(lead.published_at || lead.scraped_at, language)}</span>
            </div>
          </article>

          <aside className="rail">
            <div className="rail-h">{language === "en" ? "Worth watching" : "Đáng chú ý"}</div>
            {marketAlerts.map((item) => (
              <Link className="rail-item" to={withLanguagePrefix(item.source_url === "#" ? "/tin-tuc" : newsPath(item), language)} key={item.article_id}>
                <div className="rk">{item.category || copy.market}</div>
                <h4>{displayTitle(item.title, 84)}</h4>
                <span className="tm">{formatDate(item.published_at || item.scraped_at, language)}</span>
              </Link>
            ))}
          </aside>
        </section>

        <section className="p-section">
          <div className="p-sec-head">
            <h2>{language === "en" ? "Market price board" : "Bảng giá thị trường"}</h2>
            <button type="button" className="more p-action-link" onClick={() => onOpenAnalytics("sau_rieng")}>
              {language === "en" ? "Open analysis" : "Mở phân tích"} <ArrowRight size={13} />
            </button>
          </div>
          <div className="home-freshness-line">
            <FreshnessBanner />
          </div>
          <div className="board">
            {boardCards.map((card) => (
              <article className="cell" key={`${card.label}-${card.sublabel}`}>
                <div className="cm">
                  {card.label} <small>{card.sublabel}</small>
                </div>
                <div className="cp">{stripUnit(card.value)}</div>
                <div className={`cc ${card.tone === "up" ? "pos" : "neg"}`}>
                  {card.tone === "up" ? "▲" : "▼"} {card.change}
                </div>
                <Sparkline points={card.points} tone={card.tone} />
              </article>
            ))}
          </div>
        </section>

        <section className="p-section">
          <div className="p-sec-head">
            <h2>{language === "en" ? "Strongest market moves" : "Biến động mạnh nhất"}</h2>
            <button type="button" className="more p-action-link" onClick={() => onOpenAnalytics("ca_phe")}>
              {copy.priceForecast} <ArrowRight size={13} />
            </button>
          </div>
          <div className="movers">
            <div className="col">
              <h3 className="pos">{language === "en" ? "▲ Biggest gainers" : "▲ Vùng tăng giá mạnh nhất"}</h3>
              {movers.gainers.map((card) => (
                <MoverRow card={card} key={`gain-${card.label}-${card.sublabel}`} />
              ))}
            </div>
            <div className="col">
              <h3 className="neg">{language === "en" ? "▼ Biggest decliners" : "▼ Vùng giảm giá mạnh nhất"}</h3>
              {movers.decliners.map((card) => (
                <MoverRow card={card} key={`drop-${card.label}-${card.sublabel}`} />
              ))}
            </div>
          </div>
        </section>

        <section className="p-section">
          <div className="p-sec-head">
            <h2>{language === "en" ? "Latest agricultural news" : "Tin nông nghiệp mới nhất"}</h2>
            <button type="button" className="more p-action-link" onClick={onOpenNews}>
              {copy.allNews} <ArrowRight size={13} />
            </button>
          </div>
          <div className="river">
            {newsColumns.map((column, columnIndex) => (
              <div className="art" key={`news-col-${columnIndex}`}>
                {column.map((item, itemIndex) => (
                  <div key={item.article_id}>
                    <Link to={withLanguagePrefix(item.source_url === "#" ? "/tin-tuc" : newsPath(item), language)}>
                      <div className="rk">{item.category || copy.market}</div>
                      <h3>{displayTitle(item.title, itemIndex === 0 ? 82 : 70)}</h3>
                    </Link>
                    {itemIndex === 0 ? <p>{displayTitle(item.summary || item.excerpt || copy.updating, 128)}</p> : null}
                    <span className="tm">{formatDate(item.published_at || item.scraped_at, language)}</span>
                    {itemIndex < column.length - 1 ? <div className="divider" /> : null}
                  </div>
                ))}
              </div>
            ))}
          </div>
        </section>

        <section className="p-section p-section-last">
          <div className="p-sec-head">
            <h2>{language === "en" ? "Field guides" : "Hướng dẫn sử dụng"}</h2>
            <button type="button" className="more p-action-link" onClick={onOpenGuides}>
              {language === "en" ? "Guide library" : "Thư viện hướng dẫn"} <ArrowRight size={13} />
            </button>
          </div>
          <div className="guides">
            {guidePreview.length
              ? guidePreview.map((guide, index) => (
                  <Link className="guide" to={withLanguagePrefix(guidePath(guide.slug), language)} key={guide.slug}>
                    <div className="step">{String(index + 1).padStart(2, "0")}</div>
                    <h4>{displayTitle(guide.title, 74)}</h4>
                    <p>{displayTitle(guide.summary, 132)}</p>
                    <span className="read">{language === "en" ? "Read guide" : "Xem hướng dẫn"} →</span>
                  </Link>
                ))
              : fallbackHomeGuides(language).map((guide, index) => (
                  <Link className="guide" to={withLanguagePrefix("/huong-dan", language)} key={guide.title}>
                    <div className="step">{String(index + 1).padStart(2, "0")}</div>
                    <h4>{guide.title}</h4>
                    <p>{guide.summary}</p>
                    <span className="read">{language === "en" ? "Open library" : "Mở thư viện"} →</span>
                  </Link>
                ))}
          </div>
        </section>
      </div>
    </section>
  );
}

function PriceTicker({ items }: { items: TickerItem[] }) {
  const { language } = useLanguage();
  const visible = items.slice(0, 6);

  return (
    <div className="p-strip" aria-label={language === "en" ? "Live agricultural price strip" : "Bảng giá nông sản hôm nay"}>
      <div className="lab">{language === "en" ? "Today prices" : "Giá hôm nay"}</div>
      <div className="items">
        {visible.map((item) => (
          <div className="it" key={`${item.label}-${item.value}`}>
            <span className="s">{item.label}</span>
            <span className="pr">
              <b>{item.value}</b>
              <em className={item.tone === "up" ? "pos" : "neg"}>{item.change}</em>
            </span>
          </div>
        ))}
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
    <svg className={`spark ${tone}`} viewBox="0 0 120 42" preserveAspectRatio="none" role="img" aria-label="Biểu đồ biến động nhỏ">
      <polygon points={area} />
      <polyline points={coords} />
    </svg>
  );
}

function MoverRow({ card }: { card: MarketCard }) {
  return (
    <div className="mv">
      <div className="nm">
        {card.label}
        <small>{card.sublabel}</small>
      </div>
      <div className="px">{stripUnit(card.value)}</div>
      <div className={`ch ${card.tone === "up" ? "pos" : "neg"}`}>{card.change}</div>
    </div>
  );
}

function buildTickerItems(live: HomeTickerState, usdVndRate: UsdVndRate | null, language: "vi" | "en" = "vi"): TickerItem[] {
  const usdTicker = usdRateToTicker(usdVndRate, language) ?? fallbackTicker[6];
  if (!live.coffee.length && !live.durian.length && !live.pepper.length && !live.rice.length) {
    return [...fallbackTicker.slice(0, 6), usdTicker];
  }

  return [
    pointToTicker(live.coffee, "Cà phê Robusta", ["Robusta", "Culi", "Arabica"], language) ?? fallbackTicker[0],
    pointToTicker(live.durian, "Sầu riêng", ["Ri6", "Dona", "Thái", "Musang", "Black Thorn"], language) ?? fallbackTicker[1],
    pointToTicker(live.pepper, "Hồ tiêu", ["Tiêu đen", "Tiêu trắng", "Tiêu đỏ"], language) ?? fallbackTicker[2],
    pointToTicker(live.rice, "Lúa", ["OM", "Đài thơm", "Nàng Hoa", "Jasmine"], language) ?? fallbackTicker[3],
    fallbackTicker[5],
    usdTicker
  ];
}

function usdRateToTicker(rate: UsdVndRate | null, language: "vi" | "en" = "vi"): TickerItem | null {
  if (!rate?.transfer) return null;
  return {
    label: "USD/VND VCB",
    value: Math.round(rate.transfer).toLocaleString(localeFor(language)),
    change: rate.as_of ? `VCB ${formatShortDate(rate.as_of, language)}` : "VCB",
    tone: "up"
  };
}

function buildMarketCards(live: HomeTickerState, language: "vi" | "en" = "vi"): MarketCard[] {
  if (!live.coffee.length && !live.durian.length && !live.pepper.length && !live.rice.length) return fallbackMarketCards;

  return [
    pointToCard(live.coffee, fallbackMarketCards[0], ["Robusta", "Culi"], language),
    pointToCard(live.durian, fallbackMarketCards[1], ["Ri6", "Sầu"], language),
    pointToCard(live.durian, fallbackMarketCards[2], ["Dona", "Thái", "Musang", "Black Thorn"], language),
    pointToCard(live.pepper, fallbackMarketCards[3], ["Tiêu đen", "Tiêu trắng", "Tiêu đỏ"], language),
    pointToCard(live.rice, fallbackMarketCards[4], ["OM", "Đài thơm", "Nàng Hoa", "Jasmine"], language),
    pointToCard(live.rice, fallbackMarketCards[5], ["ST25"], language),
    pointToCard(live.pepper, fallbackMarketCards[6], ["Tiêu đen"], language),
    pointToCard(live.pepper, fallbackMarketCards[7], ["Tiêu trắng"], language)
  ];
}

function splitMovers(cards: MarketCard[]) {
  const ranked = [...cards].sort((left, right) => Math.abs(parseChangeNumber(right.change)) - Math.abs(parseChangeNumber(left.change)));
  const gainers = ranked.filter((card) => card.tone === "up").slice(0, 5);
  const decliners = ranked.filter((card) => card.tone === "down").slice(0, 5);

  return {
    gainers: gainers.length ? gainers : ranked.slice(0, 5),
    decliners: decliners.length ? decliners : ranked.slice(0, 5)
  };
}

function parseChangeNumber(value: string) {
  const normalized = value.replace("%", "").replace(",", ".").replace(/[^\d.+-]/g, "");
  const parsed = Number.parseFloat(normalized);
  return Number.isFinite(parsed) ? parsed : 0;
}

function buildNewsColumns(items: NewsArticle[]) {
  const source = items.length ? items : fallbackNews;
  return [source.slice(0, 2), source.slice(2, 4), source.slice(4, 6)].map((column) => (column.length ? column : source.slice(0, 1)));
}

function fallbackHomeGuides(language: "vi" | "en") {
  return language === "en"
    ? [
        {
          title: "Read price charts and forecast bands",
          summary: "Understand actual prices, ML forecasts and confidence bands before deciding when to sell."
        },
        {
          title: "Compare prices by growing region",
          summary: "Filter by crop, variety and province to spot regional price gaps and timing differences."
        },
        {
          title: "Estimate profit from input costs",
          summary: "Combine expected yield, selling price and fertilizer cost to frame a practical farm budget."
        }
      ]
    : [
        {
          title: "Đọc biểu đồ giá và dải dự báo",
          summary: "Phân biệt giá thực tế, dự báo ML và dải tin cậy trước khi quyết định thời điểm bán."
        },
        {
          title: "So sánh giá theo vùng trồng",
          summary: "Lọc theo cây, giống và tỉnh để nhìn nhanh chênh lệch vùng và nhịp thu hoạch."
        },
        {
          title: "Ước tính lợi nhuận nông vụ",
          summary: "Kết hợp năng suất, giá bán kỳ vọng và chi phí đầu vào để lập ngân sách thực tế."
        }
      ];
}

function stripUnit(value: string) {
  return value.replace(/\s+(đ\/kg|VND\/kg)$/i, "");
}

function pointToTicker(points: PricePoint[], fallbackLabel: string, keywords: string[], language: "vi" | "en"): TickerItem | null {
  const selected = selectSeries(points, keywords);
  if (!selected.length) return null;
  const latest = selected[0];
  const change = computeChange(selected);
  const location = latest.province || latest.region;

  return {
    label: `${latest.variety || fallbackLabel}${location ? ` ${location}` : ""}`,
    value: formatPrice(pointPrice(latest), language),
    change: formatChange(change, language),
    tone: change >= 0 ? "up" : "down"
  };
}

function pointToCard(points: PricePoint[], fallback: MarketCard, keywords: string[], language: "vi" | "en"): MarketCard {
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
    value: formatPrice(pointPrice(latest), language),
    change: formatChange(change, language),
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

function formatPrice(value: number, language: "vi" | "en" = "vi") {
  return `${Math.round(value).toLocaleString(localeFor(language))} ${language === "en" ? "VND/kg" : "đ/kg"}`;
}

function localeFor(language: "vi" | "en") {
  return language === "en" ? "en-US" : "vi-VN";
}

function formatShortDate(value: string, language: "vi" | "en" = "vi") {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const parts = new Intl.DateTimeFormat(localeFor(language), {
    day: "2-digit",
    month: "2-digit",
    timeZone: "Asia/Ho_Chi_Minh"
  }).formatToParts(date);
  const day = parts.find((part) => part.type === "day")?.value ?? "";
  const month = parts.find((part) => part.type === "month")?.value ?? "";
  return day && month ? (language === "en" ? `${month}/${day}` : `${day}/${month}`) : "";
}

function formatChange(value: number, language: "vi" | "en" = "vi") {
  if (!Number.isFinite(value) || Math.abs(value) < 0.05) return `${(0).toLocaleString(localeFor(language), { maximumFractionDigits: 1 })}%`;
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toLocaleString(localeFor(language), { maximumFractionDigits: 1 })}%`;
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

function normalizeDisplayText(value: string | null | undefined) {
  return (value || "").normalize("NFC");
}

function displayTitle(title: string, maxLength: number) {
  const cleaned = normalizeDisplayText(title).replace(/\s+/g, " ").trim();
  if (cleaned.length <= maxLength) return cleaned;
  const boundary = cleaned.lastIndexOf(" ", maxLength - 1);
  return `${cleaned.slice(0, boundary > 42 ? boundary : maxLength).trim()}...`;
}

function localWebpSource(src: string) {
  if (!src.startsWith("/") || !src.endsWith(".jpg")) return null;
  return src.replace(/\.jpg$/i, ".webp");
}

function formatDate(value: string | null, language: "vi" | "en" = "vi") {
  if (!value) return "Đang cập nhật";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Đang cập nhật";
  return new Intl.DateTimeFormat(localeFor(language), { day: "2-digit", month: "2-digit", year: "numeric" }).format(date);
}
