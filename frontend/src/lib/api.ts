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

export type AgriInputProduct = {
  product_id: number;
  slug: string;
  name: string;
  category: "fertilizer";
  product_type: string;
  nutrient_profile: string | null;
  standard_unit: string;
  package_label: string | null;
  package_size_kg: number | null;
  notes: string | null;
  is_active: boolean;
};

export type AgriInputPricePoint = {
  observation_id: number;
  product_id: number;
  product_slug: string;
  product_name: string;
  product_type: string;
  observed_at: string;
  province: string;
  region_name: string | null;
  brand: string | null;
  seller_name: string | null;
  source_name: string;
  source_url: string | null;
  package_price_vnd: number | null;
  normalized_price_vnd: number;
  normalized_unit: string;
  package_size_kg: number | null;
  package_label: string | null;
  confidence_score: number;
  data_kind: string;
};

export type AgriInputForecastPoint = {
  timestamp: string;
  forecast_price_vnd: number;
  confidence_low_vnd: number;
  confidence_high_vnd: number;
  normalized_price_vnd: number;
  normalized_low_vnd: number;
  normalized_high_vnd: number;
  model_kind: string;
};

export type AgriInputForecast = {
  points: AgriInputForecastPoint[];
  model_kind: string;
  history_points: number;
  volatility: number;
  latest_observed_at: string | null;
};

export type WorldFertilizerCommodity = "urea" | "dap" | "kali_mop";

export type WorldFertilizerCommodityInfo = {
  commodity_slug: WorldFertilizerCommodity;
  name_vi: string;
  name_en: string;
  quote_type: string;
  driver_note_vi: string;
};

export type WorldFertilizerHistoryPoint = {
  observed_at: string;
  price_usd_per_tonne: number;
  quote_type: string;
  source: string;
  source_url: string | null;
  confidence_score: number;
};

export type WorldFertilizerForecastPoint = {
  date: string;
  price_usd_per_tonne: number;
  price_low_usd_per_tonne: number;
  price_high_usd_per_tonne: number;
  daily_pct_change: number;
  cumulative_pct_from_today: number;
};

export type WorldFertilizerWeeklyPoint = {
  week_index: number;
  week_label_vi: string;
  date_from: string;
  date_to: string;
  median_price_usd_per_tonne: number;
  low_price_usd_per_tonne?: number | null;
  high_price_usd_per_tonne?: number | null;
  pct_change_vs_prev_week: number;
  pct_change_vs_today: number;
  daily_breakdown: WorldFertilizerForecastPoint[];
};

export type WorldFertilizerForecast = {
  commodity_slug: WorldFertilizerCommodity;
  commodity_name_vi: string;
  quote_type: string | null;
  base_price_usd_per_tonne: number | null;
  base_observed_at: string | null;
  model_kind: string;
  history_points: number;
  volatility: number;
  volatility_daily?: number | null;
  source_mode?: string | null;
  data_quality?: {
    level?: string;
    source_mode?: string;
    sources?: string[];
    history_points?: number;
    latest_source?: string | null;
    latest_observed_at?: string | null;
    last_source_check_at?: string | null;
    staleness_days?: number;
    reason_vi?: string;
  } | null;
  forecast_daily: WorldFertilizerForecastPoint[];
  forecast_weekly: WorldFertilizerWeeklyPoint[];
  note_vi: string;
};

export const EMPTY_INPUT_FORECAST: AgriInputForecast = {
  points: [],
  model_kind: "no-data",
  history_points: 0,
  volatility: 0,
  latest_observed_at: null
};

export type RoiCalculateRequest = {
  crop: CropType;
  crop_area_ha: number;
  expected_yield_t_ha: number;
  expected_sell_price_vnd_per_kg: number;
  region_id?: number | null;
  variety_id?: number | null;
  fertilizer_total_cost_vnd_per_ha?: number | null;
  fertilizer_lines: { product_slug?: string | null; name?: string | null; kg_per_ha: number; price_vnd_per_kg?: number | null }[];
  other_input_cost_vnd_per_ha: number;
  labor_cost_vnd_per_ha: number;
  save?: boolean;
};

