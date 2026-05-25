import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { BrowserRouter, useLocation, useNavigate } from "react-router-dom";
import {
  BookOpenCheck,
  Calculator,
  Coffee,
  Database,
  Filter,
  Home,
  IconContext,
  Leaf,
  Newspaper,
  Pin,
  RefreshCw,
  Sprout
} from "./components/icons";
import { AppHeader } from "./components/AppHeader";
import { FreshnessBanner } from "./components/FreshnessBanner";
import { LivePriceTicker } from "./components/LivePriceTicker";
import { TickerTape } from "./components/TickerTape";
import { SiteFooter } from "./components/SiteFooter";
import { SeoHead } from "./components/SeoHead";
import { useAuth } from "./contexts/AuthContext";
import { LanguageProvider, useLanguage, type AppLanguage } from "./contexts/LanguageContext";
import {
  fetchAvailableVarieties,
  exportCsvUrl,
  exportPdfUrl,
  exportXlsxUrl,
  fetchDataQuality,
  fetchChangeExplanation,
  fetchForecast,
  fetchHeatmap,
  fetchHistorical,
  fetchMarketComparison,
  fetchMarketIndex,
  fetchMetrics,
  fetchModelRuns,
  fetchGuides,
  fetchNews,
  fetchPlatformJobs,
  fetchRegions,
  fetchSignals,
  fetchTickerPrices,
  fetchTopMovers,
  fetchStrategyAlerts,
  fetchWatchlist,
  runPlatformJob,
  scrapeNews,
  saveWatchlistItem,
  type CropType,
  type DataQuality,
  type ChangeExplanation,
  type ForecastPoint,
  type GuidePost,
  type HeatmapCell,
  type MarketComparison,
  type MarketIndex,
  type ModelTrainingRun,
  type ModelMetrics,
  type Mover,
  type NewsArticle,
  type PlatformJobRun,
  type PricePoint,
  type Region,
  type StrategyAlert,
  type TopMovers,
  type TradingSignal,
  type Variety
} from "./lib/api";
import { cropSeoLabels, forecastPath, publicGuideSlug } from "./lib/seo";
import { splitLanguagePath, withLanguagePrefix } from "./lib/localizedRoutes";

const DataGrid = lazy(() => import("./components/DataGrid").then(({ DataGrid }) => ({ default: DataGrid })));
const AnalysisBrief = lazy(() => import("./components/AnalysisBrief").then(({ AnalysisBrief }) => ({ default: AnalysisBrief })));
const GuideLibrary = lazy(() => import("./components/GuideLibrary").then(({ GuideLibrary }) => ({ default: GuideLibrary })));
const HomePage = lazy(() => import("./components/HomePage").then(({ HomePage }) => ({ default: HomePage })));
const ForecastMethodology = lazy(() =>
  import("./components/ForecastMethodology").then(({ ForecastMethodology }) => ({ default: ForecastMethodology }))
);
const IntelligencePanels = lazy(() =>
  import("./components/IntelligencePanels").then(({ IntelligencePanels }) => ({ default: IntelligencePanels }))
);
const MarketBrain = lazy(() => import("./components/MarketBrain").then(({ MarketBrain }) => ({ default: MarketBrain })));
const MasterChart = lazy(() => import("./components/MasterChart").then(({ MasterChart }) => ({ default: MasterChart })));
const MetricsDashboard = lazy(() =>
  import("./components/MetricsDashboard").then(({ MetricsDashboard }) => ({ default: MetricsDashboard }))
);
const NewsPortal = lazy(() => import("./components/NewsPortal").then(({ NewsPortal }) => ({ default: NewsPortal })));
const NewsDetailPage = lazy(() =>
  import("./components/NewsDetailPage").then(({ NewsDetailPage }) => ({ default: NewsDetailPage }))
);
const GuideDetailPage = lazy(() =>
  import("./components/GuideDetailPage").then(({ GuideDetailPage }) => ({ default: GuideDetailPage }))
);
const AdvisoryHub = lazy(() => import("./components/AdvisoryHub").then(({ AdvisoryHub }) => ({ default: AdvisoryHub })));
const FertilizerAdvisor = lazy(() =>
  import("./components/FertilizerAdvisor").then(({ FertilizerAdvisor }) => ({ default: FertilizerAdvisor }))
);
const FertilizerMethodology = lazy(() =>
  import("./components/FertilizerMethodology").then(({ FertilizerMethodology }) => ({ default: FertilizerMethodology }))
);
const InputPricesPage = lazy(() =>
  import("./components/InputPricesPage").then(({ InputPricesPage }) => ({ default: InputPricesPage }))
);
const RoiCalculatorPage = lazy(() =>
  import("./components/RoiCalculatorPage").then(({ RoiCalculatorPage }) => ({ default: RoiCalculatorPage }))
);
const YieldFeedbackPage = lazy(() =>
  import("./components/YieldFeedbackPage").then(({ YieldFeedbackPage }) => ({ default: YieldFeedbackPage }))
);
const NotFoundPage = lazy(() => import("./components/NotFoundPage").then(({ NotFoundPage }) => ({ default: NotFoundPage })));
const ProductionPanel = lazy(() =>
  import("./components/ProductionPanel").then(({ ProductionPanel }) => ({ default: ProductionPanel }))
);
const TechnicalPanel = lazy(() => import("./components/TechnicalPanel").then(({ TechnicalPanel }) => ({ default: TechnicalPanel })));

const tabs: { value: CropType; label: string; Icon: typeof Leaf }[] = [
  { value: "sau_rieng", label: "Sầu riêng", Icon: Sprout },
  { value: "ca_phe", label: "Cà phê", Icon: Coffee },
  { value: "ho_tieu", label: "Hồ tiêu", Icon: Leaf },
  { value: "lua", label: "Lúa", Icon: Sprout }
];

const cropLabels: Record<CropType, string> = {
  sau_rieng: "sầu riêng",
  ca_phe: "cà phê",
  ho_tieu: "hồ tiêu",
  lua: "lúa"
};

const cropLabelsEn: Record<CropType, string> = {
  sau_rieng: "durian",
  ca_phe: "coffee",
  ho_tieu: "black pepper",
  lua: "rice"
};

