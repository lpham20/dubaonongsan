import { memo } from "react";
import { useLanguage } from "../contexts/LanguageContext";
import type { PricePoint } from "../lib/api";

type Props = {
  points: PricePoint[];
};

type TickerItem = {
  label: string;
  value: string;
  change: string;
  tone: "up" | "down";
};

function TickerTapeComponent({ points }: Props) {
  const { language } = useLanguage();
  const isEnglish = language === "en";
  const items = buildForecastTicker(points, language);
  const repeated = [...items, ...items];

  return (
    <div className="home-price-ticker forecast-price-ticker" aria-label={isEnglish ? "Live agricultural price ticker" : "Dải băng giá nông sản"}>
      <div className="home-price-ticker-label">
        {isEnglish ? "Live prices" : "Giá trực tuyến"}
      </div>
      <div className="home-price-track">
        <div className="home-price-content">
          {repeated.map((item, index) => (
            <span key={`${item.label}-${index}`}>
              <strong>{item.label}</strong>
              <b className="num">{item.value}</b>
              <em className={item.tone}>{item.change}</em>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

export const TickerTape = memo(TickerTapeComponent);

function buildForecastTicker(points: PricePoint[], language: "vi" | "en"): TickerItem[] {
  const seen = new Set<string>();
  const items: TickerItem[] = [];
  const locale = language === "en" ? "en-US" : "vi-VN";
  const unit = language === "en" ? "VND/kg" : "đ/kg";

  for (const point of points) {
    if (!point.max_price_vnd) continue;

    const label = formatLabel(point, language);
    const key = label.toLocaleLowerCase("vi-VN");
    if (seen.has(key)) continue;
    seen.add(key);

    const series = points.filter((item) => formatLabel(item, language) === label && item.max_price_vnd);
    const latest = series[0]?.max_price_vnd ?? point.max_price_vnd;
    const previous = series[1]?.max_price_vnd;
    const change = previous ? ((latest - previous) / previous) * 100 : 0;

    items.push({
      label,
      value: `${Math.round(latest).toLocaleString(locale)} ${unit}`,
      change: `${change >= 0 ? "+" : ""}${change.toLocaleString(locale, { maximumFractionDigits: 1 })}%`,
      tone: change >= 0 ? "up" : "down"
    });

    if (items.length >= 4) break;
  }

  return items.length
    ? items
    : language === "en"
      ? [
          { label: "Robusta coffee", value: "Updating", change: "+0.0%", tone: "up" },
          { label: "Ri6 durian", value: "Updating", change: "+0.0%", tone: "up" },
          { label: "Urea fertilizer", value: "Updating", change: "+0.0%", tone: "up" },
          { label: "Export FX rate", value: "Updating", change: "+0.0%", tone: "up" }
        ]
      : [
          { label: "Cà phê Robusta", value: "Đang cập nhật", change: "+0,0%", tone: "up" },
          { label: "Sầu riêng Ri6", value: "Đang cập nhật", change: "+0,0%", tone: "up" },
          { label: "Phân bón urê", value: "Đang cập nhật", change: "+0,0%", tone: "up" },
          { label: "Tỷ giá xuất khẩu", value: "Đang cập nhật", change: "+0,0%", tone: "up" }
        ];
}

function formatLabel(point: PricePoint, language: "vi" | "en" = "vi") {
  const grade = point.quality_grade ? ` ${point.quality_grade}` : "";
  const market = point.province ?? point.region ?? "";
  return translateTickerLabel(`${point.variety}${grade}${market ? ` ${market}` : ""}`.trim(), language);
}

function translateTickerLabel(value: string, language: "vi" | "en") {
  if (language !== "en") return value;
  return value
    .replace(/Cà phê/gi, "Coffee")
    .replace(/Hồ tiêu/gi, "Pepper")
    .replace(/Tiêu đen/gi, "Black pepper")
    .replace(/Sầu riêng/gi, "Durian")
    .replace(/Lúa/gi, "Rice")
    .replace(/Phân bón urê|Urê|Urea hạt đục/gi, "Urea")
    .replace(/\bĐắk Lắk\b/g, "Dak Lak")
    .replace(/\bĐắk Nông\b/g, "Dak Nong")
    .replace(/\bLâm Đồng\b/g, "Lam Dong")
    .replace(/\bBà Rịa - Vũng Tàu\b/g, "Ba Ria - Vung Tau");
}
