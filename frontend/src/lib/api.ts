export type PricePoint = {
  timestamp: string;
  region_id: number | null;
  variety_id: number | null;
  variety: string;
  region: string;
  province: string | null;
  quality_grade: string | null;
  exchange_source: string | null;
  min_price_vnd: number | null;
  max_price_vnd: number | null;
  volume_traded_tons: number | null;
  temp_max_celsius: number | null;
  precipitation_mm: number | null;
  maturity_index: number | null;
  data_kind: string;
  is_synthetic: boolean;
  farmer_report_price_vnd: number | null;
  farmer_reported_at: string | null;
  farmer_report_quality_grade: string | null;
};

export type ForecastPoint = {
  timestamp: string;
  forecast_price_vnd: number;
  confidence_low_vnd: number;
  confidence_high_vnd: number;
};

export type TradingSignal = {
  timestamp: string;
  price_vnd: number;
  signal: string;
  reason: string;
  prominence: number;
};

export type Region = {
  region_id: number;
  region_name: string;
  province: string | null;
  export_code: string | null;
  risk_level_index: number;
};

export type Variety = {
  variety_id: number;
  name: string;
  description: string | null;
};

export type ModelMetrics = {
  rmse_usd_per_kg: number;
  mae_usd_per_kg: number;
  rmse_vnd_per_kg: number | null;
  mae_vnd_per_kg: number | null;
  lookback_days: number;
  forecast_horizon_days: number;
  backtest_samples: number;
  evaluated_series: number;
  note: string | null;
};

export type CropType = "sau_rieng" | "ca_phe" | "ho_tieu" | "lua";

export type AuthUser = {
  user_id: number;
  email: string;
  display_name: string;
  is_admin: boolean;
};

export type AuthSession = {
  access_token: string;
  token_type: "bearer";
  user: AuthUser;
};

export type DataQuality = {
  score: number;
  history_points: number;
  observed_points: number;
  synthetic_points: number;
  observed_ratio: number;
  source_count: number;
  sources: string[];
  latest_timestamp: string | null;
  freshness_days: number | null;
  note: string;
  risk_flags: string[];
};

export type Mover = {
  variety: string;
  region: string;
  province: string | null;
  latest_price_vnd: number;
  previous_price_vnd: number;
  change_vnd: number;
  change_pct: number;
  timestamp: string;
};

export type TopMovers = {
  gainers: Mover[];
  losers: Mover[];
};

export type HeatmapCell = {
  region_id: number;
  region: string;
  province: string | null;
  avg_price_vnd: number;
  change_pct: number;
  variety_count: number;
  quality_score: number;
};

export type StrategyAlert = {
  level: string;
  title: string;
  message: string;
};

export type MarketIndex = {
  name: string;
  latest_value_vnd: number;
  change_pct_7d: number;
  series: { date: string; index_price_vnd: number }[];
};

export type Driver = {
  name: string;
  impact: number;
  direction: string;
  detail: string;
};

export type ChangeExplanation = {
  summary: string;
  drivers: Driver[];
  recommendation: string;
};

export type MarketComparison = {
  selected_avg_price_vnd: number;
  peers: { label: string; avg_price_vnd: number; premium_pct: number }[];
};

export type WatchlistItem = {
  item_id: number;
  crop_type: CropType;
  region_id: number;
  variety_id: number;
  label: string;
  created_at: string;
};

export type PlatformJobRun = {
  job_id: number;
  job_name: string;
  started_at: string;
  finished_at: string | null;
  status: string;
  summary: string | null;
  error_message: string | null;
};

export type ModelTrainingRun = {
  run_id: number;
  crop_type: CropType;
  started_at: string;
  finished_at: string | null;
  status: string;
  rmse_vnd_per_kg: number | null;
  mae_vnd_per_kg: number | null;
  backtest_samples: number;
  evaluated_series: number;
  note: string | null;
};

export type NewsArticle = {
  article_id: number;
  source_name: string;
  source_url: string;
  title: string;
  summary: string;
  excerpt: string | null;
  category: string;
  image_url: string | null;
  published_at: string | null;
  scraped_at: string;
};

export type GuidePost = {
  post_id: number;
  slug: string;
  title: string;
  crop_type: string | null;
  category: string;
  summary: string;
  content: string;
  author: string;
  published_at: string;
};

export type Subscriber = {
  subscriber_id: number;
  email: string;
  source: string | null;
  created_at: string;
  updated_at: string;
};