const appCopy = {
  vi: {
    regionFallback: "Vùng trồng",
    varietyFallback: "Giống",
    marketDataDescription: "Dữ liệu giá, dự báo và cảnh báo theo vùng trồng đang chọn.",
    refreshing: "Đang làm mới...",
    refreshPrice: "Làm mới giá",
    refreshPriceAria: "Làm mới giá",
    dataWindow: "Khung dữ liệu",
    latestPrice: "Giá mới nhất",
    scraping: "Đang quét...",
    scrapePrices: "Quét giá",
    runScrapeNow: "Chạy scrape giá ngay",
    analysisTools: "Công cụ phân tích giá",
    chart: "Biểu đồ",
    analysis: "Phân tích",
    technical: "Kỹ thuật",
    data: "Dữ liệu",
    regionLabel: "Tỉnh/vùng trồng",
    loading: "Đang tải",
    varietyLabel: "Giống",
    retry: "Thử lại",
    loadingMarket: "Đang tải dữ liệu thị trường...",
    loadingUi: "Đang tải giao diện...",
    forecastTitle: (cropName: string) => `Giá ${cropName} hôm nay & dự báo 30 ngày`,
    forecastDescription: (cropName: string) =>
      `Cập nhật giá ${cropName} mới nhất theo tỉnh, vùng trồng và giống. Xem biểu đồ lịch sử, dự báo 30 ngày, cảnh báo bán và độ tin cậy dữ liệu.`,
    quoteTitleToday: (cropName: string) => `Giá ${cropName} hôm nay`,
    quoteForecast: (province?: string | null) => `Dự báo 30 ngày${province ? ` tại ${province}` : ""}`,
    timeRange: "Khoảng thời gian",
    days: "ngày",
    dataLayers: "Lớp dữ liệu",
    price: "Giá",
    forecast: "Dự báo",
    rain: "Mưa",
    alerts: "Cảnh báo",
    noRainData: "Chưa có dữ liệu lượng mưa cho khoảng thời gian này",
    pinMarket: "Ghim thị trường",
    selectedRegionFallback: "vùng đang chọn",
    selectedVarietyFallback: "giống đang chọn",
    accountProfitGate: "Vui lòng đăng nhập hoặc đăng ký tài khoản để tính lợi nhuận.",
    analyticsAuthMessage: "Vui lòng đăng nhập hoặc đăng ký tài khoản để xem mục này.",
    fertilizerAuthMessage: "Vui lòng đăng nhập hoặc đăng ký tài khoản trước khi tính khuyến nghị.",
    advisoryAuthMessage: "Vui lòng đăng nhập hoặc đăng ký tài khoản để sử dụng công cụ này.",
    errorFallback: "Một phần dữ liệu dự báo chưa tải được. Bạn có thể thử lại sau ít phút.",
    errorTitleUser: "Cần kiểm tra lại thông tin",
    errorTitleData: "Dữ liệu đang được cập nhật",
    noProductData: "Chưa có dữ liệu giá cho sản phẩm này.",
    noRegionData: "Chưa có dữ liệu giá cho tỉnh/vùng trồng này.",
    loadDataError: "Không tải được dữ liệu.",
    loadContentError: "Không tải được nội dung.",
    loadGuidesError: "Không tải được hướng dẫn kỹ thuật.",
    saveWatchlistError: "Không lưu được danh sách ghim",
    invalidEmail: "Email không hợp lệ",
    invalidPassword: "Mật khẩu cần tối thiểu 8 ký tự và có ít nhất 1 chữ số",
    missingName: "Vui lòng nhập họ tên",
    authFailed: "Không đăng nhập được",
    platformJobError: "Không chạy được job",
    newsUpdateError: "Không cập nhật được tin tức",
    updatedToday: "Cập nhật hôm nay",
    updatedDaysAgo: (days: number) => `Cập nhật ${days} ngày trước`,
    staleDaysAgo: (days: number) => `Dữ liệu ${days} ngày trước`,
    oldDataDays: (days: number) => `Dữ liệu cũ ${days} ngày`
  },
  en: {
    regionFallback: "Growing region",
    varietyFallback: "Variety",
    marketDataDescription: "Price history, forecasts and alerts for the selected growing region.",
    refreshing: "Refreshing...",
    refreshPrice: "Refresh prices",
    refreshPriceAria: "Refresh prices",
    dataWindow: "Data window",
    latestPrice: "Latest price",
    scraping: "Scraping...",
    scrapePrices: "Scrape prices",
    runScrapeNow: "Run price scrape now",
    analysisTools: "Price analysis tools",
    chart: "Chart",
    analysis: "Analysis",
    technical: "Technical",
    data: "Data",
    regionLabel: "Province/growing region",
    loading: "Loading",
    varietyLabel: "Variety",
    retry: "Try again",
    loadingMarket: "Loading market data...",
    loadingUi: "Loading interface...",
    forecastTitle: (cropName: string) => `${cropName} price today & 30-day forecast`,
    forecastDescription: (cropName: string) =>
      `Track the latest ${cropName} prices by province, growing region and variety, with history, a 30-day forecast, sell signals and data-confidence notes.`,
    quoteTitleToday: (cropName: string) => `${cropName} price today`,
    quoteForecast: (province?: string | null) => `30-day forecast${province ? ` in ${province}` : ""}`,
    timeRange: "Time range",
    days: "days",
    dataLayers: "Data layers",
    price: "Price",
    forecast: "Forecast",
    rain: "Rain",
    alerts: "Alerts",
    noRainData: "Rainfall data is not available for this range",
    pinMarket: "Pin market",
    selectedRegionFallback: "selected region",
    selectedVarietyFallback: "selected variety",
    accountProfitGate: "Please sign in or create an account to calculate farm profit.",
    analyticsAuthMessage: "Please sign in or create an account to view this section.",
    fertilizerAuthMessage: "Please sign in or create an account before calculating a fertilizer recommendation.",
    advisoryAuthMessage: "Please sign in or create an account to use this tool.",
    errorFallback: "Some forecast data could not be loaded yet. Please try again in a few minutes.",
    errorTitleUser: "Check your details",
    errorTitleData: "Data is being updated",
    noProductData: "No price data is available for this product yet.",
    noRegionData: "No price data is available for this province or growing region yet.",
    loadDataError: "Could not load the data.",
    loadContentError: "Could not load the content.",
    loadGuidesError: "Could not load the technical guides.",
    saveWatchlistError: "Could not save the pinned markets.",
    invalidEmail: "Please enter a valid email address.",
    invalidPassword: "Password must be at least 8 characters and include at least one number.",
    missingName: "Please enter your full name.",
    authFailed: "Could not sign in.",
    platformJobError: "Could not run the job.",
    newsUpdateError: "Could not update the news.",
    updatedToday: "Updated today",
    updatedDaysAgo: (days: number) => `Updated ${days} days ago`,
    staleDaysAgo: (days: number) => `Data from ${days} days ago`,
    oldDataDays: (days: number) => `Old data: ${days} days`
  }
} satisfies Record<AppLanguage, Record<string, unknown>>;

type MainSection =
  | "home"
  | "analytics"
  | "inputPrices"
  | "roi"
  | "news"
  | "guides"
  | "fertilizer"
  | "sellingTime"
  | "arbitrage"
  | "crossCrop"
  | "fertilizerMethodology"
  | "yieldFeedback"
  | "methodology";
