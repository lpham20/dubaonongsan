import { memo, useEffect, useMemo, useState } from "react";
import { useLanguage } from "../contexts/LanguageContext";
import {
  fetchTickerPrices,
  fetchWorldFertilizerForecast,
  type CropType,
  type PricePoint,
  type WorldFertilizerForecast
} from "../lib/api";

type TickerItem = {
  label: string;
  value: string;
  change: string;
  tone: "up" | "down";
};

const EMPTY_TICKER_DATA: Record<CropType, PricePoint[]> = {
  ca_phe: [],
  sau_rieng: [],
  ho_tieu: [],
  lua: []
};

const FALLBACK_TICKER: Record<"vi" | "en", TickerItem[]> = {
  vi: [
    { label: "Cà phê Robusta", value: "Đang cập nhật", change: "+0,0%", tone: "up" },
    { label: "Sầu riêng Ri6", value: "Đang cập nhật", change: "+0,0%", tone: "up" },
    { label: "Hồ tiêu đen", value: "Đang cập nhật", change: "+0,0%", tone: "up" },
    { label: "Lúa OM 5451", value: "Đang cập nhật", change: "+0,0%", tone: "up" },
    { label: "Urê thế giới", value: "Đang cập nhật", change: "+0,0%", tone: "up" }
  ],
  en: [
    { label: "Robusta coffee", value: "Updating", change: "+0.0%", tone: "up" },
    { label: "Ri6 durian", value: "Updating", change: "+0.0%", tone: "up" },
    { label: "Black pepper", value: "Updating", change: "+0.0%", tone: "up" },
    { label: "OM 5451 rice", value: "Updating", change: "+0.0%", tone: "up" },
    { label: "World urea", value: "Updating", change: "+0.0%", tone: "up" }
  ]
};

function LivePriceTickerComponent() {
  const { language } = useLanguage();
  const [tickerData, setTickerData] = useState<Record<CropType, PricePoint[]>>(EMPTY_TICKER_DATA);
  const [ureaForecast, setUreaForecast] = useState<WorldFertilizerForecast | null>(null);
  const items = useMemo(() => buildLiveTicker(tickerData, language, ureaForecast), [language, tickerData, ureaForecast]);
  const repeated = [...items, ...items, ...items];

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
        if (active) setTickerData(EMPTY_TICKER_DATA);
      });

    fetchWorldFertilizerForecast("urea", { horizonDays: 7 })
      .then((forecast) => {
        if (active) setUreaForecast(forecast);
      })
      .catch(() => {
        if (active) setUreaForecast(null);
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="p-strip paper" aria-label={language === "en" ? "Today agricultural price ticker" : "Dải băng giá nông sản hôm nay"}>
      <div className="lab">{language === "en" ? "Today prices" : "Giá hôm nay"}</div>
      <div className="items">
        {repeated.map((item, index) => (
          <div className="it" key={`${item.label}-${index}`}>
            <span className="s">{item.label}</span>
            <span className="pr">
              <b className="num">{item.value}</b>
              <em className={item.tone === "up" ? "pos" : "neg"}>{item.change}</em>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export const LivePriceTicker = memo(LivePriceTickerComponent);

function buildLiveTicker(data: Record<CropType, PricePoint[]>, language: "vi" | "en", ureaForecast: WorldFertilizerForecast | null): TickerItem[] {
  const fallback = FALLBACK_TICKER[language];
  const coffee = pointToTicker(data.ca_phe, fallback[0].label, ["robusta", "culi", "arabica"], language);
  const durian = pointToTicker(data.sau_rieng, fallback[1].label, ["ri6", "dona", "thai", "musang", "black thorn"], language);
  const pepper = pointToTicker(data.ho_tieu, fallback[2].label, ["tieu den", "tieu trang", "tieu do"], language);
  const rice = pointToTicker(data.lua, fallback[3].label, ["om", "dai thom", "nang hoa", "jasmine"], language);
  const urea = worldUreaTicker(ureaForecast, language) ?? fallback[4];
  return [
    coffee ?? fallback[0],
    durian ?? fallback[1],
    pepper ?? fallback[2],
    rice ?? fallback[3],
    urea
  ];
}

function worldUreaTicker(forecast: WorldFertilizerForecast | null, language: "vi" | "en"): TickerItem | null {
  const price = forecast?.base_price_usd_per_tonne;
  if (!price) return null;
  const change = forecast?.forecast_daily[0]?.daily_pct_change ?? 0;
  const locale = language === "en" ? "en-US" : "vi-VN";
  const unit = language === "en" ? "USD/tonne" : "USD/tấn";
  return {
    label: language === "en" ? "World urea" : "Urê thế giới",
    value: `${price.toLocaleString(locale, { maximumFractionDigits: 0 })} ${unit}`,
    change: formatTickerChange(change, language),
    tone: change >= 0 ? "up" : "down"
  };
}

function pointToTicker(points: PricePoint[], fallbackLabel: string, keywords: string[], language: "vi" | "en") {
  const selected = selectTickerSeries(points, keywords);
  if (!selected.length) return null;
  const latest = selected[0];
  const change = computeTickerChange(selected);
  return {
    label: translateTickerLabel(latest.variety || fallbackLabel, language),
    value: formatTickerPrice(pointPrice(latest), language),
    change: formatTickerChange(change, language),
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

function formatTickerPrice(value: number, language: "vi" | "en") {
  const locale = language === "en" ? "en-US" : "vi-VN";
  const unit = language === "en" ? "VND/kg" : "đ/kg";
  return `${Math.round(value).toLocaleString(locale)} ${unit}`;
}

function formatTickerChange(value: number, language: "vi" | "en") {
  const locale = language === "en" ? "en-US" : "vi-VN";
  const zero = language === "en" ? "0.0%" : "0,0%";
  if (!Number.isFinite(value) || Math.abs(value) < 0.05) return zero;
  return `${value > 0 ? "+" : ""}${value.toLocaleString(locale, { maximumFractionDigits: 1 })}%`;
}

function translateTickerLabel(value: string, language: "vi" | "en") {
  if (language !== "en") return value;
  return value
    .replace(/Cà phê/gi, "Coffee")
    .replace(/Hồ tiêu/gi, "Pepper")
    .replace(/Tiêu đen/gi, "Black pepper")
    .replace(/Tiêu trắng/gi, "White pepper")
    .replace(/Sầu riêng/gi, "Durian")
    .replace(/Lúa/gi, "Rice")
    .replace(/Urea hạt đục|Urê thế giới|Urê|Urea/gi, "Urea")
    .replace(/loại\s*(\d+)/gi, "grade $1")
    .replace(/\bĐắk Lắk\b/g, "Dak Lak")
    .replace(/\bĐắk Nông\b/g, "Dak Nong")
    .replace(/\bLâm Đồng\b/g, "Lam Dong")
    .replace(/\bBà Rịa - Vũng Tàu\b/g, "Ba Ria - Vung Tau");
}

function normalize(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase();
}
