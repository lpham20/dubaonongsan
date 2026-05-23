import { useEffect, useMemo, useState, type CSSProperties } from "react";
import {
  Area,
  Brush,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { Activity, BarChart3, LineChart, RefreshCw, TrendingDown, TrendingUp } from "./icons";
import {
  fetchWorldFertilizerCommodities,
  fetchWorldFertilizerForecast,
  fetchWorldFertilizerHistory,
  type WorldFertilizerCommodity,
  type WorldFertilizerCommodityInfo,
  type WorldFertilizerForecast,
  type WorldFertilizerForecastPoint,
  type WorldFertilizerHistoryPoint,
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

function formatCheckedAt(value: string | null | undefined) {
  if (!value) return "đang chờ";
  return new Intl.DateTimeFormat("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit"
  }).format(new Date(value));
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

type WorldChartRow = {
  dateKey: string;
  price?: number;
  forecast?: number;
  dailyPct?: number;
  cumulativePct?: number;
};

const chartColors = {
  grid: "rgba(255,255,255,0.06)",
  axisLine: "rgba(255,255,255,0.18)",
  tickFill: "#b6c0bb",
  priceLine: "#4ade80",
  priceArea: "#4ade80",
  forecastLine: "#fbbf24",
  tooltipBg: "#181f1d",
  tooltipText: "#ecf2ee",
  tooltipBorder: "rgba(255,255,255,0.18)"
};

const toDateKey = (value: string) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value.slice(0, 10) : date.toISOString().slice(0, 10);
};

const formatShortDate = (value: string) =>
  new Intl.DateTimeFormat("vi-VN", { day: "2-digit", month: "2-digit" }).format(new Date(`${value}T00:00:00`));

const formatFullDate = (value: string) =>
  new Intl.DateTimeFormat("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" }).format(new Date(`${value}T00:00:00`));

function aggregateHistory(history: WorldFertilizerHistoryPoint[]) {
  const groups = history.reduce((map, point) => {
    const dateKey = toDateKey(point.observed_at);
    map.set(dateKey, [...(map.get(dateKey) ?? []), point]);
    return map;
  }, new Map<string, WorldFertilizerHistoryPoint[]>());

  return Array.from(groups.entries())
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([dateKey, points]) => ({
      dateKey,
      price: points.reduce((total, point) => total + point.price_usd_per_tonne, 0) / points.length
    }));
}

function buildWorldChartRows(history: WorldFertilizerHistoryPoint[], forecast: WorldFertilizerForecastPoint[]) {
  return [
    ...aggregateHistory(history),
    ...forecast.map((point) => ({
      dateKey: toDateKey(point.date),
      forecast: point.price_usd_per_tonne,
      dailyPct: point.daily_pct_change,
      cumulativePct: point.cumulative_pct_from_today
    }))
  ];
}

function clampZoomRange(range: { startIndex: number; endIndex: number }, fullEndIndex: number) {
  const endLimit = Math.max(0, fullEndIndex);
  const startIndex = Math.min(Math.max(0, range.startIndex), endLimit);
  const endIndex = Math.min(Math.max(startIndex, range.endIndex), endLimit);
  return { startIndex, endIndex };
}

function WorldForecastTooltip({
  active,
  payload
}: {
  active?: boolean;
  payload?: Array<{ payload?: WorldChartRow; dataKey?: string; value?: unknown; name?: string }>;
}) {
  if (!active || !payload?.length) return null;
  const row = payload.find((item) => item.payload)?.payload;
  if (!row) return null;
  return (
    <div className="world-chart-tooltip">
      <strong>{formatFullDate(row.dateKey)}</strong>
      {typeof row.price === "number" ? (
        <span>
          Giá lịch sử <b>{formatUsd(row.price)}</b>
        </span>
      ) : null}
      {typeof row.forecast === "number" ? (
        <span>
          Dự báo <b>{formatUsd(row.forecast)}</b>
        </span>
      ) : null}
      {typeof row.dailyPct === "number" ? (
        <span>
          Đổi mỗi ngày <b className={trendClass(row.dailyPct)}>{formatPct(row.dailyPct)}</b>
        </span>
      ) : null}
      {typeof row.cumulativePct === "number" ? (
        <span>
          Đổi cộng dồn <b className={trendClass(row.cumulativePct)}>{formatPct(row.cumulativePct)}</b>
        </span>
      ) : null}
    </div>
  );
}