type AnalyticsTab = "chart" | "analysis" | "technical" | "data";
type NewsView = "latest" | "sau_rieng" | "ca_phe" | "ho_tieu";
type PriceNewsView = Exclude<NewsView, "latest">;
type InitialRoute = {
  section: MainSection;
  crop: CropType;
  newsView: NewsView;
  newsSlug: string;
  guideSlug: string;
  notFound: boolean;
};
const validSections: MainSection[] = [
  "home",
  "analytics",
  "inputPrices",
  "roi",
  "news",
  "guides",
  "fertilizer",
  "sellingTime",
  "arbitrage",
  "crossCrop",
  "fertilizerMethodology",
  "yieldFeedback",
  "methodology"
];
const validCrops: CropType[] = ["sau_rieng", "ca_phe", "ho_tieu", "lua"];
const validNewsViews: NewsView[] = ["latest", "sau_rieng", "ca_phe", "ho_tieu"];
const gatedAnalyticsTabs: AnalyticsTab[] = ["analysis", "technical", "data"];
const gatedAdvisorySections: MainSection[] = ["sellingTime", "arbitrage", "crossCrop"];
const AUTH_GATE_MESSAGES = new Set([
  appCopy.vi.analyticsAuthMessage,
  appCopy.vi.fertilizerAuthMessage,
  appCopy.vi.advisoryAuthMessage,
  appCopy.vi.accountProfitGate,
  appCopy.en.analyticsAuthMessage,
  appCopy.en.fertilizerAuthMessage,
  appCopy.en.advisoryAuthMessage,
  appCopy.en.accountProfitGate
]);
const newsViewPaths: Record<PriceNewsView, string> = {
  sau_rieng: "gia-sau-rieng",
  ca_phe: "gia-ca-phe",
  ho_tieu: "gia-ho-tieu"
};
const newsPathViews: Record<string, PriceNewsView> = Object.fromEntries(
  Object.entries(newsViewPaths).map(([view, path]) => [path, view])
) as Record<string, PriceNewsView>;

const mainSections: { value: MainSection; label: string; Icon: typeof Leaf }[] = [
  { value: "home", label: "Trang chủ", Icon: Home },
  { value: "news", label: "Tin tức", Icon: Newspaper },
  { value: "guides", label: "Hướng dẫn", Icon: BookOpenCheck },
  { value: "fertilizer", label: "Khuyến nghị", Icon: Calculator }
];

function getInitialSection(search = window.location.search): MainSection {
  const section = new URLSearchParams(search).get("section");
  return validSections.includes(section as MainSection) ? (section as MainSection) : "home";
}

function getInitialCrop(search = window.location.search): CropType {
  const crop = new URLSearchParams(search).get("crop");
  return validCrops.includes(crop as CropType) ? (crop as CropType) : "sau_rieng";
}

function getInitialNewsView(search = window.location.search): NewsView {
  const newsView = new URLSearchParams(search).get("news");
  return validNewsViews.includes(newsView as NewsView) ? (newsView as NewsView) : "latest";
}

function getInitialRoute(pathnameInput = window.location.pathname, search = window.location.search): InitialRoute {
  let pathname: string;
  try {
    pathname = decodeURIComponent(pathnameInput).replace(/\/+$/, "") || "/";
  } catch {
    pathname = pathnameInput.replace(/\/+$/, "") || "/";
  }
  pathname = splitLanguagePath(pathname).pathname;
  const fallback: InitialRoute = {
    section: getInitialSection(search),
    crop: getInitialCrop(search),
    newsView: getInitialNewsView(search),
    newsSlug: "",
    guideSlug: "",
    notFound: false
  };
  const parts = pathname.split("/").filter(Boolean);
  if (pathname === "/") return fallback;
  if (parts[0] === "tin-tuc") {
    if (parts[1] === "category") return { ...fallback, section: "news", newsView: "latest" };
    if (parts[1] && newsPathViews[parts[1]]) {
      return { ...fallback, section: "news", newsView: newsPathViews[parts[1]], newsSlug: "" };
    }
    return { ...fallback, section: "news", newsView: "latest", newsSlug: parts[1] ?? "" };
  }
  if (parts[0] === "huong-dan") {
    const rawGuideSlug = parts[1] ?? "";
    const cleanGuideSlug = publicGuideSlug(rawGuideSlug);
    return { ...fallback, section: "guides", guideSlug: cleanGuideSlug };
  }
  if (parts[0] === "du-bao-gia") {
    if (parts[1] === "phan-bon") return { ...fallback, section: "inputPrices" };
    const routeCrop = validCrops.includes(parts[1] as CropType) ? (parts[1] as CropType) : "sau_rieng";
    return { ...fallback, section: "analytics", crop: routeCrop };
  }
  if (parts[0] === "roi-uoc-tinh") return { ...fallback, section: "roi" };
  if (parts[0] === "thoi-diem-ban") return { ...fallback, section: "sellingTime" };
  if (parts[0] === "chenh-lech-vung") return { ...fallback, section: "arbitrage" };
  if (parts[0] === "so-sanh-cay-trong") return { ...fallback, section: "crossCrop" };
  if (parts[0] === "khuyen-nghi-bon-phan" && parts[1] === "roi") return { ...fallback, section: "roi" };
  if (parts[0] === "khuyen-nghi-bon-phan" && parts[1] === "thoi-diem-ban") return { ...fallback, section: "sellingTime" };
  if (parts[0] === "khuyen-nghi-bon-phan" && parts[1] === "chenh-lech-vung") return { ...fallback, section: "arbitrage" };
  if (parts[0] === "khuyen-nghi-bon-phan" && parts[1] === "so-sanh-cay-trong") return { ...fallback, section: "crossCrop" };
  if (parts[0] === "khuyen-nghi-bon-phan" && parts[1] === "logic") return { ...fallback, section: "fertilizerMethodology" };
  if (parts[0] === "khuyen-nghi-bon-phan") return { ...fallback, section: "fertilizer" };
  if (parts[0] === "bao-cao-nang-suat") return { ...fallback, section: "yieldFeedback" };
  if (parts[0] === "thuat-toan-du-bao") return { ...fallback, section: "methodology" };
  return { ...fallback, notFound: true };
}

export function App() {
  return (
    <BrowserRouter>
      <LanguageProvider>
        <RoutedApp />
      </LanguageProvider>
    </BrowserRouter>
  );
}

function routeToUrl(route: InitialRoute, language: AppLanguage = "vi") {
  if (route.notFound) return `${window.location.pathname}${window.location.search}`;
  const params = new URLSearchParams();
  let path = "/";
  if (route.section === "news") {
    path = route.newsSlug
      ? `/tin-tuc/${route.newsSlug}`
      : route.newsView === "latest"
        ? "/tin-tuc"
        : `/tin-tuc/${newsViewPaths[route.newsView as PriceNewsView]}`;
  } else if (route.section === "guides") {
    path = route.guideSlug ? `/huong-dan/${route.guideSlug}` : "/huong-dan";
  } else if (route.section === "analytics") {
    path = forecastPath(route.crop);
  } else if (route.section === "inputPrices") {
    path = "/du-bao-gia/phan-bon";
  } else if (route.section === "roi") {
    path = "/roi-uoc-tinh";
  } else if (route.section === "fertilizer") {
    path = "/khuyen-nghi-bon-phan";
  } else if (route.section === "sellingTime") {
    path = "/thoi-diem-ban";
  } else if (route.section === "arbitrage") {
    path = "/chenh-lech-vung";
  } else if (route.section === "crossCrop") {
    path = "/so-sanh-cay-trong";
  } else if (route.section === "fertilizerMethodology") {
    path = "/khuyen-nghi-bon-phan/logic";
  } else if (route.section === "yieldFeedback") {
    path = "/bao-cao-nang-suat";
  } else if (route.section === "methodology") {
    path = "/thuat-toan-du-bao";
  }
  const unprefixed = params.toString() ? `${path}?${params}` : path;
  return withLanguagePrefix(unprefixed, language);
}