export type RoiScenario = {
  scenario: "pessimistic" | "expected" | "optimistic";
  label_vi: string;
  sell_price_vnd_per_kg: number;
  yield_t_ha: number;
  revenue_vnd: number;
  total_cost_vnd: number;
  net_profit_vnd: number;
  roi_pct: number;
  rationale_vi: string;
};

export type RoiCalculateResponse = {
  scenario_id: number | null;
  fertilizer_input_mode: "simple" | "detail" | "db_reference";
  fertilizer_cost_vnd_per_ha: number;
  total_revenue_vnd: number;
  total_cost_vnd: number;
  net_profit_vnd: number;
  roi_pct: number;
  scenarios: RoiScenario[];
  confidence_score: number;
  forecast_model_kind: string;
  breakdown: {
    product_slug: string | null;
    product_name: string;
    name?: string | null;
    kg_per_ha: number | null;
    price_vnd_per_kg: number | null;
    cost_vnd_per_ha: number;
    price_source?: string;
    source_name: string;
    observed_at: string | null;
  }[];
  sensitivity: { matrix: { sell_price_delta_pct: number; fertilizer_price_delta_pct: number; roi_pct: number; net_profit_vnd: number }[] };
  notes_vi: string[];
  recommendations_vi: string[];
};

export type CropType = "sau_rieng" | "ca_phe" | "ho_tieu" | "lua";

export type UsdVndRate = {
  currency_code: "USD";
  buy: number | null;
  transfer: number;
  sell: number | null;
  as_of: string | null;
  source: string;
  raw_datetime: string | null;
  stale?: boolean;
};

export type AuthUser = {
  user_id: number;
  email: string;
  display_name: string;
  is_admin: boolean;
};

export type AuthSession = {
  access_token: string;
  refresh_token: string;
  refresh_expires_at: string;
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
export type FertilizerStage = "mature_kinh_doanh" | "establishment_y1" | "establishment_y2" | "establishment_y3" | "establishment_y4" | "establishment_y5" | "fruit_set" | "fruit_fill";
export type SoilTexture = "basaltic_red" | "grey_granite" | "gneiss" | "acrisol" | "alluvial";
export type FertilizerKSource = "kcl" | "k2so4" | "kno3";

export type FertilizerRequest = {
  crop: FertilizerCrop;
  variety?: string | null;
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
    available_p_mg_per_kg?: number | null;
    exchangeable_k_method: "nh4oac";
    exchangeable_k2o_mg_per_100g: number | null;
    cec_cmolc_per_kg: number | null;
    sample_depth_cm?: number | null;
    sample_date?: string | null;
  };
  location?: { province?: string | null; district?: string | null; elevation_m?: number | null };
  climate?: { annual_rainfall_mm?: number | null; irrigation_available?: boolean | null } | null;
  field?: { slope_pct?: number | null; years_under_current_crop?: number | null } | null;
  preferences?: { language?: "vi" | "en"; include_product_mix?: boolean; preferred_brand?: string | null; preferred_k_source?: FertilizerKSource | null; organic_available_t_ha?: number | null };
};

export type FertilizerWarning = {
  level: string;
  code: string;
  message_vi: string;
  message_en: string;
};

export type FertilizerRecommendation = {
  request_id: string;
  session_id?: string;
  session_code?: string;
  timestamp: string;
  engine_version: string;
  knowledge_base_version: string;
  crop: FertilizerCrop;
  variety?: string | null;
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
      n_pct: number;
      p2o5_pct: number;
      k2o_pct: number;
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
  confidence: {
    overall: string;
    calibration_tier?: string;
    score?: number;
    badge_vi?: string;
    badge_icon?: string;
    explain_vi?: string;
    data_quality_score: number;
    calibration_basis: string[];
    limitations: string[];
    missing_inputs: string[];
  };
  warnings: FertilizerWarning[];
  rationale: { calculation_trace: string[]; sources_cited: { id: string; title: string }[] };
};

