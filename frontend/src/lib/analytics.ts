export type AnalyticsEventName =
  | "signup_completed"
  | "login_completed"
  | "logout"
  | "fertilizer_recommend_requested"
  | "fertilizer_recommend_received"
  | "roi_calculate_submitted"
  | "roi_calculate_received"
  | "watchlist_item_added"
  | "watchlist_item_removed"
  | "news_article_viewed"
  | "guide_post_viewed"
  | "forecast_chart_viewed"
  | "world_fertilizer_viewed"
  | "language_changed"
  | "search_query_submitted"
  | "exception";

export type AnalyticsEventParams = Record<string, string | number | boolean | undefined | null>;

export const ANALYTICS_CONSENT_STORAGE_KEY = "marketai.consent.v1";

type AnalyticsWindow = Window & {
  DUBAONONGSAN_GA_ID?: string;
  DUBAONONGSAN_LOAD_ANALYTICS?: () => void;
  gtag?: (...args: unknown[]) => void;
};

const BLOCKED_KEY_PARTS = [
  "authorization",
  "display_name",
  "email",
  "full_name",
  "ip",
  "password",
  "phone",
  "secret",
  "token"
];

function analyticsWindow(): AnalyticsWindow | null {
  return typeof window === "undefined" ? null : (window as AnalyticsWindow);
}

function normalizeKey(key: string) {
  return key.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_");
}

function isBlockedKey(key: string) {
  const normalized = normalizeKey(key);
  return BLOCKED_KEY_PARTS.some((part) => normalized.includes(part));
}

export function hasAnalyticsConsent(): boolean {
  if (typeof window === "undefined") return false;
  try {
    const raw = window.localStorage.getItem(ANALYTICS_CONSENT_STORAGE_KEY);
    if (!raw) return false;
    const consent = JSON.parse(raw) as { analytics?: unknown; decided?: unknown };
    return consent.analytics === true && consent.decided === true;
  } catch {
    return false;
  }
}

/**
 * Send a GA4 event only after explicit analytics consent.
 * PII-like parameter names are removed and long string values are truncated.
 */
export function trackEvent(name: AnalyticsEventName, params: AnalyticsEventParams = {}): void {
  const browser = analyticsWindow();
  if (!browser?.gtag || !browser.DUBAONONGSAN_GA_ID || !hasAnalyticsConsent()) return;

  const safeParams: AnalyticsEventParams = {};
  for (const [key, value] of Object.entries(params)) {
    if (isBlockedKey(key) || value === undefined || value === null) continue;
    safeParams[key] = typeof value === "string" ? value.slice(0, 100) : value;
  }

  try {
    browser.gtag("event", name, safeParams);
  } catch {
    // Analytics must never break a user workflow.
  }
}

/**
 * Send a manual page view for SPA navigation.
 */
export function trackPageView(path: string, title: string): void {
  const browser = analyticsWindow();
  if (!browser?.gtag || !browser.DUBAONONGSAN_GA_ID || !hasAnalyticsConsent()) return;
  try {
    browser.gtag("config", browser.DUBAONONGSAN_GA_ID, {
      page_path: path.slice(0, 300),
      page_title: title.slice(0, 100)
    });
  } catch {
    // Analytics must never break navigation.
  }
}