const TECHNICAL_ERROR_PATTERN = /api|json|unexpected token|doctype|failed to fetch|networkerror|syntaxerror|html|stack|trace|chunkload/i;
const USER_ACTION_ERROR_PATTERN = /^(email|password|please|full name|mật khẩu|mat khau|vui lòng|vui long)/i;

function safeErrorCopy(message: string | null, language: AppLanguage) {
  const clean = (message ?? "").replace(/\s+/g, " ").trim();
  const fallback = appCopy[language].errorFallback;
  if (!clean) return fallback;
  if (USER_ACTION_ERROR_PATTERN.test(clean) || clean.toLowerCase().includes("chưa có dữ liệu")) return clean;
  if (TECHNICAL_ERROR_PATTERN.test(clean)) return fallback;
  return clean.length > 150 ? fallback : clean;
}

function safeErrorTitle(message: string | null, language: AppLanguage) {
  const clean = message ?? "";
  if (USER_ACTION_ERROR_PATTERN.test(clean) || clean.toLowerCase().includes("chưa có dữ liệu")) {
    return appCopy[language].errorTitleUser;
  }
  return appCopy[language].errorTitleData;
}

function canRetryError(message: string | null) {
  const clean = message ?? "";
  return !USER_ACTION_ERROR_PATTERN.test(clean);
}

