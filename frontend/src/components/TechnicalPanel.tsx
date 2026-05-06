import { memo } from "react";
import { Activity, BarChart3, Gauge, LineChart, TrendingDown, TrendingUp } from "./icons";
import type { PricePoint, TradingSignal } from "../lib/api";

type Props = {
  points: PricePoint[];
  signals: TradingSignal[];
};

const money = (value: number) => `${Math.round(value).toLocaleString("vi-VN")} VND/kg`;

function TechnicalPanelComponent({ points, signals }: Props) {
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
  const signalLabel = trendScore >= 2 ? "Có thể giữ hàng" : trendScore <= -2 ? "Nên bán giảm rủi ro" : "Theo dõi thêm";
  const SignalIcon = trendScore >= 2 ? TrendingUp : trendScore <= -2 ? TrendingDown : Activity;

  return (
    <section className="technical-panel">
      <div className="technical-summary">
        <span>
          <Gauge size={17} />
          Tín hiệu giá
        </span>
        <h2>{signalLabel}</h2>
        <p>
          Hệ thống so sánh giá hiện tại với mặt bằng 7 ngày, 30 ngày, vùng giá mua đỡ gần nhất và vùng giá dễ bị chặn lại.
          Nếu giá tiến sát vùng trên nhưng lực mua không mạnh, nên cân nhắc bán một phần. Nếu giá giữ trên vùng dưới và nhu cầu thu mua còn đều,
          có thể giữ lại một phần sản lượng thay vì bán vội.
        </p>
      </div>

      <div className="technical-cards">
        <TechnicalCard icon={SignalIcon} label="Tổng hợp" value={signalLabel} detail={`${signals.length} cảnh báo đang mở`} />
        <TechnicalCard icon={LineChart} label="Mặt bằng 7 ngày" value={money(sma7 || latest)} detail={latest >= sma7 ? "Giá cao hơn gần đây" : "Giá thấp hơn gần đây"} />
        <TechnicalCard icon={BarChart3} label="Mặt bằng 30 ngày" value={money(sma30 || latest)} detail={latest >= sma30 ? "Nền giá còn tốt" : "Nền giá đang yếu"} />
        <TechnicalCard icon={Activity} label="Dao động 30 ngày" value={`${volatility.toFixed(2)}%`} detail="Mức lên xuống quanh giá trung bình" />
      </div>

      <div className="technical-levels">
        <article>
          <span>Vùng mua đỡ gần</span>
          <strong>{money(support || latest)}</strong>
        </article>
        <article>
          <span>Giá hiện tại</span>
          <strong>{money(latest)}</strong>
        </article>
        <article>
          <span>Vùng giá dễ chững</span>
          <strong>{money(resistance || latest)}</strong>
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
