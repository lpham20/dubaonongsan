import { useEffect, useMemo, useState } from "react";
import { Activity, BarChart3, LineChart, RefreshCw, TrendingDown, TrendingUp } from "./icons";
import {
  fetchWorldFertilizerCommodities,
  fetchWorldFertilizerForecast,
  type WorldFertilizerCommodity,
  type WorldFertilizerCommodityInfo,
  type WorldFertilizerForecast,
  type WorldFertilizerForecastPoint,
  type WorldFertilizerWeeklyPoint
} from "../lib/api";

const FALLBACK_COMMODITIES: WorldFertilizerCommodityInfo[] = [
  {
    commodity_slug: "urea",
    name_vi: "Urê",
    name_en: "Urea",
    quote_type: "FOB Middle East",
    driver_note_vi: "Urê thường nhạy với khí gas, than và nguồn cung Trung Quốc/Trung Đông."
  },
  {
    commodity_slug: "dap",
    name_vi: "DAP",
    name_en: "Diammonium phosphate",
    quote_type: "FOB US Gulf",
    driver_note_vi: "DAP chịu ảnh hưởng bởi phosphate rock, lưu huỳnh và chi phí logistics."
  },
  {
    commodity_slug: "kali_mop",
    name_vi: "Kali (MOP)",
    name_en: "Potassium chloride",
    quote_type: "Brazil CFR / FOB Vancouver",
    driver_note_vi: "Kali Việt Nam phụ thuộc nhiều vào nhập khẩu."
  }
];

function formatUsd(value: number | null | undefined) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "Đang cập nhật";
  return `${value.toLocaleString("vi-VN", { maximumFractionDigits: 2 })} USD/tấn`;
}

function formatDate(value: string | null | undefined) {
  if (!value) return "Đang cập nhật";
  return new Intl.DateTimeFormat("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" }).format(new Date(value));
}

function formatPct(value: number | null | undefined) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "0,00%";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toLocaleString("vi-VN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
}

function trendClass(value: number) {
  if (value > 0.5) return "up";
  if (value < -0.5) return "down";
  return "flat";
}