function RoutedApp() {
  const location = useLocation();
  const navigate = useNavigate();
  const { language, setLanguage } = useLanguage();
  const copy = appCopy[language];
  const [initialRoute] = useState<InitialRoute>(() => getInitialRoute(location.pathname, location.search));
  const [crop, setCrop] = useState<CropType>(initialRoute.crop);
  const [regionId, setRegionId] = useState(1);
  const [varietyId, setVarietyId] = useState(1);
  const [historical, setHistorical] = useState<PricePoint[]>([]);
  const [tickerPoints, setTickerPoints] = useState<PricePoint[]>([]);
  const [forecast, setForecast] = useState<ForecastPoint[]>([]);
  const [signals, setSignals] = useState<TradingSignal[]>([]);
  const [regions, setRegions] = useState<Region[]>([]);
  const [varieties, setVarieties] = useState<Variety[]>([]);
  const [metrics, setMetrics] = useState<ModelMetrics | null>(null);
  const [quality, setQuality] = useState<DataQuality | null>(null);
  const [topMovers, setTopMovers] = useState<TopMovers>({ gainers: [], losers: [] });
  const [heatmap, setHeatmap] = useState<HeatmapCell[]>([]);
  const [strategyAlerts, setStrategyAlerts] = useState<StrategyAlert[]>([]);
  const [marketIndex, setMarketIndex] = useState<MarketIndex | null>(null);
  const [changeExplanation, setChangeExplanation] = useState<ChangeExplanation | null>(null);
  const [marketComparison, setMarketComparison] = useState<MarketComparison | null>(null);
  const { token: authToken, user, signIn, signUp } = useAuth();
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [authName, setAuthName] = useState("");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authOpen, setAuthOpen] = useState(false);
  const advisoryGatePromptedRef = useRef<MainSection | null>(null);
  const [jobs, setJobs] = useState<PlatformJobRun[]>([]);
  const [modelRuns, setModelRuns] = useState<ModelTrainingRun[]>([]);
  const [newsArticles, setNewsArticles] = useState<NewsArticle[]>([]);
  const [guides, setGuides] = useState<GuidePost[]>([]);
  const [section, setSection] = useState<MainSection>(initialRoute.section);
  const [platformBusy, setPlatformBusy] = useState(false);
  const [contentBusy, setContentBusy] = useState(false);
  const [priceMenuOpen, setPriceMenuOpen] = useState(false);
  const [newsMenuOpen, setNewsMenuOpen] = useState(false);
  const [fertilizerMenuOpen, setFertilizerMenuOpen] = useState(false);
  const [newsView, setNewsView] = useState<NewsView>(initialRoute.newsView);
  const [newsSlug, setNewsSlug] = useState(initialRoute.newsSlug);
  const [guideSlug, setGuideSlug] = useState(initialRoute.guideSlug);
  const [notFound, setNotFound] = useState(initialRoute.notFound);
  const [analyticsTab, setAnalyticsTab] = useState<AnalyticsTab>("chart");
  const [pendingAnalyticsTab, setPendingAnalyticsTab] = useState<AnalyticsTab | null>(null);
  const [watchlist, setWatchlist] = useState<string[]>(() => {
    try {
      const saved = localStorage.getItem("agri_price.watchlist");
      return saved ? (JSON.parse(saved) as string[]) : [];
    } catch {
      return [];
    }
  });
  const [days, setDays] = useState(180);
  const [layers, setLayers] = useState({
    price: true,
    forecast: true,
    rain: true,
    signals: true
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadContent(signal?: AbortSignal) {
    const [newsPayload, guidePayload] = await Promise.all([
      fetchNews(signal, language),
      fetchGuides(undefined, section === "guides" ? 300 : 12, signal, language)
    ]);
    setNewsArticles(newsPayload);
    setGuides(guidePayload);
  }

  async function loadData(signal?: AbortSignal) {
    setLoading(true);
    setError(null);
    try {
      const [regionsPayload, tickerPayload] = await Promise.all([
        fetchRegions(crop, signal),
        fetchTickerPrices(crop, signal)
      ]);

      const nextRegionId = regionsPayload.some((item) => item.region_id === regionId)
        ? regionId
        : regionsPayload[0]?.region_id;

      if (!nextRegionId) {
        setRegions([]);
        setVarieties([]);
        setTickerPoints(tickerPayload);
        setHistorical([]);
        setForecast([]);
        setSignals([]);
        setMetrics(null);
        setError(copy.noProductData);
        return;
      }

      const availableVarietiesPayload = await fetchAvailableVarieties(crop, nextRegionId, signal);
      const nextVarietyId = availableVarietiesPayload.some((item) => item.variety_id === varietyId)
        ? varietyId
        : availableVarietiesPayload[0]?.variety_id;

      setRegions(regionsPayload);
      setVarieties(availableVarietiesPayload);
      setTickerPoints(tickerPayload);

      if (!nextVarietyId) {
        setHistorical([]);
        setForecast([]);
        setSignals([]);
        setMetrics(null);
        setError(copy.noRegionData);
        return;
      }

      if (nextRegionId !== regionId) {
        setRegionId(nextRegionId);
      }
      if (nextVarietyId !== varietyId) {
        setVarietyId(nextVarietyId);
      }

      const [
        historicalPayload,
        forecastPayload,
        signalsPayload,
        metricsPayload,
        qualityPayload,
        moversPayload,
        heatmapPayload,
        alertsPayload,
        marketIndexPayload,
        explanationPayload,
        comparisonPayload
      ] = await Promise.all([
        fetchHistorical(crop, nextRegionId, nextVarietyId, { limit: Math.max(days * 4, 60), signal }),
        fetchForecast(crop, nextRegionId, nextVarietyId, signal),
        fetchSignals(crop, nextRegionId, nextVarietyId, signal),
        fetchMetrics(crop, nextRegionId, nextVarietyId, signal),
        fetchDataQuality(crop, nextRegionId, nextVarietyId, signal),
        fetchTopMovers(crop, signal),
        fetchHeatmap(crop, signal),
        fetchStrategyAlerts(crop, nextRegionId, nextVarietyId, signal),
        fetchMarketIndex(crop, signal),
        fetchChangeExplanation(crop, nextRegionId, nextVarietyId, signal),
        fetchMarketComparison(crop, nextRegionId, nextVarietyId, signal)
      ]);

      setHistorical(historicalPayload);
      setForecast(forecastPayload);
      setSignals(signalsPayload);
      setMetrics(metricsPayload);
      setQuality(qualityPayload);
      setTopMovers(moversPayload);
      setHeatmap(heatmapPayload);
      setStrategyAlerts(alertsPayload);
      setMarketIndex(marketIndexPayload);
      setChangeExplanation(explanationPayload);
      setMarketComparison(comparisonPayload);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setError(err instanceof Error ? err.message : copy.loadDataError);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const controller = new AbortController();
    void loadContent(controller.signal).catch((err) => {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setError(err instanceof Error ? err.message : copy.loadContentError);
    });
    const newsRefreshTimer = window.setInterval(() => {
      void fetchNews(undefined, language)
        .then(setNewsArticles)
        .catch((err) => {
          console.warn("[App] background news refresh failed", err);
        });
    }, 15 * 60 * 1000);
    return () => {
      controller.abort();
      window.clearInterval(newsRefreshTimer);
    };
  }, [language]);

  useEffect(() => {
    const route = getInitialRoute(location.pathname, location.search);
    const pathLanguage = splitLanguagePath(location.pathname).language;
    const routeLanguage = pathLanguage ?? language;
    if (pathLanguage && pathLanguage !== language) {
      setLanguage(pathLanguage);
    }
    const canonicalUrl = routeToUrl(route, routeLanguage);
    const canonicalWithSearch =
      (route.section === "news" && !route.newsSlug && location.search) ||
      (route.section === "yieldFeedback" && location.search) ||
      (route.section === "fertilizer" && location.search)
        ? `${canonicalUrl}${location.search}`
        : canonicalUrl;
    const currentUrl = `${location.pathname}${location.search}`;
    if (!route.notFound && canonicalWithSearch !== currentUrl) {
      navigate(canonicalWithSearch, { replace: true });
      return;
    }
    setSection(route.section);
    setCrop(route.crop);
    setNewsView(route.newsView);
    setNewsSlug(route.newsSlug);
    setGuideSlug(route.guideSlug);
    setNotFound(route.notFound);
  }, [language, location.pathname, location.search, navigate, setLanguage]);

  useEffect(() => {
    const onInternalLinkClick = (event: MouseEvent) => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const target = event.target instanceof Element ? event.target.closest<HTMLAnchorElement>('a[href^="/"]') : null;
      if (!target || target.target || target.hasAttribute("download")) return;
      const url = new URL(target.href, window.location.origin);
      if (url.origin !== window.location.origin) return;
      event.preventDefault();
      navigate(withLanguagePrefix(`${url.pathname}${url.search}${url.hash}`, language));
    };
    document.addEventListener("click", onInternalLinkClick);
    return () => document.removeEventListener("click", onInternalLinkClick);
  }, [language, navigate]);

  useEffect(() => {
    if (section !== "analytics") return;
    const controller = new AbortController();
    void loadData(controller.signal);
    return () => controller.abort();
  }, [section, crop, regionId, varietyId, days]);

  useEffect(() => {
    if (section !== "guides" || guides.length >= 80) return;
    const controller = new AbortController();
    void fetchGuides(undefined, 300, controller.signal, language)
      .then(setGuides)
      .catch((err) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : copy.loadGuidesError);
      });
    return () => controller.abort();
  }, [language, section, guides.length]);

  useEffect(() => {
    localStorage.setItem("agri_price.watchlist", JSON.stringify(watchlist));
  }, [watchlist]);

  useEffect(() => {
    if (!authToken || !user) return;
    void loadAccountData(authToken, user);
  }, [authToken, user]);

  useEffect(() => {
    if (authToken || !gatedAnalyticsTabs.includes(analyticsTab)) return;
    setAnalyticsTab("chart");
  }, [authToken, analyticsTab]);

  useEffect(() => {
    if (!authToken || !pendingAnalyticsTab) return;
    setAnalyticsTab(pendingAnalyticsTab);
    setPendingAnalyticsTab(null);
  }, [authToken, pendingAnalyticsTab]);

  useEffect(() => {
    if (authToken) {
      advisoryGatePromptedRef.current = null;
      return;
    }
    if (!gatedAdvisorySections.includes(section)) {
      advisoryGatePromptedRef.current = null;
      return;
    }
    if (advisoryGatePromptedRef.current === section) return;
    advisoryGatePromptedRef.current = section;
    requestAccountAccess(copy.advisoryAuthMessage);
  }, [authToken, copy.advisoryAuthMessage, section]);

  const latestPrice = useMemo(() => historical.at(-1)?.max_price_vnd ?? 0, [historical]);
  const visibleHistorical = useMemo(() => {
    const validDates = historical
      .map((point) => new Date(point.timestamp))
      .filter((date) => !Number.isNaN(date.getTime()));
    const latestDate = validDates.reduce<Date | null>(
      (latest, current) => (!latest || current > latest ? current : latest),
      null
    );
    if (!latestDate) return [];

    const cutoff = new Date(latestDate);
    cutoff.setDate(cutoff.getDate() - days + 1);
    cutoff.setHours(0, 0, 0, 0);

    return historical.filter((point) => {
      const pointDate = new Date(point.timestamp);
      return !Number.isNaN(pointDate.getTime()) && pointDate >= cutoff;
    });
  }, [historical, days]);
  const quoteChangePct = useMemo(() => {
    const ordered = visibleHistorical
      .filter((point) => typeof point.max_price_vnd === "number")
      .sort((left, right) => new Date(left.timestamp).getTime() - new Date(right.timestamp).getTime());
    const first = ordered[0]?.max_price_vnd;
    const last = ordered.at(-1)?.max_price_vnd;
    if (!first || !last) return 0;
    return ((last - first) / first) * 100;
  }, [visibleHistorical]);
  const hasRainData = useMemo(
    () => visibleHistorical.some((point) => typeof point.precipitation_mm === "number" && point.precipitation_mm > 0),
    [visibleHistorical]
  );
  const freshnessDays = quality?.freshness_days ?? null;
  const freshnessLabel = useMemo(() => {
    if (freshnessDays == null) return null;
    if (freshnessDays <= 1) return copy.updatedToday;
    if (freshnessDays <= 3) return copy.updatedDaysAgo(freshnessDays);
    if (freshnessDays <= 14) return copy.staleDaysAgo(freshnessDays);
    return copy.oldDataDays(freshnessDays);
  }, [copy, freshnessDays]);
  const freshnessClass = freshnessDays == null
    ? ""
    : freshnessDays <= 3
      ? "fresh"
      : freshnessDays <= 14
        ? "stale"
        : "very-stale";
  const cropLabel = language === "en" ? cropLabelsEn[crop] : cropLabels[crop];
  const activeTab = tabs.find((tab) => tab.value === crop) ?? tabs[0];
  const ActiveIcon = activeTab.Icon;
  const selectedRegion = regions.find((item) => item.region_id === regionId);
  const selectedVariety = varieties.find((item) => item.variety_id === varietyId);
  const watchKey = `${crop}|${regionId}|${varietyId}|${selectedRegion?.province ?? selectedRegion?.region_name ?? "Vùng"} - ${selectedVariety?.name ?? "Giống"}`;

  function toggleLayer(key: keyof typeof layers) {
    if (key === "rain" && !hasRainData) return;
    setLayers((current) => ({ ...current, [key]: !current[key] }));
  }

  async function addWatchlist() {
    setWatchlist((current) => (current.includes(watchKey) ? current : [watchKey, ...current].slice(0, 8)));
    if (!authToken || !selectedRegion || !selectedVariety) return;
    try {
      await saveWatchlistItem(authToken, {
        crop_type: crop,
        region_id: regionId,
        variety_id: varietyId,
        label: `${selectedRegion.province ?? selectedRegion.region_name} - ${selectedVariety.name}`
      });
      await syncWatchlist(authToken);
    } catch (err) {
      setError(err instanceof Error ? err.message : copy.saveWatchlistError);
    }
  }

  function selectWatchlist(key: string) {
    const [nextCrop, nextRegionId, nextVarietyId] = key.split("|");
    setNotFound(false);
    setNewsSlug("");
    setGuideSlug("");
    setSection("analytics");
    setCrop(nextCrop as CropType);
    setRegionId(Number(nextRegionId));
    setVarietyId(Number(nextVarietyId));
    navigate(withLanguagePrefix(forecastPath(nextCrop as CropType), language));
  }

  function openAnalytics(nextCrop: CropType) {
    setNotFound(false);
    setNewsSlug("");
    setGuideSlug("");
    setCrop(nextCrop);
    setSection("analytics");
    setAnalyticsTab("chart");
    setPriceMenuOpen(false);
    setFertilizerMenuOpen(false);
    navigate(withLanguagePrefix(forecastPath(nextCrop), language));
  }

  function requestAccountAccess(message: string) {
    setAuthMode("register");
    setAuthOpen(true);
    setPriceMenuOpen(false);
    setNewsMenuOpen(false);
    setFertilizerMenuOpen(false);
    setError(message);
  }

  function handleAuthOpenChange(open: boolean) {
    setAuthOpen(open);
    if (!open) {
      setPendingAnalyticsTab(null);
      setError((current) =>
        current && AUTH_GATE_MESSAGES.has(current) ? null : current
      );
    }
  }

  function openAnalyticsTab(nextTab: AnalyticsTab) {
    if (!authToken && gatedAnalyticsTabs.includes(nextTab)) {
      setPendingAnalyticsTab(nextTab);
      requestAccountAccess(copy.analyticsAuthMessage);
      return;
    }
    setPendingAnalyticsTab(null);
    setError(null);
    setAnalyticsTab(nextTab);
  }

  function openNews(nextView: NewsView = "latest") {
    setNotFound(false);
    setNewsSlug("");
    setGuideSlug("");
    setNewsView(nextView);
    setSection("news");
    setNewsMenuOpen(false);
    setFertilizerMenuOpen(false);
    navigate(
      withLanguagePrefix(
        nextView === "latest"
          ? "/tin-tuc"
          : `/tin-tuc/${newsViewPaths[nextView as PriceNewsView]}`,
        language
      )
    );
  }

  function changeSection(nextSection: MainSection) {
    setNotFound(false);
    setNewsSlug("");
    setGuideSlug("");
    setSection(nextSection);
    setNewsMenuOpen(false);
    setPriceMenuOpen(false);
    setFertilizerMenuOpen(false);
    navigate(routeToUrl({ section: nextSection, crop, newsView: "latest", newsSlug: "", guideSlug: "", notFound: false }, language));
  }

  function toggleRouteLanguage() {
    const nextLanguage: AppLanguage = language === "vi" ? "en" : "vi";
    setLanguage(nextLanguage);
    const route = getInitialRoute(location.pathname, location.search);
    const target = routeToUrl(
      {
        ...route,
        crop,
        newsView,
        newsSlug,
        guideSlug,
        section,
        notFound
      },
      nextLanguage
    );
    navigate(target, { replace: false });
  }

  async function handleAuth(mode: "login" | "register") {
    setError(null);
    const email = authEmail.trim().toLowerCase();
    const password = authPassword.trim();
    const displayName = authName.trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError(copy.invalidEmail);
      return;
    }
    if (password.length < 8 || !/\d/.test(password)) {
      setError(copy.invalidPassword);
      return;
    }
    if (mode === "register" && displayName.length < 2) {
      setError(copy.missingName);
      return;
    }
    try {
      const session = mode === "login"
        ? await signIn(email, password)
        : await signUp(email, password, displayName);
      setAuthOpen(false);
      await loadAccountData(session.access_token, session.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : copy.authFailed);
    }
  }

  async function loadAccountData(token = authToken, account = user) {
    if (!token) return;
    await syncWatchlist(token);
    if (account?.is_admin) {
      await refreshPlatform(token, account);
    }
  }

  async function syncWatchlist(token = authToken) {
    const items = await fetchWatchlist(token);
    if (items.length) {
      setWatchlist(items.map((item) => `${item.crop_type}|${item.region_id}|${item.variety_id}|${item.label}`));
    }
  }

  async function refreshPlatform(token = authToken, account = user) {
    if (!token || !account?.is_admin) return;
    const [jobPayload, modelPayload] = await Promise.all([
      fetchPlatformJobs(token),
      fetchModelRuns(token)
    ]);
    setJobs(jobPayload);
    setModelRuns(modelPayload);
  }

  async function runJob(job: "scrape" | "news" | "data-quality" | "retrain") {
    if (!authToken || !user?.is_admin) return;
    setPlatformBusy(true);
    try {
      await runPlatformJob(authToken, job);
      await refreshPlatform(authToken);
      if (section === "analytics") {
        await loadData();
      } else {
        await loadContent();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : copy.platformJobError);
    } finally {
      setPlatformBusy(false);
    }
  }

  async function refreshNews() {
    setContentBusy(true);
    try {
      if (authToken) {
        if (!user?.is_admin) return;
        await scrapeNews(authToken);
      }
      setNewsArticles(await fetchNews(undefined, language));
    } catch (err) {
    setError(err instanceof Error ? err.message : copy.newsUpdateError);
    } finally {
      setContentBusy(false);
    }
  }

  function retryAfterError() {
    setError(null);
    if (section === "analytics") {
      void loadData();
      return;
    }
    if (section === "home" || section === "news" || section === "guides") {
      void loadContent();
    }
  }

  const showErrorBanner = Boolean(error && (authOpen || section === "analytics"));
  const baseAppShellClassName =
    section === "analytics"
      ? `app-shell forecast-shell crop-${crop} analytics-tab-${analyticsTab}`
      : section === "inputPrices"
        ? "app-shell forecast-shell input-prices-shell"
      : "app-shell";
  const appShellClassName = `${baseAppShellClassName}${section === "news" || section === "inputPrices" ? " live-ticker-shell" : ""}`;

  return (
    <IconContext.Provider value={{ size: 18, weight: "regular", mirrored: false }}>
    <main className={appShellClassName}>
      <AppHeader
        section={section}
        crop={crop}
        newsView={newsView}
        mainSections={mainSections}
        cropTabs={tabs}
        priceMenuOpen={priceMenuOpen}
        newsMenuOpen={newsMenuOpen}
        fertilizerMenuOpen={fertilizerMenuOpen}
        authOpen={authOpen}
        authMode={authMode}
        authName={authName}
        authEmail={authEmail}
        authPassword={authPassword}
        onSectionChange={changeSection}
        onAnalyticsOpen={openAnalytics}
        onNewsOpen={openNews}
        onPriceMenuOpenChange={setPriceMenuOpen}
        onNewsMenuOpenChange={setNewsMenuOpen}
        onFertilizerMenuOpenChange={setFertilizerMenuOpen}
        onAuthOpenChange={handleAuthOpenChange}
        onAuthModeChange={setAuthMode}
        onAuthNameChange={setAuthName}
        onAuthEmailChange={setAuthEmail}
        onAuthPasswordChange={setAuthPassword}
        onAuthSubmit={(mode) => void handleAuth(mode)}
        onLanguageToggle={toggleRouteLanguage}
      />

      {section === "analytics" ? <TickerTape points={tickerPoints} /> : null}
      {section === "inputPrices" ? <LivePriceTicker /> : null}

      {section === "analytics" ? (
        <>
          <header className="market-quote-header">
            <div className="quote-main">
              <div className="quote-title-row">
                <ActiveIcon size={20} />
                <h1>
                  <span className="quote-h1-line1">{copy.quoteTitleToday(cropLabel)}{"\u00a0"}</span>
                  <span className="quote-h1-line2">
                    {copy.quoteForecast(selectedRegion?.province)}
                  </span>
                </h1>
              </div>
              <FreshnessBanner />
              <div className="quote-meta">
                <span>{selectedRegion?.province ?? selectedRegion?.region_name ?? copy.regionFallback}</span>
                <span>{selectedVariety?.name ?? copy.varietyFallback}</span>
                <span>VND/kg</span>
              </div>
              <div className="quote-price-row">
                <strong className="num">{latestPrice.toLocaleString("vi-VN")}</strong>
                <span className={quoteChangePct >= 0 ? "quote-change positive num" : "quote-change negative num"}>
                  {quoteChangePct >= 0 ? "+" : ""}
                  {quoteChangePct.toFixed(2)}%
                </span>
                <small>VND/kg · {selectedVariety?.name ?? copy.varietyFallback}</small>
                {freshnessLabel ? (
                  <small className={`freshness-badge ${freshnessClass}`}>{freshnessLabel}</small>
                ) : null}
              </div>
              <p>{copy.marketDataDescription}</p>
            </div>

            <div className="quote-side">
              <button
                type="button"
                className="quote-refresh-button"
                onClick={() => void loadData()}
                disabled={loading}
                aria-label={copy.refreshPriceAria}
              >
                <RefreshCw size={18} />
                {loading ? copy.refreshing : copy.refreshPrice}
              </button>
              <div className="quote-range">
                <span>{copy.dataWindow}</span>
                <strong className="num">{days} {copy.days}</strong>
              </div>
              <div className="quote-range">
                <span>{copy.latestPrice}</span>
                <strong className="num">{latestPrice.toLocaleString("vi-VN")}</strong>
              </div>
              {user?.is_admin ? (
                <button
                  type="button"
                  className="quote-side-action"
                  onClick={() => void runJob("scrape")}
                  disabled={platformBusy}
                  title={copy.runScrapeNow}
                >
                  <RefreshCw size={14} />
                  {platformBusy ? copy.scraping : copy.scrapePrices}
                </button>
              ) : null}
            </div>
          </header>

          <nav className="market-subnav" aria-label={copy.analysisTools}>
            <button type="button" className={analyticsTab === "chart" ? "active" : ""} onClick={() => openAnalyticsTab("chart")}>{copy.chart}</button>
            <button type="button" className={analyticsTab === "analysis" ? "active" : ""} onClick={() => openAnalyticsTab("analysis")}>{copy.analysis}</button>
            <button type="button" className={analyticsTab === "technical" ? "active" : ""} onClick={() => openAnalyticsTab("technical")}>{copy.technical}</button>
            <button type="button" className={analyticsTab === "data" ? "active" : ""} onClick={() => openAnalyticsTab("data")}>{copy.data}</button>
          </nav>

          <section className="control-band">
            <div className="filter-group">
              <Filter size={18} />
              <label>
                {copy.regionLabel}
                <select value={regionId} onChange={(event) => setRegionId(Number(event.target.value))}>
                  {regions.length === 0 ? (
                    <option value={regionId}>{copy.loading}</option>
                  ) : (
                    regions.map((region) => (
                      <option value={region.region_id} key={region.region_id}>
                        {region.province ?? region.region_name}
                      </option>
                    ))
                  )}
                </select>
              </label>
              <label>
                {copy.varietyLabel}
                <select value={varietyId} onChange={(event) => setVarietyId(Number(event.target.value))}>
                  {varieties.map((variety) => (
                    <option value={variety.variety_id} key={variety.variety_id}>
                      {variety.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="market-status">
              <Database size={18} />
              <span>{copy.latestPrice}</span>
              <strong className="num">{latestPrice.toLocaleString("vi-VN")} VND/kg</strong>
            </div>
          </section>
        </>
      ) : null}

      {showErrorBanner ? (
        <div className="error-banner" role="status" aria-live="polite">
          <div className="error-banner-copy">
            <strong>{safeErrorTitle(error, language)}</strong>
            <span>{safeErrorCopy(error, language)}</span>
          </div>
          {canRetryError(error) ? <button type="button" onClick={retryAfterError}>{copy.retry}</button> : null}
        </div>
      ) : null}
      {loading && section === "analytics" ? <div className="loading">{copy.loadingMarket}</div> : null}

      <Suspense fallback={<div className="section-fallback">{copy.loadingUi}</div>}>
      {notFound ? <NotFoundPage /> : null}
      {!notFound && section === "home" ? (
        <HomePage
          news={newsArticles}
          guides={guides}
          onOpenAnalytics={openAnalytics}
          onOpenNews={() => openNews("latest")}
          onOpenGuides={() => changeSection("guides")}
        />
      ) : null}
      {!notFound && section === "analytics" ? (
        <>
          <SeoHead
            title={copy.forecastTitle(language === "en" ? cropLabelsEn[crop] : cropSeoLabels[crop])}
            description={copy.forecastDescription(language === "en" ? cropLabelsEn[crop] : cropSeoLabels[crop])}
            canonical={forecastPath(crop)}
            schemaJsonLd={buildPriceSchema({
              cropLabel: cropSeoLabels[crop],
              regionLabel: selectedRegion?.province ?? selectedRegion?.region_name ?? (language === "en" ? "Vietnam" : "Việt Nam"),
              varietyLabel: selectedVariety?.name ?? (language === "en" ? cropLabelsEn[crop] : cropSeoLabels[crop]),
              latestPrice,
              historical: visibleHistorical
            })}
          />
          {analyticsTab === "chart" ? (
            <>
              <section className="chart-toolbar">
                <div className="chart-control-group">
                  <span className="control-label">{copy.timeRange}</span>
                  <div className="segmented">
                  {[30, 90, 180].map((value) => (
                    <button
                      type="button"
                      className={days === value ? "active" : ""}
                      key={value}
                      onClick={() => setDays(value)}
                    >
                      {value} {copy.days}
                    </button>
                  ))}
                  </div>
                </div>
                <div className="chart-control-group chart-control-group--layers">
                  <span className="control-label">{copy.dataLayers}</span>
                  <div className="layer-toggles">
                  <button type="button" className={layers.price ? "active" : ""} onClick={() => toggleLayer("price")}>{copy.price}</button>
                  <button type="button" className={layers.forecast ? "active" : ""} onClick={() => toggleLayer("forecast")}>{copy.forecast}</button>
                  <button
                    type="button"
                    className={layers.rain && hasRainData ? "active" : ""}
                    onClick={() => toggleLayer("rain")}
                    disabled={!hasRainData}
                    title={hasRainData ? undefined : copy.noRainData}
                  >
                    {copy.rain}
                  </button>
                  <button type="button" className={layers.signals ? "active" : ""} onClick={() => toggleLayer("signals")}>{copy.alerts}</button>
                  </div>
                </div>
                <button type="button" className="pin-button" onClick={() => void addWatchlist()}>
                  <Pin size={16} />
                {copy.pinMarket}
                </button>
              </section>
              <MasterChart
                historical={visibleHistorical}
                forecast={forecast}
                signals={signals}
                showPrice={layers.price}
                showForecast={layers.forecast}
                showRain={layers.rain && hasRainData}
                showSignals={layers.signals}
              />
              <IntelligencePanels
                quality={quality}
                gainers={topMovers.gainers}
                losers={topMovers.losers}
                heatmap={heatmap}
                alerts={strategyAlerts}
                watchlist={watchlist}
                onSelectWatch={selectWatchlist}
                exportUrl={exportCsvUrl(crop, regionId, varietyId)}
                exportXlsxUrl={exportXlsxUrl(crop, regionId, varietyId)}
                exportPdfUrl={exportPdfUrl(crop, regionId, varietyId)}
              />
            </>
          ) : null}
          {analyticsTab === "analysis" ? (
            <>
              <AnalysisBrief
                cropLabel={cropLabel}
            regionLabel={selectedRegion?.province ?? selectedRegion?.region_name ?? copy.selectedRegionFallback}
            varietyLabel={selectedVariety?.name ?? copy.selectedVarietyFallback}
                historical={visibleHistorical}
                forecast={forecast}
                explanation={changeExplanation}
              />
              <MetricsDashboard metrics={metrics} />
            </>
          ) : null}
          {analyticsTab === "technical" ? <TechnicalPanel points={visibleHistorical} signals={signals} /> : null}
          {analyticsTab === "data" ? <DataGrid points={visibleHistorical} /> : null}
        </>
      ) : null}
      {!notFound && section === "news" && newsSlug ? <NewsDetailPage slug={newsSlug} /> : null}
      {!notFound && section === "news" && !newsSlug ? (
        <NewsPortal
          articles={newsArticles}
          canScrape={Boolean(authToken && user?.is_admin)}
          busy={contentBusy}
          onScrape={() => void refreshNews()}
          activeView={newsView}
          onOpenAnalytics={openAnalytics}
        />
      ) : null}
      {!notFound && section === "guides" && guideSlug ? <GuideDetailPage slug={guideSlug} /> : null}
      {!notFound && section === "guides" && !guideSlug ? <GuideLibrary guides={guides} /> : null}
      {!notFound && section === "inputPrices" ? <InputPricesPage /> : null}
      {!notFound && section === "roi" ? (
        <RoiCalculatorPage authToken={authToken} onRequireAuth={() => requestAccountAccess(copy.accountProfitGate)} />
      ) : null}
      {!notFound && section === "fertilizer" ? (
        <AdvisoryHub
          authToken={authToken}
          onRequireAuth={() => requestAccountAccess(copy.fertilizerAuthMessage)}
        />
      ) : null}
      {!notFound && section === "sellingTime" ? (
        <AdvisoryHub
          tool="sellingTime"
          authToken={authToken}
          onRequireAuth={() => requestAccountAccess(copy.advisoryAuthMessage)}
        />
      ) : null}
      {!notFound && section === "arbitrage" ? (
        <AdvisoryHub
          tool="arbitrage"
          authToken={authToken}
          onRequireAuth={() => requestAccountAccess(copy.advisoryAuthMessage)}
        />
      ) : null}
      {!notFound && section === "crossCrop" ? (
        <AdvisoryHub
          tool="crossCrop"
          authToken={authToken}
          onRequireAuth={() => requestAccountAccess(copy.advisoryAuthMessage)}
        />
      ) : null}
      {!notFound && section === "fertilizerMethodology" ? <FertilizerMethodology /> : null}
      {!notFound && section === "yieldFeedback" ? <YieldFeedbackPage /> : null}
      {!notFound && section === "methodology" ? <ForecastMethodology /> : null}
      </Suspense>
      <SiteFooter
        onOpenNews={() => openNews("latest")}
        onOpenGuides={() => changeSection("guides")}
        onOpenAnalytics={() => {
          openAnalytics(crop);
          setAnalyticsTab("chart");
        }}
        onOpenInputPrices={() => changeSection("inputPrices")}
      />
    </main>
    </IconContext.Provider>
  );
}

function buildPriceSchema({
  cropLabel,
  regionLabel,
  varietyLabel,
  latestPrice,
  historical
}: {
  cropLabel: string;
  regionLabel: string;
  varietyLabel: string;
  latestPrice: number;
  historical: PricePoint[];
}) {
  const prices = historical
    .flatMap((point) => [point.min_price_vnd, point.max_price_vnd])
    .filter((value): value is number => typeof value === "number" && value > 0);
  const lowPrice = prices.length ? Math.min(...prices) : latestPrice;
  const highPrice = prices.length ? Math.max(...prices) : latestPrice;

  return {
    "@context": "https://schema.org",
    "@type": "Product",
    name: `${varietyLabel} ${regionLabel}`,
      description: `Giá ${cropLabel} hôm nay tại ${regionLabel}, kèm lịch sử giá và dự báo 30 ngày.`,
      category: `Nông sản / ${cropLabel}`,
    offers: {
      "@type": "AggregateOffer",
      priceCurrency: "VND",
      lowPrice: Math.round(lowPrice || 0),
      highPrice: Math.round(highPrice || 0),
      offerCount: Math.max(1, historical.length),
      priceSpecification: {
        "@type": "UnitPriceSpecification",
        price: Math.round(latestPrice || highPrice || lowPrice || 0),
        priceCurrency: "VND",
        unitText: "kg",
        validFrom: new Date().toISOString()
      }
    }
  };
}
