import { lazy, Suspense, useEffect, useMemo, useState } from "react";
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
import { TickerTape } from "./components/TickerTape";
import { SiteFooter } from "./components/SiteFooter";
import { SeoHead } from "./components/SeoHead";
import { useAuth } from "./contexts/AuthContext";
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
const FertilizerAdvisor = lazy(() =>
  import("./components/FertilizerAdvisor").then(({ FertilizerAdvisor }) => ({ default: FertilizerAdvisor }))
);
const FertilizerMethodology = lazy(() =>
  import("./components/FertilizerMethodology").then(({ FertilizerMethodology }) => ({ default: FertilizerMethodology }))
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

type MainSection = "home" | "analytics" | "news" | "guides" | "fertilizer" | "fertilizerMethodology" | "methodology";
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
const validSections: MainSection[] = ["home", "analytics", "news", "guides", "fertilizer", "fertilizerMethodology", "methodology"];
const validCrops: CropType[] = ["sau_rieng", "ca_phe", "ho_tieu", "lua"];
const validNewsViews: NewsView[] = ["latest", "sau_rieng", "ca_phe", "ho_tieu"];
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
  { value: "fertilizer", label: "Khuyến nghị bón phân", Icon: Calculator }
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
  const pathname = decodeURIComponent(pathnameInput).replace(/\/+$/, "") || "/";
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
    const routeCrop = validCrops.includes(parts[1] as CropType) ? (parts[1] as CropType) : "sau_rieng";
    return { ...fallback, section: "analytics", crop: routeCrop };
  }
  if (parts[0] === "khuyen-nghi-bon-phan" && parts[1] === "logic") return { ...fallback, section: "fertilizerMethodology" };
  if (parts[0] === "khuyen-nghi-bon-phan") return { ...fallback, section: "fertilizer" };
  if (parts[0] === "thuat-toan-du-bao") return { ...fallback, section: "methodology" };
  return { ...fallback, notFound: true };
}

export function App() {
  return (
    <BrowserRouter>
      <RoutedApp />
    </BrowserRouter>
  );
}

function routeToUrl(route: InitialRoute) {
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
  } else if (route.section === "fertilizer") {
    path = "/khuyen-nghi-bon-phan";
  } else if (route.section === "fertilizerMethodology") {
    path = "/khuyen-nghi-bon-phan/logic";
  } else if (route.section === "methodology") {
    path = "/thuat-toan-du-bao";
  }
  return params.toString() ? `${path}?${params}` : path;
}

const TECHNICAL_ERROR_PATTERN = /api|json|unexpected token|doctype|failed to fetch|networkerror|syntaxerror|html|stack|trace|chunkload/i;
const USER_ACTION_ERROR_PATTERN = /^(email|mật khẩu|mat khau|vui lòng|vui long)/i;

function safeErrorCopy(message: string | null) {
  const clean = (message ?? "").replace(/\s+/g, " ").trim();
  const fallback = "Một phần dữ liệu dự báo chưa tải được. Bạn có thể thử lại sau ít phút.";
  if (!clean) return fallback;
  if (USER_ACTION_ERROR_PATTERN.test(clean) || clean.toLowerCase().includes("chưa có dữ liệu")) return clean;
  if (TECHNICAL_ERROR_PATTERN.test(clean)) return fallback;
  return clean.length > 150 ? fallback : clean;
}

function safeErrorTitle(message: string | null) {
  const clean = message ?? "";
  if (USER_ACTION_ERROR_PATTERN.test(clean) || clean.toLowerCase().includes("chưa có dữ liệu")) {
    return "Cần kiểm tra lại thông tin";
  }
  return "Dữ liệu đang được cập nhật";
}

function canRetryError(message: string | null) {
  const clean = message ?? "";
  return !USER_ACTION_ERROR_PATTERN.test(clean);
}