function WorldForecastChart({
  rows,
  showPrice,
  showForecast
}: {
  rows: WorldChartRow[];
  showPrice: boolean;
  showForecast: boolean;
}) {
  const [zoomRange, setZoomRange] = useState<{ startIndex: number; endIndex: number } | null>(null);
  const fullEndIndex = Math.max(rows.length - 1, 0);
  const defaultVisiblePoints = 120;
  const defaultZoomRange = { startIndex: Math.max(0, fullEndIndex - defaultVisiblePoints + 1), endIndex: fullEndIndex };
  const activeZoomRange = clampZoomRange(zoomRange ?? defaultZoomRange, fullEndIndex);
  const canZoom = rows.length > 14;

  useEffect(() => {
    setZoomRange(null);
  }, [rows.length]);

  function updateZoom(nextRange: { startIndex: number; endIndex: number }) {
    setZoomRange(clampZoomRange(nextRange, fullEndIndex));
  }

  function zoomBy(factor: number) {
    if (!canZoom) return;
    const currentLength = activeZoomRange.endIndex - activeZoomRange.startIndex + 1;
    const nextLength = Math.min(rows.length, Math.max(14, Math.round(currentLength * factor)));
    if (nextLength >= rows.length) {
      updateZoom({ startIndex: 0, endIndex: fullEndIndex });
      return;
    }
    const center = (activeZoomRange.startIndex + activeZoomRange.endIndex) / 2;
    const maxStart = Math.max(0, rows.length - nextLength);
    const startIndex = Math.min(maxStart, Math.max(0, Math.round(center - (nextLength - 1) / 2)));
    updateZoom({ startIndex, endIndex: startIndex + nextLength - 1 });
  }

  if (!rows.length) {
    return <div className="world-forecast-empty">Chưa có dữ liệu dự báo cho lựa chọn này.</div>;
  }

  return (
    <section className="chart-section world-chart-section">
      <div className="section-heading">
        <div>
          <h2>Diễn biến giá và dự báo</h2>
          <p>Giá lịch sử và đường dự báo 30 ngày theo USD/tấn.</p>
        </div>
        <div className="chart-heading-tools">
          <div className="legend">
            <span className="legend-price" style={{ "--legend-color": chartColors.priceLine } as CSSProperties}>
              Giá
            </span>
            <span className="legend-forecast" style={{ "--legend-color": chartColors.forecastLine } as CSSProperties}>
              Dự báo
            </span>
          </div>
          {canZoom ? (
            <div className="chart-zoom-controls" aria-label="Điều khiển thu phóng biểu đồ">
              <button type="button" onClick={() => zoomBy(0.58)} aria-label="Phóng to biểu đồ">
                +
              </button>
              <button type="button" onClick={() => zoomBy(1.72)} aria-label="Thu nhỏ biểu đồ">
                -
              </button>
              <button type="button" onClick={() => updateZoom({ startIndex: 0, endIndex: fullEndIndex })}>
                Tất cả
              </button>
            </div>
          ) : null}
        </div>
      </div>
      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height={430}>
          <ComposedChart data={rows} margin={{ top: 18, right: 16, left: 4, bottom: canZoom ? 4 : 0 }}>
            <defs>
              <linearGradient id="worldPriceArea" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor={chartColors.priceArea} stopOpacity={0.3} />
                <stop offset="100%" stopColor={chartColors.priceArea} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke={chartColors.grid} strokeDasharray="0" vertical={false} />
            <XAxis
              dataKey="dateKey"
              tickFormatter={formatShortDate}
              minTickGap={30}
              axisLine={{ stroke: chartColors.axisLine }}
              tickLine={false}
              tick={{ fill: chartColors.tickFill, fontSize: 11, fontFamily: "JetBrains Mono, monospace" }}
            />
            <YAxis
              tickFormatter={(value) => `${Math.round(Number(value))}`}
              orientation="right"
              axisLine={false}
              tickLine={false}
              tick={{ fill: chartColors.tickFill, fontSize: 11, fontFamily: "JetBrains Mono, monospace" }}
              width={58}
            />
            <Tooltip
              cursor={{ stroke: chartColors.axisLine, strokeDasharray: "3 4" }}
              content={<WorldForecastTooltip />}
            />
            {showPrice ? (
              <Area
                type="monotone"
                dataKey="price"
                stroke={chartColors.priceLine}
                strokeWidth={2}
                fill="url(#worldPriceArea)"
                dot={false}
                activeDot={{ r: 4, fill: chartColors.priceLine, stroke: chartColors.tooltipBg, strokeWidth: 2 }}
                connectNulls
                isAnimationActive={false}
                name="Giá lịch sử"
              />
            ) : null}
            {showForecast ? (
              <Line
                type="monotone"
                dataKey="forecast"
                stroke={chartColors.forecastLine}
                strokeDasharray="4 4"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: chartColors.forecastLine, stroke: chartColors.tooltipBg, strokeWidth: 2 }}
                connectNulls
                isAnimationActive={false}
                name="Dự báo"
              />
            ) : null}
            {canZoom ? (
              <Brush
                dataKey="dateKey"
                height={28}
                travellerWidth={8}
                startIndex={activeZoomRange.startIndex}
                endIndex={activeZoomRange.endIndex}
                tickFormatter={formatShortDate}
                stroke={chartColors.priceLine}
                fill="#111918"
                gap={8}
                onChange={(nextRange) => {
                  if (typeof nextRange?.startIndex === "number" && typeof nextRange.endIndex === "number") {
                    updateZoom({ startIndex: nextRange.startIndex, endIndex: nextRange.endIndex });
                  }
                }}
              />
            ) : null}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

