import { memo } from "react";
import { Activity, BarChart3, Gauge, LineChart, TrendingDown, TrendingUp } from "./icons";
import type { PricePoint, TradingSignal } from "../lib/api";
import { useLanguage, type AppLanguage } from "../contexts/LanguageContext";

type Props = {
  points: PricePoint[];
  signals: TradingSignal[];
};

const money = (value: number, language: AppLanguage = "vi") => `${Math.round(value).toLocaleString(language === "en" ? "en-US" : "vi-VN")} VND/kg`;

function TechnicalPanelComponent({ points, signals }: Props) {
  const { language } = useLanguage();
  const prices = points
    .filter((point) => typeof point.max_price_vnd === "number")
    .map((point) => Number(point.max_price_vnd));
  const latest = prices.at(-1) ?? 0;
  const sma7 = average(prices.slice(-7));
  const sma30 = average(prices.slice(-30));
  const volatility = volatilityPct(prices.slice(-30));
  const support = nearestSupport(prices, latest);
  const resistance = nearestResistance(prices, latest);
  const trendScore = scoreTrend(latest, sma7, sma30, support, resistance, volatility, signals.length);
  const signalLabel = trendScore >= 2
    ? language === "en" ? "Can hold part of stock" : "Có thể giữ hàng"
    : trendScore <= -2
      ? language === "en" ? "Consider selling to reduce risk" : "Nên bán giảm rủi ro"
      : language === "en" ? "Watch for confirmation" : "Theo dõi thêm";
  const SignalIcon = trendScore >= 2 ? TrendingUp : trendScore <= -2 ? TrendingDown : Activity;

  return (
    <section className="terminal-technical technical-panel">
      <div className="technical-summary">
        <span>
          <Gauge size={17} />
          {language === "en" ? "Price signal" : "Tín hiệu giá"}
        </span>
        <h2>{signalLabel}</h2>
        <p>
          {language === "en"
            ? "The system compares the current price with the 7-day level, 30-day level, nearest support area and likely resistance area. If price is near resistance without strong buying, selling part of the stock may reduce risk. If price holds above support and demand is still steady, holding part of the volume can be reasonable."
            : "Hệ thống so sánh giá hiện tại với mặt bằng 7 ngày, 30 ngày, vùng giá mua đỡ gần nhất và vùng giá dễ bị chặn lại. Nếu giá tiến sát vùng trên nhưng lực mua không mạnh, nên cân nhắc bán một phần. Nếu giá giữ trên vùng dưới và nhu cầu thu mua còn đều, có thể giữ lại một phần sản lượng thay vì bán vội."}
        </p>
      </div>

      <div className="technical-cards">
        <TechnicalCard icon={SignalIcon} label={language === "en" ? "Summary" : "Tổng hợp"} value={signalLabel} detail={`${signals.length} ${language === "en" ? "open alerts" : "cảnh báo đang mở"}`} />
        <TechnicalCard icon={LineChart} label={language === "en" ? "7-day level" : "Mặt bằng 7 ngày"} value={money(sma7 || latest, language)} detail={latest >= sma7 ? (language === "en" ? "Price is above the recent level" : "Giá cao hơn gần đây") : (language === "en" ? "Price is below the recent level" : "Giá thấp hơn gần đây")} />
        <TechnicalCard icon={BarChart3} label={language === "en" ? "30-day level" : "Mặt bằng 30 ngày"} value={money(sma30 || latest, language)} detail={latest >= sma30 ? (language === "en" ? "The price base is still firm" : "Nền giá còn tốt") : (language === "en" ? "The price base is weakening" : "Nền giá đang yếu")} />
        <TechnicalCard icon={Activity} label={language === "en" ? "30-day volatility" : "Dao động 30 ngày"} value={`${volatility.toFixed(2)}%`} detail={language === "en" ? "Movement around the average price" : "Mức lên xuống quanh giá trung bình"} />
      </div>

      <div className="technical-levels">
        <article>
          <span>{language === "en" ? "Nearest support area" : "Vùng mua đỡ gần"}</span>
          <strong>{money(support || latest, language)}</strong>
        </article>
        <article>
          <span>{language === "en" ? "Current price" : "Giá hiện tại"}</span>
          <strong>{money(latest, language)}</strong>
        </article>
        <article>
          <span>{language === "en" ? "Likely resistance area" : "Vùng giá dễ chững"}</span>
          <strong>{money(resistance || latest, language)}</strong>
        </article>
      </div>
    </section>
  );
}

export const TechnicalPanel = memo(TechnicalPanelComponent);

function TechnicalCard({
  icon: Icon,
  label,
  value,
  detail
}: {
  icon: typeof Activity;
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <article>
      <Icon size={18} />
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function average(values: number[]) {
  return values.length ? values.reduce((total, value) => total + value, 0) / values.length : 0;
}

function volatilityPct(values: number[]) {
  if (values.length < 2) return 0;
  const mean = average(values);
  if (!mean) return 0;
  const variance = values.reduce((total, value) => total + (value - mean) ** 2, 0) / values.length;
  return (Math.sqrt(variance) / mean) * 100;
}

function uniqueSorted(prices: number[]) {
  return Array.from(new Set(prices.filter((price) => Number.isFinite(price)))).sort((a, b) => a - b);
}

function nearestSupport(prices: number[], latest: number) {
  const values = uniqueSorted(prices.slice(-45));
  const below = values.filter((price) => price < latest);
  if (below.length) return below.at(-1) ?? latest;
  const volatilityBuffer = Math.max(latest * 0.015, 1000);
  return Math.max(0, latest - volatilityBuffer);
}

function nearestResistance(prices: number[], latest: number) {
  const values = uniqueSorted(prices.slice(-45));
  const above = values.filter((price) => price > latest);
  if (above.length) return above[0];
  const volatilityBuffer = Math.max(latest * 0.018, 1000);
  return latest + volatilityBuffer;
}

function scoreTrend(
  latest: number,
  sma7: number,
  sma30: number,
  support: number,
  resistance: number,
  volatility: number,
  signalCount: number
) {
  let score = 0;
  if (latest >= sma7) score += 1;
  else score -= 1;
  if (sma7 >= sma30) score += 1;
  else score -= 1;
  const range = resistance - support;
  if (range > 0) {
    const position = (latest - support) / range;
    if (position > 0.85) score -= 1;
    if (position < 0.25) score += 1;
  }
  if (volatility > 8) score -= 1;
  if (signalCount > 0) score -= 1;
  return score;
}