function WorldForecastChart({ points }: { points: WorldFertilizerForecastPoint[] }) {
  const width = 920;
  const height = 260;
  const padding = { top: 24, right: 24, bottom: 36, left: 70 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const values = points
    .flatMap((point) => [point.price_usd_per_tonne, point.price_low_usd_per_tonne, point.price_high_usd_per_tonne])
    .filter((value) => Number.isFinite(value));
  const minValue = values.length ? Math.min(...values) * 0.97 : 0;
  const maxValue = values.length ? Math.max(...values) * 1.03 : 1;
  const span = Math.max(1, maxValue - minValue);

  function x(index: number) {
    if (points.length <= 1) return padding.left;
    return padding.left + (index / (points.length - 1)) * plotWidth;
  }

  function y(value: number) {
    return padding.top + (1 - (value - minValue) / span) * plotHeight;
  }

  if (!points.length) {
    return <div className="world-forecast-empty">Chưa có dữ liệu dự báo cho lựa chọn này.</div>;
  }

  const line = points.map((point, index) => `${x(index).toFixed(2)},${y(point.price_usd_per_tonne).toFixed(2)}`).join(" ");
  const band = [
    ...points.map((point, index) => `${index === 0 ? "M" : "L"} ${x(index).toFixed(2)} ${y(point.price_high_usd_per_tonne).toFixed(2)}`),
    ...points
      .slice()
      .reverse()
      .map((point, reverseIndex) => {
        const index = points.length - reverseIndex - 1;
        return `L ${x(index).toFixed(2)} ${y(point.price_low_usd_per_tonne).toFixed(2)}`;
      }),
    "Z"
  ].join(" ");
  const gridValues = [0, 0.25, 0.5, 0.75, 1].map((ratio) => minValue + span * ratio);

  return (
    <svg className="world-forecast-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Biểu đồ xu hướng giá phân bón thế giới">
      {gridValues.map((value) => (
        <g key={value}>
          <line x1={padding.left} x2={width - padding.right} y1={y(value)} y2={y(value)} />
          <text x={padding.left - 12} y={y(value) + 4} textAnchor="end">
            {Math.round(value).toLocaleString("vi-VN")}
          </text>
        </g>
      ))}
      <path className="world-forecast-band" d={band} />
      <polyline className="world-forecast-line" points={line} />
      {points.map((point, index) => (
        <circle key={point.date} className="world-forecast-dot" cx={x(index)} cy={y(point.price_usd_per_tonne)} r="3.5" />
      ))}
      <text x={padding.left} y={height - 12}>
        {formatDate(points[0]?.date)}
      </text>
      <text x={width - padding.right} y={height - 12} textAnchor="end">
        {formatDate(points.at(-1)?.date)}
      </text>
    </svg>
  );
}

export function WorldFertilizerForecastSection() {
  const [commodities, setCommodities] = useState<WorldFertilizerCommodityInfo[]>(FALLBACK_COMMODITIES);
  const [selected, setSelected] = useState<WorldFertilizerCommodity>("urea");
  const [forecast, setForecast] = useState<WorldFertilizerForecast | null>(null);
  const [expandedWeek, setExpandedWeek] = useState(1);
  const [refreshNonce, setRefreshNonce] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchWorldFertilizerCommodities(controller.signal)
      .then((payload) => {
        if (payload.length) setCommodities(payload);
      })
      .catch(() => {
        setCommodities(FALLBACK_COMMODITIES);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    fetchWorldFertilizerForecast(selected, { horizonDays: 30, signal: controller.signal })
      .then((payload) => {
        setForecast(payload);
        setExpandedWeek(payload.forecast_weekly[0]?.week_index ?? 1);
      })
      .catch((err) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Không tải được xu hướng phân bón thế giới.");
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [selected, refreshNonce]);

  const selectedCommodity = commodities.find((item) => item.commodity_slug === selected) ?? FALLBACK_COMMODITIES[0];
  const currentWeek = useMemo<WorldFertilizerWeeklyPoint | undefined>(
    () => forecast?.forecast_weekly.find((week) => week.week_index === expandedWeek) ?? forecast?.forecast_weekly[0],
    [expandedWeek, forecast]
  );
  const daySeven = forecast?.forecast_daily[6];
  const dayThirty = forecast?.forecast_daily.at(-1);
  const summaryTrend = dayThirty?.cumulative_pct_from_today ?? 0;
  const SummaryIcon = summaryTrend > 0.5 ? TrendingUp : summaryTrend < -0.5 ? TrendingDown : Activity;
  const qualityText =
    forecast?.source_mode === "monthly_official_anchor"
      ? "Neo chính thức theo tháng"
      : forecast?.source_mode === "daily_signal"
        ? "Có tín hiệu daily"
        : "Đang đánh giá nguồn";

  return (
    <section id="world" className="input-price-panel world-fertilizer-section">
      <div className="input-section-heading world-heading">
        <div>
          <span className="world-kicker">
            <LineChart size={17} />
            Commodity thế giới
          </span>
          <h2>Xu hướng giá phân bón thế giới</h2>
          <p>Forecast Urê, DAP, Kali theo USD/tấn để người dùng tự áp tỷ lệ vào giá đại lý địa phương.</p>
        </div>
        <button type="button" className="world-refresh-button" onClick={() => setRefreshNonce((value) => value + 1)} disabled={loading}>
          <RefreshCw size={16} />
          {loading ? "Đang tải" : "Làm mới"}
        </button>
      </div>

      <div className="world-commodity-tabs" role="tablist" aria-label="Chọn commodity phân bón thế giới">
        {commodities.map((item) => (
          <button
            key={item.commodity_slug}
            type="button"
            className={item.commodity_slug === selected ? "active" : ""}
            onClick={() => setSelected(item.commodity_slug)}
          >
            <span>{item.name_vi}</span>
            <small>{item.quote_type}</small>
          </button>
        ))}
      </div>

      {error ? <div className="input-price-error">{error}</div> : null}

      <div className="world-summary-grid">
        <div className="world-summary-main">
          <span>{selectedCommodity.name_en}</span>
          <strong>{formatUsd(forecast?.base_price_usd_per_tonne)}</strong>
          <small>
            Cập nhật {formatDate(forecast?.base_observed_at)} - {forecast?.quote_type ?? selectedCommodity.quote_type}
          </small>
        </div>
        <div className={`world-trend-card ${trendClass(daySeven?.cumulative_pct_from_today ?? 0)}`}>
          <BarChart3 size={18} />
          <span>7 ngày tới</span>
          <strong>{formatPct(daySeven?.cumulative_pct_from_today)}</strong>
          <small>So với giá tham chiếu hôm nay</small>
        </div>
        <div className={`world-trend-card ${trendClass(summaryTrend)}`}>
          <SummaryIcon size={18} />
          <span>30 ngày tới</span>
          <strong>{formatPct(summaryTrend)}</strong>
          <small>{qualityText}</small>
        </div>
      </div>

      <div className="world-note">
        <strong>Giá thế giới, không phải giá bán lẻ nội địa.</strong>
        <p>{forecast?.note_vi ?? selectedCommodity.driver_note_vi}</p>
        {forecast?.data_quality?.reason_vi ? <p>{forecast.data_quality.reason_vi}</p> : null}
      </div>

      {!loading && forecast?.forecast_weekly.length === 0 ? (
        <div className="world-forecast-empty">
          Chưa đủ dữ liệu lịch sử để dự báo {selectedCommodity.name_vi}. Crawler đang thu thập thêm dữ liệu từ nguồn công khai.
        </div>
      ) : null}

      {forecast?.forecast_weekly.length ? (
        <>
          <div className="world-weekly-table">
            <div className="world-table-head">
              <span>Tuần</span>
              <span>Giá TB</span>
              <span>Đổi so tuần trước</span>
              <span>Đổi so hôm nay</span>
            </div>
            {forecast.forecast_weekly.map((week) => (
              <button
                key={week.week_index}
                type="button"
                className={week.week_index === currentWeek?.week_index ? "active" : ""}
                onClick={() => setExpandedWeek(week.week_index)}
              >
                <span>{week.week_label_vi}</span>
                <strong>{formatUsd(week.median_price_usd_per_tonne)}</strong>
                <em className={trendClass(week.pct_change_vs_prev_week)}>{formatPct(week.pct_change_vs_prev_week)}</em>
                <em className={trendClass(week.pct_change_vs_today)}>{formatPct(week.pct_change_vs_today)}</em>
              </button>
            ))}
          </div>

          <WorldForecastChart points={currentWeek?.daily_breakdown ?? forecast.forecast_daily.slice(0, 7)} />

          <div className="world-daily-table">
            <table aria-label="Chi tiết dự báo phân bón thế giới theo ngày">
              <thead>
                <tr>
                  <th>Ngày</th>
                  <th>Giá dự báo</th>
                  <th>Đổi mỗi ngày</th>
                  <th>Đổi cộng dồn</th>
                </tr>
              </thead>
              <tbody>
                {(currentWeek?.daily_breakdown ?? []).map((point) => (
                  <tr key={point.date}>
                    <td>{formatDate(point.date)}</td>
                    <td>{formatUsd(point.price_usd_per_tonne)}</td>
                    <td className={trendClass(point.daily_pct_change)}>{formatPct(point.daily_pct_change)}</td>
                    <td className={trendClass(point.cumulative_pct_from_today)}>{formatPct(point.cumulative_pct_from_today)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
    </section>
  );
}