export type YieldFeedbackPayload = {
  actual_yield_t_ha: number;
  harvest_date?: string | null;
  fertilizer_followed_pct?: number | null;
  rating?: number | null;
  note?: string | null;
  contact_phone?: string | null;
};

export type YieldFeedbackResponse = {
  session_id: string;
  session_code: string;
  feedback_id: number;
  message: string;
};

const DEFAULT_API_BASE_URL = import.meta.env.PROD ? "https://api.dubaonongsan.com" : "";
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL).replace(/\/$/, "");
const jsonHeaders = { Accept: "application/json", "Content-Type": "application/json" };
const GET_RETRY_DELAY_MS = 450;
const AUTH_EXPIRED_EVENT = "marketai:auth-expired";
const inFlightGetRequests = new Map<string, Promise<unknown>>();
let authRecoveryHandler: (() => Promise<string | null>) | null = null;

function apiUrl(path: string) {
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

function authHeaders(token?: string) {
  return token ? { ...jsonHeaders, Authorization: `Bearer ${token}` } : jsonHeaders;
}

class ApiRequestError extends Error {
  status?: number;
  transient: boolean;

  constructor(message: string, options: { status?: number; transient?: boolean } = {}) {
    super(message);
    this.name = "ApiRequestError";
    this.status = options.status;
    this.transient = Boolean(options.transient);
  }
}

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function mergedJsonHeaders(headers?: HeadersInit) {
  const merged = new Headers(jsonHeaders);
  if (headers) {
    new Headers(headers).forEach((value, key) => merged.set(key, value));
  }
  return merged;
}

function isAbortError(error: unknown) {
  return error instanceof DOMException && error.name === "AbortError";
}

export function onAuthExpired(handler: () => void) {
  if (typeof window === "undefined") return () => undefined;
  window.addEventListener(AUTH_EXPIRED_EVENT, handler);
  return () => window.removeEventListener(AUTH_EXPIRED_EVENT, handler);
}

export function setAuthRecoveryHandler(handler: (() => Promise<string | null>) | null) {
  authRecoveryHandler = handler;
}

function notifyAuthExpired() {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
}

function errorMessageFromPayload(payload: unknown, fallback: string) {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail?: unknown }).detail;
    if (Array.isArray(detail)) {
      const first = detail[0] as { msg?: unknown } | undefined;
      if (typeof first?.msg === "string") return first.msg;
    }
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  if (response.status === 204) {
    if (!response.ok) {
      throw new ApiRequestError(`${response.status} ${response.statusText}`.trim(), {
        status: response.status,
        transient: false
      });
    }
    return undefined as T;
  }
  const contentType = response.headers.get("content-type") ?? "";
  const expectsJson = contentType.toLowerCase().includes("application/json");
  const fallback = `${response.status} ${response.statusText}`.trim();

  if (!expectsJson) {
    await response.text().catch(() => "");
    throw new ApiRequestError(
      response.ok
        ? "Máy chủ trả về định dạng không hợp lệ. Vui lòng thử lại sau vài giây."
        : `API tạm thời không khả dụng (${fallback}). Vui lòng thử lại sau vài giây.`,
      { status: response.status, transient: response.ok || response.status >= 500 }
    );
  }

  const payload = await response.json().catch(() => {
    throw new ApiRequestError("Dữ liệu API không phải JSON hợp lệ. Vui lòng thử lại sau vài giây.", {
      status: response.status,
      transient: true
    });
  });

  if (!response.ok) {
    throw new ApiRequestError(errorMessageFromPayload(payload, fallback), {
      status: response.status,
      transient: response.status >= 500
    });
  }

  return payload as T;
}