export function WorldFertilizerForecastSection() {
  const [commodities, setCommodities] = useState<WorldFertilizerCommodityInfo[]>(FALLBACK_COMMODITIES);
  const [selected, setSelected] = useState<WorldFertilizerCommodity>("urea");
  const [forecast, setForecast] = useState<WorldFertilizerForecast | null>(null);
  const [history, setHistory] = useState<WorldFertilizerHistoryPoint[]>([]);
  const [historyDays, setHistoryDays] = useState(365);
  const [layers, setLayers] = useState({ price: true, forecast: true });
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
    Promise.all([
      fetchWorldFertilizerForecast(selected, { horizonDays: 30, signal: controller.signal }),
      fetchWorldFertilizerHistory(selected, { days: historyDays, signal: controller.signal })
    ])
      .then(([forecastPayload, historyPayload]) => {
        setForecast(forecastPayload);
        setHistory(historyPayload);
        setExpandedWeek(forecastPayload.forecast_weekly[0]?.week_index ?? 1);
      })
      .catch((err) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError("Không tải được dữ liệu dự báo phân bón thế giới. Vui lòng thử lại sau ít phút.");
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [selected, historyDays, refreshNonce]);

  const selectedCommodity = commodities.find((item) => item.commodity_slug === selected) ?? FALLBACK_COMMODITIES[0];
  const currentWeek = useMemo<WorldFertilizerWeeklyPoint | undefined>(
    () => forecast?.forecast_weekly.find((week) => week.week_index === expandedWeek) ?? forecast?.forecast_weekly[0],
    [expandedWeek, forecast]
  );
  const daySeven = forecast?.forecast_daily[6];
  const dayThirty = forecast?.forecast_daily.at(-1);
  const summaryTrend = dayThirty?.cumulative_pct_from_today ?? 0;
  const SummaryIcon = summaryTrend > 0.5 ? TrendingUp : summaryTrend < -0.5 ? TrendingDown : Activity;
  const chartRows = useMemo(
    () => buildWorldChartRows(history, forecast?.forecast_daily ?? []),
    [forecast?.forecast_daily, history]
  );

  return (
    <section id="world" className="input-price-panel world-fertilizer-section">
      <div className="input-section-heading world-heading">
        <div>
          <span className="world-kicker">
            <LineChart size={17} />
            Phân bón thế giới
          </span>
          <h2>Xu hướng giá phân bón thế giới</h2>
          <p>Giá tham chiếu và dự báo 30 ngày theo USD/tấn.</p>
        </div>
        <button type="button" className="world-refresh-button" onClick={() => setRefreshNonce((value) => value + 1)} disabled={loading}>
          <RefreshCw size={16} />
          {loading ? "Đang tải" : "Làm mới"}
        </button>
      </div>

      <div className="world-commodity-tabs" role="tablist" aria-label="Chọn nhóm phân bón thế giới">
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
          <span>{selectedCommodity.name_vi}</span>
          <strong>{formatUsd(forecast?.base_price_usd_per_tonne)}</strong>
          <small>
            Giá nguồn {formatDate(forecast?.base_observed_at)} · quét lúc {formatCheckedAt(forecast?.data_quality?.last_source_check_at)}
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
          <small>So với giá tham chiếu hôm nay</small>
        </div>
      </div>

      <section className="chart-toolbar world-chart-toolbar" aria-label="Điều khiển biểu đồ phân bón thế giới">
        <div className="chart-control-group">
          <span className="control-label">Khoảng thời gian</span>
          <div className="segmented">
            {[
              { days: 90, label: "90 ngày" },
              { days: 365, label: "1 năm" },
              { days: 1095, label: "3 năm" }
            ].map((period) => (
              <button
                key={period.days}
                type="button"
                className={historyDays === period.days ? "active" : ""}
                onClick={() => setHistoryDays(period.days)}
              >
                {period.label}
              </button>
            ))}
          </div>
        </div>
        <div className="chart-control-group chart-control-group--layers">
          <span className="control-label">Lớp dữ liệu</span>
          <div className="layer-toggles">
            <button type="button" className={layers.price ? "active" : ""} onClick={() => setLayers((value) => ({ ...value, price: !value.price }))}>
              Giá
            </button>
            <button type="button" className={layers.forecast ? "active" : ""} onClick={() => setLayers((value) => ({ ...value, forecast: !value.forecast }))}>
              Dự báo
            </button>
          </div>
        </div>
      </section>

      {!loading && forecast?.forecast_weekly.length === 0 ? (
        <div className="world-forecast-empty">
          Chưa đủ dữ liệu lịch sử để dự báo {selectedCommodity.name_vi}. Crawler đang thu thập thêm dữ liệu từ nguồn công khai.
        </div>
      ) : null}

      {forecast?.forecast_weekly.length ? (
        <>
          <WorldForecastChart
            rows={chartRows}
            showPrice={layers.price}
            showForecast={layers.forecast}
          />

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