export type UserPriceReportPayload = {
  crop_type: CropType;
  region_id: number;
  variety_id: number;
  price_vnd: number;
  quality_grade?: string | null;
  reporter_name?: string | null;
  note?: string | null;
};

export type UserPriceReport = {
  report_id: number;
  crop_type: CropType;
  region_id: number;
  variety_id: number;
  price_vnd: number;
  quality_grade: string | null;
  approved_for_training: boolean;
  created_at: string;
  message: string;
};

export type FertilizerCrop = "robusta_coffee" | "black_pepper" | "durian";
export type FertilizerStage = "mature_kinh_doanh" | "establishment_y1" | "establishment_y2" | "establishment_y3" | "establishment_y4" | "establishment_y5" | "fruit_fill";
export type SoilTexture = "basaltic_red" | "grey_granite" | "gneiss" | "acrisol" | "alluvial";

export type FertilizerRequest = {
  crop: FertilizerCrop;
  growth_stage: FertilizerStage;
  yield_target_t_ha: number | null;
  tree_density_per_ha: number | null;
  soil: {
    texture: SoilTexture;
    ph_kcl: number;
    organic_carbon_pct: number | null;
    total_n_pct: number | null;
    available_p_method: "bray_ii" | "mehlich_3";
    available_p_mg_per_100g: number | null;
    exchangeable_k_method: "nh4oac";
    exchangeable_k2o_mg_per_100g: number | null;
    cec_cmolc_per_kg: number | null;
    sample_depth_cm?: number | null;
    sample_date?: string | null;
  };
  location?: { province?: string | null; district?: string | null; elevation_m?: number | null };
  climate?: { annual_rainfall_mm?: number | null; irrigation_available?: boolean | null } | null;
  field?: { slope_pct?: number | null; years_under_current_crop?: number | null } | null;
  preferences?: { language?: "vi" | "en"; include_product_mix?: boolean; preferred_brand?: string | null; organic_available_t_ha?: number | null };
};

export type FertilizerWarning = {
  level: string;
  code: string;
  message_vi: string;
  message_en: string;
};

export type FertilizerRecommendation = {
  request_id: string;
  timestamp: string;
  engine_version: string;
  knowledge_base_version: string;
  crop: FertilizerCrop;
  crop_name_vi: string;
  calibration_status: string;
  soil_categorization: Record<string, unknown>;
  recommendation: {
    annual_total: {
      n_kg_ha: number;
      n_kg_ha_before_adjustment: number;
      p2o5_kg_ha: number;
      p2o5_kg_ha_before_adjustment: number;
      k2o_kg_ha: number;
      k2o_kg_ha_before_adjustment: number;
      lime_kg_ha: number;
      organic_t_ha?: number;
      organic_kg_tree?: number;
      adjustment_factors: {
        n_combined: number;
        p_combined: number;
        k_combined: number;
        breakdown: { name: string; code: string; n: number; p: number; k: number; rationale_vi: string; missing: boolean }[];
      };
      rationale_vi: string;
    };
    splits: {
      split_index: number;
      name_vi: string;
      calendar_window: string;
      n_kg_ha: number;
      p2o5_kg_ha: number;
      k2o_kg_ha: number;
      notes_vi: string;
      commercial_products: { sku: string; name_vi: string; kg_ha_yr: number; bags_50kg_ha: number }[];
    }[];
    product_mix_options: {
      option_id: number;
      label_vi: string;
      products: { sku: string; name_vi: string; kg_ha_yr: number; bags_50kg_ha: number }[];
    }[];
  };
  confidence: { overall: string; data_quality_score: number; calibration_basis: string[]; limitations: string[]; missing_inputs: string[] };
  warnings: FertilizerWarning[];
  rationale: { calculation_trace: string[]; sources_cited: { id: string; title: string }[] };
};

const DEFAULT_API_BASE_URL = import.meta.env.PROD ? "https://api.dubaonongsan.com" : "";
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL).replace(/\/$/, "");
const jsonHeaders = { "Content-Type": "application/json" };

