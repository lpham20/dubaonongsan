import { useEffect, useState } from "react";
import { useLanguage } from "../contexts/LanguageContext";
import {
  ANALYTICS_CONSENT_STORAGE_KEY,
  trackPageView
} from "../lib/analytics";

type Consent = {
  analytics: boolean;
  decided: boolean;
  decided_at?: string;
};

type AnalyticsWindow = Window & {
  DUBAONONGSAN_LOAD_ANALYTICS?: () => void;
  gtag?: (...args: unknown[]) => void;
};

const EMPTY_CONSENT: Consent = { analytics: false, decided: false };

const COPY = {
  vi: {
    aria: "Tùy chọn cookie phân tích",
    message: "Chúng tôi chỉ dùng cookie phân tích khi bạn đồng ý, nhằm hiểu lượt truy cập và cải thiện dịch vụ.",
    accept: "Đồng ý",
    decline: "Từ chối"
  },
  en: {
    aria: "Analytics cookie options",
    message: "We only use analytics cookies with your consent to understand visits and improve the service.",
    accept: "Accept",
    decline: "Decline"
  }
} as const;

function loadConsent(): Consent {
  try {
    const raw = window.localStorage.getItem(ANALYTICS_CONSENT_STORAGE_KEY);
    if (!raw) return EMPTY_CONSENT;
    const saved = JSON.parse(raw) as Partial<Consent>;
    return {
      analytics: saved.analytics === true,
      decided: saved.decided === true,
      decided_at: typeof saved.decided_at === "string" ? saved.decided_at : undefined
    };
  } catch {
    return EMPTY_CONSENT;
  }
}

function saveConsent(consent: Consent) {
  try {
    window.localStorage.setItem(ANALYTICS_CONSENT_STORAGE_KEY, JSON.stringify(consent));
  } catch {
    // Private browsing can reject storage. The current session still receives the consent signal.
  }
}

function updateConsentSignal(analytics: boolean) {
  const browser = window as AnalyticsWindow;
  browser.gtag?.("consent", "update", {
    analytics_storage: analytics ? "granted" : "denied",
    ad_storage: "denied",
    ad_user_data: "denied",
    ad_personalization: "denied"
  });
  if (analytics) browser.DUBAONONGSAN_LOAD_ANALYTICS?.();
}

export function CookieConsentBanner() {
  const { language } = useLanguage();
  const [consent, setConsent] = useState<Consent>(loadConsent);

  useEffect(() => {
    if (!consent.decided) return;
    updateConsentSignal(consent.analytics);
  }, [consent.analytics, consent.decided]);

  if (consent.decided) return null;

  const copy = COPY[language];

  function decide(analytics: boolean) {
    const next: Consent = {
      analytics,
      decided: true,
      decided_at: new Date().toISOString()
    };
    saveConsent(next);
    setConsent(next);
    updateConsentSignal(analytics);
    if (analytics) {
      trackPageView(`${window.location.pathname}${window.location.search}`, document.title);
    }
  }

  return (
    <div className="cookie-consent-banner" role="dialog" aria-label={copy.aria} aria-live="polite">
      <div className="cookie-consent-content">
        <p>{copy.message}</p>
        <div className="cookie-consent-actions">
          <button type="button" className="cookie-consent-decline" onClick={() => decide(false)}>
            {copy.decline}
          </button>
          <button type="button" className="cookie-consent-accept" onClick={() => decide(true)}>
            {copy.accept}
          </button>
        </div>
      </div>
    </div>
  );
}