async function requestJson<T>(url: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = mergedJsonHeaders(init.headers);
  const attempts = method === "GET" ? 2 : 1;
  const absoluteUrl = apiUrl(url);
  const dedupeKey = method === "GET" && !init.signal && !init.body ? absoluteUrl : "";

  if (dedupeKey) {
    const existing = inFlightGetRequests.get(dedupeKey);
    if (existing) return existing as Promise<T>;
  }

  const promise = (async () => {
    for (let attempt = 1; attempt <= attempts; attempt += 1) {
      try {
        const response = await fetch(absoluteUrl, { ...init, headers });
        return await parseJsonResponse<T>(response);
      } catch (error) {
        const canRetry =
          attempt < attempts &&
          !isAbortError(error) &&
          !(init.signal instanceof AbortSignal && init.signal.aborted) &&
          (!(error instanceof ApiRequestError) || error.transient);

        if (!canRetry) throw error;
        await sleep(GET_RETRY_DELAY_MS);
      }
    }

    throw new ApiRequestError("Không kết nối được API. Vui lòng thử lại sau vài giây.", { transient: true });
  })();

  if (dedupeKey) {
    inFlightGetRequests.set(dedupeKey, promise);
    void promise.finally(() => inFlightGetRequests.delete(dedupeKey)).catch(() => undefined);
  }

  return promise;
}

async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  return requestJson<T>(url, { signal });
}

async function getJsonWithBody<T>(url: string, payload: unknown, signal?: AbortSignal): Promise<T> {
  return requestJson<T>(url, { method: "POST", signal, body: JSON.stringify(payload) });
}