function RoutedApp() {
  const location = useLocation();
  const navigate = useNavigate();
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
      fetchNews(signal),
      fetchGuides(undefined, section === "guides" ? 300 : 12, signal)
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
        setError("Chưa có dữ liệu giá cho sản phẩm này.");
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
        setError("Chưa có dữ liệu giá cho tỉnh/vùng trồng này.");
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
      setError(err instanceof Error ? err.message : "Không tải được dữ liệu.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const controller = new AbortController();
    void loadContent(controller.signal).catch((err) => {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setError(err instanceof Error ? err.message : "Không tải được nội dung.");
    });
    const newsRefreshTimer = window.setInterval(() => {
      void fetchNews()
        .then(setNewsArticles)
        .catch((err) => {
          console.warn("[App] background news refresh failed", err);
        });
    }, 15 * 60 * 1000);
    return () => {
      controller.abort();
      window.clearInterval(newsRefreshTimer);
    };
  }, []);

  useEffect(() => {
    const route = getInitialRoute(location.pathname, location.search);
    const canonicalUrl = routeToUrl(route);
    const canonicalWithSearch =
      route.section === "news" && !route.newsSlug && location.search ? `${canonicalUrl}${location.search}` : canonicalUrl;
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
  }, [location.pathname, location.search, navigate]);

  useEffect(() => {
    const onInternalLinkClick = (event: MouseEvent) => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const target = event.target instanceof Element ? event.target.closest<HTMLAnchorElement>('a[href^="/"]') : null;
      if (!target || target.target || target.hasAttribute("download")) return;
      const url = new URL(target.href, window.location.origin);
      if (url.origin !== window.location.origin) return;
      event.preventDefault();
      navigate(`${url.pathname}${url.search}${url.hash}`);
    };
    document.addEventListener("click", onInternalLinkClick);
    return () => document.removeEventListener("click", onInternalLinkClick);
  }, [navigate]);

  useEffect(() => {
    if (section !== "analytics") return;
    const controller = new AbortController();
    void loadData(controller.signal);
    return () => controller.abort();
  }, [section, crop, regionId, varietyId, days]);

  useEffect(() => {
    if (section !== "guides" || guides.length >= 80) return;
    const controller = new AbortController();
    void fetchGuides(undefined, 300, controller.signal)
      .then(setGuides)
      .catch((err) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Không tải được hướng dẫn kỹ thuật.");
      });
    return () => controller.abort();
  }, [section, guides.length]);

  useEffect(() => {
    localStorage.setItem("agri_price.watchlist", JSON.stringify(watchlist));
  }, [watchlist]);

  useEffect(() => {
    if (!authToken || !user) return;
    void loadAccountData(authToken, user);
  }, [authToken, user]);

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
    if (freshnessDays <= 1) return "C\u1eadp nh\u1eadt h\u00f4m nay";
    if (freshnessDays <= 3) return `C\u1eadp nh\u1eadt ${freshnessDays} ng\u00e0y tr\u01b0\u1edbc`;
    if (freshnessDays <= 14) return `D\u1eef li\u1ec7u ${freshnessDays} ng\u00e0y tr\u01b0\u1edbc`;
    return `D\u1eef li\u1ec7u c\u0169 ${freshnessDays} ng\u00e0y`;
  }, [freshnessDays]);
  const freshnessClass = freshnessDays == null
    ? ""
    : freshnessDays <= 3
      ? "fresh"
      : freshnessDays <= 14
        ? "stale"
        : "very-stale";
  const cropLabel = cropLabels[crop];
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
      setError(err instanceof Error ? err.message : "Không lưu được danh sách ghim");
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
    navigate(forecastPath(nextCrop as CropType));
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
    navigate(forecastPath(nextCrop));
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
      nextView === "latest"
        ? "/tin-tuc"
        : `/tin-tuc/${newsViewPaths[nextView as PriceNewsView]}`
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
    navigate(routeToUrl({ section: nextSection, crop, newsView: "latest", newsSlug: "", guideSlug: "", notFound: false }));
  }

  async function handleAuth(mode: "login" | "register") {
    setError(null);
    const email = authEmail.trim().toLowerCase();
    const password = authPassword.trim();
    const displayName = authName.trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError("Email không hợp lệ");
      return;
    }
    if (password.length < 8 || !/\d/.test(password)) {
      setError("Mật khẩu cần tối thiểu 8 ký tự và có ít nhất 1 chữ số");
      return;
    }
    if (mode === "register" && displayName.length < 2) {
      setError("Vui lòng nhập họ tên");
      return;
    }
    try {
      const session = mode === "login"
        ? await signIn(email, password)
        : await signUp(email, password, displayName);
      setAuthOpen(false);
      await loadAccountData(session.access_token, session.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không đăng nhập được");
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
      setError(err instanceof Error ? err.message : "Không chạy được job");
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
      setNewsArticles(await fetchNews());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không cập nhật được tin tức");
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

  const showErrorBanner = Boolean(error && (section !== "methodology" || authOpen));

  return (
    <IconContext.Provider value={{ size: 18, weight: "regular", mirrored: false }}>
    <main className={section === "analytics" ? `app-shell forecast-shell crop-${crop}` : "app-shell"}>
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
        onAuthOpenChange={setAuthOpen}
        onAuthModeChange={setAuthMode}
        onAuthNameChange={setAuthName}
        onAuthEmailChange={setAuthEmail}
        onAuthPasswordChange={setAuthPassword}
        onAuthSubmit={(mode) => void handleAuth(mode)}
      />

      {section === "analytics" ? <TickerTape points={tickerPoints} /> : null}

      {section === "analytics" ? (
        <>
          <header className="market-quote-header">
            <div className="quote-main">
              <div className="quote-title-row">
                <ActiveIcon size={20} />
                <h1>
                  <span className="quote-h1-line1">Giá {cropLabel} hôm nay{"\u00a0"}</span>
                  <span className="quote-h1-line2">
                    {`Dự báo 30 ngày${selectedRegion?.province ? ` tại ${selectedRegion.province}` : ""}`}
                  </span>
                </h1>
                <FreshnessBanner />
              </div>
              <div className="quote-meta">
                <span>{selectedRegion?.province ?? selectedRegion?.region_name ?? "Vùng trồng"}</span>
                <span>{selectedVariety?.name ?? "Giống"}</span>
                <span>VND/kg</span>
              </div>
              <div className="quote-price-row">
                <strong className="num">{latestPrice.toLocaleString("vi-VN")}</strong>
                <span className={quoteChangePct >= 0 ? "quote-change positive num" : "quote-change negative num"}>
                  {quoteChangePct >= 0 ? "+" : ""}
                  {quoteChangePct.toFixed(2)}%
                </span>
                <small>VND/kg · {selectedVariety?.name ?? "Giống"}</small>
                {freshnessLabel ? (
                  <small className={`freshness-badge ${freshnessClass}`}>{freshnessLabel}</small>
                ) : null}
              </div>
              <p>Dữ liệu giá, dự báo và cảnh báo theo vùng trồng đang chọn.</p>
            </div>

            <div className="quote-side">
              <button
                type="button"
                className="quote-refresh-button"
                onClick={() => void loadData()}
                disabled={loading}
                aria-label="L\u00e0m m\u1edbi gi\u00e1"
              >
                <RefreshCw size={18} />
                {loading ? "Đang làm mới..." : "Làm mới giá"}
              </button>
              <div className="quote-range">
                <span>Khung dữ liệu</span>
                <strong className="num">{days} ngày</strong>
              </div>
              <div className="quote-range">
                <span>Giá mới nhất</span>
                <strong className="num">{latestPrice.toLocaleString("vi-VN")}</strong>
              </div>
              {user?.is_admin ? (
                <button
                  type="button"
                  className="quote-side-action"
                  onClick={() => void runJob("scrape")}
                  disabled={platformBusy}
                  title="Chạy scrape giá ngay"
                >
                  <RefreshCw size={14} />
                  {platformBusy ? "Đang quét..." : "Quét giá"}
                </button>
              ) : null}
            </div>
          </header>

          <nav className="market-subnav" aria-label="Công cụ phân tích giá">
            <button type="button" className={analyticsTab === "chart" ? "active" : ""} onClick={() => setAnalyticsTab("chart")}>Biểu đồ</button>
            <button type="button" className={analyticsTab === "analysis" ? "active" : ""} onClick={() => setAnalyticsTab("analysis")}>Phân tích</button>
            <button type="button" className={analyticsTab === "technical" ? "active" : ""} onClick={() => setAnalyticsTab("technical")}>Kỹ thuật</button>
            <button type="button" className={analyticsTab === "data" ? "active" : ""} onClick={() => setAnalyticsTab("data")}>Dữ liệu</button>
          </nav>

          <section className="control-band">
            <div className="filter-group">
              <Filter size={18} />
              <label>
                Tỉnh/vùng trồng
                <select value={regionId} onChange={(event) => setRegionId(Number(event.target.value))}>
                  {regions.length === 0 ? (
                    <option value={regionId}>Đang tải</option>
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
                Giống
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
              <span>Giá mới nhất</span>
              <strong className="num">{latestPrice.toLocaleString("vi-VN")} VND/kg</strong>
            </div>
          </section>
        </>
      ) : null}

      {showErrorBanner ? (
        <div className="error-banner" role="status" aria-live="polite">
          <div className="error-banner-copy">
            <strong>{safeErrorTitle(error)}</strong>
            <span>{safeErrorCopy(error)}</span>
          </div>
          {canRetryError(error) ? <button type="button" onClick={retryAfterError}>Thử lại</button> : null}
        </div>
      ) : null}
      {loading && section === "analytics" ? <div className="loading">Đang tải dữ liệu thị trường...</div> : null}

      <Suspense fallback={<div className="section-fallback">Đang tải giao diện...</div>}>
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
            title={`Giá ${cropSeoLabels[crop]} hôm nay & dự báo 30 ngày`}
            description={`Cập nhật giá ${cropSeoLabels[crop]} mới nhất theo tỉnh, vùng trồng và giống. Xem biểu đồ lịch sử, dự báo 30 ngày, cảnh báo bán và độ tin cậy dữ liệu.`}
            canonical={forecastPath(crop)}
            schemaJsonLd={buildPriceSchema({
              cropLabel: cropSeoLabels[crop],
              regionLabel: selectedRegion?.province ?? selectedRegion?.region_name ?? "Việt Nam",
              varietyLabel: selectedVariety?.name ?? cropSeoLabels[crop],
              latestPrice,
              historical: visibleHistorical
            })}
          />
          {analyticsTab === "chart" ? (
            <>
              <section className="chart-toolbar">
                <div className="chart-control-group">
                  <span className="control-label">Khoảng thời gian</span>
                  <div className="segmented">
                  {[30, 90, 180].map((value) => (
                    <button
                      type="button"
                      className={days === value ? "active" : ""}
                      key={value}
                      onClick={() => setDays(value)}
                    >
                      {value} ngày
                    </button>
                  ))}
                  </div>
                </div>
                <div className="chart-control-group chart-control-group--layers">
                  <span className="control-label">Lớp dữ liệu</span>
                  <div className="layer-toggles">
                  <button type="button" className={layers.price ? "active" : ""} onClick={() => toggleLayer("price")}>Giá</button>
                  <button type="button" className={layers.forecast ? "active" : ""} onClick={() => toggleLayer("forecast")}>Dự báo</button>
                  <button
                    type="button"
                    className={layers.rain && hasRainData ? "active" : ""}
                    onClick={() => toggleLayer("rain")}
                    disabled={!hasRainData}
                    title={hasRainData ? undefined : "Chưa có dữ liệu lượng mưa cho khoảng thời gian này"}
                  >
                    Mưa
                  </button>
                  <button type="button" className={layers.signals ? "active" : ""} onClick={() => toggleLayer("signals")}>Cảnh báo</button>
                  </div>
                </div>
                <button type="button" className="pin-button" onClick={() => void addWatchlist()}>
                  <Pin size={16} />
                Ghim thị trường
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
            regionLabel={selectedRegion?.province ?? selectedRegion?.region_name ?? "vùng đang chọn"}
            varietyLabel={selectedVariety?.name ?? "giống đang chọn"}
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
          onViewChange={openNews}
          onOpenAnalytics={openAnalytics}
        />
      ) : null}
      {!notFound && section === "guides" && guideSlug ? <GuideDetailPage slug={guideSlug} /> : null}
      {!notFound && section === "guides" && !guideSlug ? <GuideLibrary guides={guides} /> : null}
      {!notFound && section === "fertilizer" ? <FertilizerAdvisor /> : null}
      {!notFound && section === "fertilizerMethodology" ? <FertilizerMethodology /> : null}
      {!notFound && section === "methodology" ? <ForecastMethodology /> : null}
      </Suspense>
      <SiteFooter
        onOpenNews={() => openNews("latest")}
        onOpenGuides={() => changeSection("guides")}
        onOpenAnalytics={() => {
          openAnalytics(crop);
          setAnalyticsTab("chart");
        }}
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