function apiUrl(path: string) {
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

function authHeaders(token?: string) {
  return token ? { ...jsonHeaders, Authorization: `Bearer ${token}` } : jsonHeaders;
}

async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(apiUrl(url), { headers: jsonHeaders, signal });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

async function authJson<T>(url: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(url), { ...init, headers: authHeaders(token) });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export function fetchHistorical(
  crop: CropType,
  regionId: number,
  varietyId: number,
  options: { qualityGrade?: string; limit?: number; signal?: AbortSignal } = {}
) {
  const { qualityGrade, limit = 200, signal } = options;
  const gradeParam = qualityGrade ? `&quality_grade=${encodeURIComponent(qualityGrade)}` : "";
  return getJson<PricePoint[]>(
    `/api/v1/analytics/historical-prices?crop=${crop}&region_id=${regionId}&variety=${varietyId}${gradeParam}&limit=${limit}`,
    signal
  );
}

export function fetchForecast(crop: CropType, regionId: number, varietyId: number, signal?: AbortSignal) {
  return getJson<ForecastPoint[]>(
    `/api/v1/analytics/forecast-30-days?crop=${crop}&region_id=${regionId}&variety=${varietyId}`,
    signal
  );
}

export function fetchSignals(crop: CropType, regionId: number, varietyId: number, signal?: AbortSignal) {
  return getJson<TradingSignal[]>(
    `/api/v1/analytics/trading-signals?crop=${crop}&region_id=${regionId}&variety=${varietyId}`,
    signal
  );
}

export function fetchRegions(crop: CropType, signal?: AbortSignal) {
  return getJson<Region[]>(`/api/v1/metadata/regions?crop=${crop}`, signal);
}

export function fetchVarieties(crop: CropType, signal?: AbortSignal) {
  return getJson<Variety[]>(`/api/v1/metadata/varieties?crop=${crop}`, signal);
}

export function fetchAvailableVarieties(crop: CropType, regionId: number, signal?: AbortSignal) {
  return getJson<Variety[]>(`/api/v1/metadata/available-varieties?crop=${crop}&region_id=${regionId}`, signal);
}

export function fetchTickerPrices(crop: CropType, signal?: AbortSignal) {
  return getJson<PricePoint[]>(`/api/v1/analytics/ticker-prices?crop=${crop}&limit=60`, signal);
}

export function fetchDailyPriceBoard(crop: CropType, signal?: AbortSignal) {
  return getJson<PricePoint[]>(`/api/v1/analytics/daily-price-board?crop=${crop}&limit=1000`, signal);
}

export function fetchMetrics(crop: CropType, regionId: number, varietyId: number, signal?: AbortSignal) {
  return getJson<ModelMetrics>(
    `/api/v1/analytics/model-metrics?crop=${crop}&region_id=${regionId}&variety=${varietyId}`,
    signal
  );
}

export function fetchDataQuality(crop: CropType, regionId: number, varietyId: number, signal?: AbortSignal) {
  return getJson<DataQuality>(
    `/api/v1/analytics/data-quality?crop=${crop}&region_id=${regionId}&variety=${varietyId}`,
    signal
  );
}

export function fetchTopMovers(crop: CropType, signal?: AbortSignal) {
  return getJson<TopMovers>(`/api/v1/analytics/top-movers?crop=${crop}&limit=6`, signal);
}

export function fetchHeatmap(crop: CropType, signal?: AbortSignal) {
  return getJson<HeatmapCell[]>(`/api/v1/analytics/heatmap?crop=${crop}`, signal);
}

export function fetchStrategyAlerts(crop: CropType, regionId: number, varietyId: number, signal?: AbortSignal) {
  return getJson<StrategyAlert[]>(
    `/api/v1/analytics/strategy-alerts?crop=${crop}&region_id=${regionId}&variety=${varietyId}`,
    signal
  );
}

export function fetchMarketIndex(crop: CropType, signal?: AbortSignal) {
  return getJson<MarketIndex>(`/api/v1/analytics/market-index?crop=${crop}`, signal);
}

export function fetchChangeExplanation(crop: CropType, regionId: number, varietyId: number, signal?: AbortSignal) {
  return getJson<ChangeExplanation>(
    `/api/v1/analytics/explain-change?crop=${crop}&region_id=${regionId}&variety=${varietyId}`,
    signal
  );
}

export function fetchMarketComparison(crop: CropType, regionId: number, varietyId: number, signal?: AbortSignal) {
  return getJson<MarketComparison>(
    `/api/v1/analytics/compare-markets?crop=${crop}&region_id=${regionId}&variety=${varietyId}`,
    signal
  );
}

export function exportCsvUrl(crop: CropType, regionId: number, varietyId: number) {
  return apiUrl(`/api/v1/analytics/export.csv?crop=${crop}&region_id=${regionId}&variety=${varietyId}`);
}

export function exportXlsxUrl(crop: CropType, regionId: number, varietyId: number) {
  return apiUrl(`/api/v1/analytics/export.xlsx?crop=${crop}&region_id=${regionId}&variety=${varietyId}`);
}

export function exportPdfUrl(crop: CropType, regionId: number, varietyId: number) {
  return apiUrl(`/api/v1/analytics/export.pdf?crop=${crop}&region_id=${regionId}&variety=${varietyId}`);
}

export function login(email: string, password: string) {
  return getAuth("/api/v1/auth/login", { email, password });
}

export function register(email: string, password: string, displayName?: string) {
  return getAuth("/api/v1/auth/register", { email, password, display_name: displayName });
}

function getAuth(url: string, payload: Record<string, string | undefined>) {
  return fetch(apiUrl(url), {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify(payload)
  }).then(async (response) => {
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      const detail = Array.isArray(payload?.detail)
        ? payload.detail[0]?.msg
        : payload?.detail;
      throw new Error(detail || `${response.status} ${response.statusText}`);
    }
    return response.json() as Promise<AuthSession>;
  });
}