async function authJson<T>(url: string, token: string, init?: RequestInit): Promise<T> {
  try {
    return await requestJson<T>(url, { ...init, headers: authHeaders(token) });
  } catch (error) {
    if (error instanceof ApiRequestError && error.status === 401) {
      const refreshedToken = await authRecoveryHandler?.();
      if (refreshedToken && refreshedToken !== token) {
        return requestJson<T>(url, { ...init, headers: authHeaders(refreshedToken) });
      }
      notifyAuthExpired();
    }
    throw error;
  }
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

export function fetchUsdVndRate(signal?: AbortSignal) {
  return getJson<UsdVndRate>(`/api/v1/analytics/usd-vnd-rate`, signal);
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

export function fetchAgriInputProducts(signal?: AbortSignal) {
  return getJson<AgriInputProduct[]>("/api/v1/input-prices/products?category=fertilizer", signal);
}

export function fetchAgriInputLatest(options: { productSlug?: string; province?: string; signal?: AbortSignal } = {}) {
  const params = new URLSearchParams({ category: "fertilizer", limit: "300" });
  if (options.productSlug) params.set("product_slug", options.productSlug);
  if (options.province) params.set("province", options.province);
  return getJson<AgriInputPricePoint[]>(`/api/v1/input-prices/latest?${params.toString()}`, options.signal);
}

export function fetchAgriInputHistory(
  productSlug: string,
  options: { province?: string; brand?: string; months?: number; signal?: AbortSignal } = {}
) {
  const params = new URLSearchParams({ product_slug: productSlug, months: String(options.months ?? 12) });
  if (options.province) params.set("province", options.province);
  if (options.brand) params.set("brand", options.brand);
  return getJson<AgriInputPricePoint[]>(`/api/v1/input-prices/history?${params.toString()}`, options.signal);
}

export function fetchAgriInputForecast(
  productSlug: string,
  options: { province?: string; brand?: string; days?: number; signal?: AbortSignal } = {}
) {
  const params = new URLSearchParams({ product_slug: productSlug, days: String(options.days ?? 30) });
  if (options.province) params.set("province", options.province);
  if (options.brand) params.set("brand", options.brand);
  return getJson<AgriInputForecast>(`/api/v1/input-prices/forecast?${params.toString()}`, options.signal);
}

export function fetchWorldFertilizerCommodities(signal?: AbortSignal) {
  return getJson<WorldFertilizerCommodityInfo[]>("/api/v1/advisory/world-fertilizer/commodities", signal);
}

export function fetchWorldFertilizerHistory(
  commodity: WorldFertilizerCommodity,
  options: { days?: number; signal?: AbortSignal } = {}
) {
  const params = new URLSearchParams({ commodity, days: String(options.days ?? 365) });
  return getJson<WorldFertilizerHistoryPoint[]>(`/api/v1/advisory/world-fertilizer/history?${params.toString()}`, options.signal);
}

export function fetchWorldFertilizerForecast(
  commodity: WorldFertilizerCommodity,
  options: { horizonDays?: number; signal?: AbortSignal } = {}
) {
  const params = new URLSearchParams({ commodity, horizon_days: String(options.horizonDays ?? 30) });
  return getJson<WorldFertilizerForecast>(`/api/v1/advisory/world-fertilizer/forecast?${params.toString()}`, options.signal);
}

export function calculateRoi(token: string, payload: RoiCalculateRequest, signal?: AbortSignal) {
  return authJson<RoiCalculateResponse>("/api/v1/advisory/roi/calculate", token, {
    method: "POST",
    signal,
    body: JSON.stringify(payload)
  });
}

export type SellingTimeRequest = {
  crop: CropType;
  region_id?: number | null;
  variety_id?: number | null;
  quantity_kg: number;
  storage_cost_vnd_per_kg_per_day?: number;
  earliest_sale_date?: string | null;
};

export type SellingTimeWindow = {
  date: string;
  forecast_price_vnd_per_kg: number;
  net_revenue_vnd: number;
  uplift_pct_vs_today: number;
  storage_cost_vnd: number;
};

export type SellingTimeResponse = {
  crop: CropType;
  crop_label_vi: string;
  model_kind: string;
  best_window: SellingTimeWindow;
  top_5_windows: SellingTimeWindow[];
  confidence_score: number;
  rationale_vi: string;
};

export function postSellingTime(token: string, payload: SellingTimeRequest, signal?: AbortSignal) {
  return authJson<SellingTimeResponse>("/api/v1/advisory/selling-time", token, {
    method: "POST",
    signal,
    body: JSON.stringify(payload)
  });
}

export type ArbitrageResponse = {
  items: {
    crop: CropType;
    crop_label_vi: string;
    from_region: string;
    to_region: string;
    from_province: string | null;
    to_province: string | null;
    source_price_vnd_per_kg: number;
    target_price_vnd_per_kg: number;
    estimated_distance_km: number;
    transport_cost_vnd_per_kg: number;
    net_spread_vnd_per_kg: number;
    net_spread_pct: number;
  }[];
  assumption_vi: string;
};

export function fetchArbitrage(token: string, options: { crop?: CropType | ""; minNetSpreadPct?: number; maxDistanceKm?: number; signal?: AbortSignal } = {}) {
  const params = new URLSearchParams({
    min_net_spread_pct: String(options.minNetSpreadPct ?? 3),
    max_distance_km: String(options.maxDistanceKm ?? 700)
  });
  if (options.crop) params.set("crop_type", options.crop);
  return authJson<ArbitrageResponse>(`/api/v1/advisory/arbitrage?${params.toString()}`, token, { signal: options.signal });
}

export type CrossCommodityResponse = {
  region_id: number;
  region_name: string;
  province: string | null;
  items: {
    crop: CropType;
    crop_label_vi: string;
    suitability_score: number;
    reference_price_vnd_per_kg: number;
    yield_t_ha: number;
    estimated_profit_vnd: number;
    roi_score: number;
  }[];
  intercropping_vi: string[];
  disclaimer_vi: string;
};

export function postCrossCommodity(token: string, payload: { region_id: number; current_crop?: CropType | null; area_hectares: number }, signal?: AbortSignal) {
  return authJson<CrossCommodityResponse>("/api/v1/advisory/cross-commodity", token, {
    method: "POST",
    signal,
    body: JSON.stringify(payload)
  });
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

export function login(email: string, password: string, signal?: AbortSignal) {
  return getAuth("/api/v1/auth/login", { email, password }, signal);
}

export function register(email: string, password: string, displayName?: string, signal?: AbortSignal) {
  return getAuth("/api/v1/auth/register", { email, password, display_name: displayName }, signal);
}

export function refreshAuth(refreshToken: string, signal?: AbortSignal) {
  return requestJson<AuthSession>("/api/v1/auth/refresh", {
    method: "POST",
    signal,
    body: JSON.stringify({ refresh_token: refreshToken })
  });
}

export function logout(token: string, refreshToken?: string) {
  return authJson<void>("/api/v1/auth/logout", token, {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken })
  });
}

function getAuth(url: string, payload: Record<string, string | undefined>, signal?: AbortSignal) {
  return requestJson<AuthSession>(url, {
    method: "POST",
    signal,
    body: JSON.stringify(payload)
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

export function runPlatformJob(token: string, job: "scrape" | "news" | "input-prices" | "world-fertilizer" | "data-quality" | "retrain" | "weather") {
  return authJson<Record<string, unknown>>(`/api/v1/platform/jobs/${job}`, token, { method: "POST" });
}

export function fetchNews(signal?: AbortSignal, language: "vi" | "en" = "vi") {
  const limit = language === "en" ? 120 : 2000;
  return getJson<NewsArticle[]>(`/api/v1/content/news?limit=${limit}&lang=${language}`, signal);
}

export function fetchNewsDetail(slug: string, signal?: AbortSignal, language: "vi" | "en" = "vi") {
  return getJson<NewsArticle>(`/api/v1/content/news/${encodeURIComponent(slug)}?lang=${language}`, signal);
}

export function scrapeNews(token: string) {
  return authJson<Record<string, unknown>>("/api/v1/content/news/scrape", token, { method: "POST" });
}

export function fetchGuides(crop?: CropType, limit = 120, signal?: AbortSignal, language: "vi" | "en" = "vi") {
  const cropParam = crop ? `?crop=${crop}&limit=${limit}&lang=${language}` : `?limit=${limit}&lang=${language}`;
  return getJson<GuidePost[]>(`/api/v1/content/guides${cropParam}`, signal);
}

export function fetchGuideDetail(slug: string, signal?: AbortSignal, language: "vi" | "en" = "vi") {
  return getJson<GuidePost>(`/api/v1/content/guides/${encodeURIComponent(slug)}?lang=${language}`, signal);
}

export function subscribeNewsletter(email: string) {
  return requestJson<Subscriber>("/api/v1/content/subscribers", {
    method: "POST",
    body: JSON.stringify({ email, source: "footer" })
  });
}

export function reportLocalPrice(payload: UserPriceReportPayload) {
  return requestJson<UserPriceReport>("/api/v1/content/price-reports", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function fetchFertilizerCrops(signal?: AbortSignal) {
  return getJson<{ crop: FertilizerCrop; name_vi: string; calibration_status: string; confidence: string; valid_yield_range_t_ha: [number, number]; valid_textures: SoilTexture[] }[]>(
    "/api/v1/fertilizer/crops",
    signal
  );
}

export function recommendFertilizer(payload: FertilizerRequest, token: string, signal?: AbortSignal) {
  return authJson<FertilizerRecommendation>("/api/v1/fertilizer/recommend", token, {
    method: "POST",
    signal,
    body: JSON.stringify(payload)
  });
}

export function submitYieldFeedback(sessionCode: string, payload: YieldFeedbackPayload, token: string) {
  return authJson<YieldFeedbackResponse>(`/api/v1/sessions/${encodeURIComponent(sessionCode)}/feedback`, token, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}