export function fetchWatchlist(token: string) {
  return authJson<WatchlistItem[]>("/api/v1/watchlist", token);
}

export function saveWatchlistItem(token: string, item: Omit<WatchlistItem, "item_id" | "created_at">) {
  return authJson<WatchlistItem>("/api/v1/watchlist", token, {
    method: "POST",
    body: JSON.stringify(item)
  });
}

export function fetchPlatformJobs(token: string) {
  return authJson<PlatformJobRun[]>("/api/v1/platform/jobs", token);
}

export function fetchModelRuns(token: string) {
  return authJson<ModelTrainingRun[]>("/api/v1/platform/model-runs", token);
}

export function runPlatformJob(token: string, job: "scrape" | "news" | "data-quality" | "retrain" | "weather") {
  return authJson<Record<string, unknown>>(`/api/v1/platform/jobs/${job}`, token, { method: "POST" });
}

export function fetchNews(signal?: AbortSignal) {
  return getJson<NewsArticle[]>("/api/v1/content/news?limit=2000", signal);
}

export function fetchNewsDetail(slug: string, signal?: AbortSignal) {
  return getJson<NewsArticle>(`/api/v1/content/news/${encodeURIComponent(slug)}`, signal);
}

export function scrapeNews(token: string) {
  return authJson<Record<string, unknown>>("/api/v1/content/news/scrape", token, { method: "POST" });
}

export function fetchGuides(crop?: CropType, limit = 120, signal?: AbortSignal) {
  const cropParam = crop ? `?crop=${crop}&limit=${limit}` : `?limit=${limit}`;
  return getJson<GuidePost[]>(`/api/v1/content/guides${cropParam}`, signal);
}

export function fetchGuideDetail(slug: string, signal?: AbortSignal) {
  return getJson<GuidePost>(`/api/v1/content/guides/${encodeURIComponent(slug)}`, signal);
}

export function subscribeNewsletter(email: string) {
  return fetch(apiUrl("/api/v1/content/subscribers"), {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify({ email, source: "footer" })
  }).then(async (response) => {
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    return response.json() as Promise<Subscriber>;
  });
}

export function reportLocalPrice(payload: UserPriceReportPayload) {
  return fetch(apiUrl("/api/v1/content/price-reports"), {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify(payload)
  }).then(async (response) => {
    if (!response.ok) {
      const errorPayload = await response.json().catch(() => null);
      throw new Error(errorPayload?.detail || `${response.status} ${response.statusText}`);
    }
    return response.json() as Promise<UserPriceReport>;
  });
}

export function fetchFertilizerCrops(signal?: AbortSignal) {
  return getJson<{ crop: FertilizerCrop; name_vi: string; calibration_status: string; confidence: string; valid_yield_range_t_ha: [number, number]; valid_textures: SoilTexture[] }[]>(
    "/api/v1/fertilizer/crops",
    signal
  );
}

export function recommendFertilizer(payload: FertilizerRequest, signal?: AbortSignal) {
  return fetch(apiUrl("/api/v1/fertilizer/recommend"), {
    method: "POST",
    headers: jsonHeaders,
    signal,
    body: JSON.stringify(payload)
  }).then(async (response) => {
    if (!response.ok) {
      const errorPayload = await response.json().catch(() => null);
      throw new Error(errorPayload?.detail || `${response.status} ${response.statusText}`);
    }
    return response.json() as Promise<FertilizerRecommendation>;
  });
}
