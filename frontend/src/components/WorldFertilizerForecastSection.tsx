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
import { Activity, BarChart3, Gauge, LineChart, RefreshCw, TrendingDown, TrendingUp } from "./icons";
import { LoadingSkeleton } from "./LoadingSkeleton";
import { useLanguage, type AppLanguage } from "../contexts/LanguageContext";
import { CHART_ZOOM_IN_FACTOR, CHART_ZOOM_OUT_FACTOR, useChartViewport, useCoarseChartPointer } from "../lib/chartViewport";
import {
  fetchWorldFertilizerCommodities,
  fetchWorldFertilizerForecast,
  fetchWorldFertilizerHistory,
  type WorldFertilizerCommodity,
  type WorldFertilizerCommodityInfo,
  type WorldFertilizerForecast,
  type WorldFertilizerForecastPoint,
  type WorldFertilizerHistoryPoint
} from "../lib/api";

const HISTORY_DAYS = 365;

const FALLBACK_COMMODITIES: WorldFertilizerCommodityInfo[] = [
  {
    commodity_slug: "urea",
    name_vi: "Urê",
    name_en: "Urea",
    quote_type: "Benchmark USD/tấn",
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

const COPY = {
  vi: {
    kicker: "Phân bón thế giới",
    title: "Xu hướng giá phân bón thế giới",
    subtitle: "Giá tham chiếu và dự báo 30 ngày theo USD/tấn.",
    refresh: "Làm mới",
    loading: "Đang tải",
    error: "Không tải được dữ liệu dự báo phân bón thế giới. Vui lòng thử lại sau ít phút.",
    tabsLabel: "Chọn nhóm phân bón thế giới",
    sourceDate: "Giá nguồn",
    checkedAt: "quét lúc",
    sevenDays: "7 ngày tới",
    thirtyDays: "30 ngày tới",
    vsToday: "So với giá tham chiếu hôm nay",
    layers: "Lớp dữ liệu",
    price: "Giá",
    forecast: "Dự báo",
    noForecast: "Chưa đủ dữ liệu lịch sử để dự báo. Crawler đang thu thập thêm dữ liệu từ nguồn công khai.",
    chartTitle: "Diễn biến giá và dự báo",
    chartSubtitle: "Giá lịch sử và đường dự báo 30 ngày theo USD/tấn.",
    zoomLabel: "Điều khiển thu phóng biểu đồ",
    zoomIn: "Phóng to biểu đồ",
    zoomOut: "Thu nhỏ biểu đồ",
    all: "Tất cả",
    mobileHint: "Dùng + / - để phóng gần hoặc thu ra, Tất cả để xem toàn bộ chuỗi.",
    previousWindow: "Lùi về khoảng thời gian trước",
    nextWindow: "Tiến tới khoảng thời gian sau",
    rangeLabel: "Chọn khoảng thời gian hiển thị trên biểu đồ",
    historyPrice: "Giá lịch sử",
    tooltipDatePrice: "Giá lịch sử",
    dailyChange: "Đổi mỗi ngày",
    cumulativeChange: "Đổi cộng dồn",
    detailTabsLabel: "Chi tiết dự báo phân bón thế giới",
    analysis: "Phân tích",
    technical: "Kỹ thuật",
    data: "Dữ liệu",
    assessment: "Nhận định",
    isRising: "đang có tín hiệu tăng",
    isFalling: "đang có tín hiệu giảm",
    latestReference: "Giá tham chiếu mới nhất là",
    sevenDayScenario: "Dự báo 7 ngày đang ở mức",
    thirtyDayScenario: "kịch bản 30 ngày là",
    comparedCurrent: "so với hiện tại",
    dataBase: "Nền dữ liệu",
    reliability: "Độ tin cậy",
    historyWindow: "Khung lịch sử",
    technicalSignal: "Tín hiệu kỹ thuật",
    technicalIntro: "Hệ thống so sánh giá hiện tại với mặt bằng 7 ngày, 30 ngày, vùng mua đỡ gần nhất và vùng giá dễ bị chặn lại. Đây là tín hiệu tham khảo để suy ra nhịp điều chỉnh của báo giá địa phương, không phải giá bán lẻ trong nước.",
    technicalCards: {
      summary: "Tổng hợp",
      sevenDay: "Mặt bằng 7 ngày",
      thirtyDay: "Mặt bằng 30 ngày",
      volatility: "Dao động 30 ngày",
      support: "Vùng mua đỡ gần",
      current: "Giá hiện tại",
      resistance: "Vùng giá dễ chững"
    },
    cardDetails: {
      signals: "Dựa trên trend, biên độ và dự báo 30 ngày",
      sevenAbove: "Giá cao hơn gần đây",
      sevenBelow: "Giá thấp hơn gần đây",
      thirtyAbove: "Nền giá còn tốt",
      thirtyBelow: "Nền giá đang yếu",
      volatility: "Mức lên xuống quanh giá trung bình"
    },
    technicalReason: "Lý do dữ liệu",
    table: {
      date: "Ngày",
      type: "Loại",
      price: "Giá",
      daily: "Đổi/ngày",
      source: "Nguồn",
      history: "Lịch sử",
      forecast: "Dự báo"
    },
    emptyChart: "Chưa có dữ liệu dự báo cho lựa chọn này.",
    updating: "Đang cập nhật",
    waiting: "đang chờ",
    qualityHigh: "Tốt",
    qualityMedium: "Trung bình",
    qualityLow: "Cần bổ sung",
    dailySource: "Nguồn daily",
    monthlyAnchor: "Neo monthly",
    insufficient: "Chưa đủ dữ liệu",
    benchmarkQuote: "Benchmark Urê public 1 năm",
    generatedNote: "Mô hình LSTM đang dùng chuỗi daily benchmark mới nhất để dự báo 30 ngày. Đây là xu hướng giá phân bón thế giới theo USD/tấn, không phải giá bán lẻ nội địa. Nên dùng tỷ lệ % tăng/giảm làm tín hiệu nền rồi tự áp vào báo giá đại lý."
  },
  en: {
    kicker: "World fertilizer",
    title: "World fertilizer price trend",
    subtitle: "Reference prices and 30-day forecasts in USD/tonne.",
    refresh: "Refresh",
    loading: "Loading",
    error: "World fertilizer forecast data could not be loaded. Please try again in a few minutes.",
    tabsLabel: "Choose world fertilizer commodity",
    sourceDate: "Source price",
    checkedAt: "checked at",
    sevenDays: "Next 7 days",
    thirtyDays: "Next 30 days",
    vsToday: "Compared with today's reference price",
    layers: "Data layers",
    price: "Price",
    forecast: "Forecast",
    noForecast: "There is not enough historical data for this forecast yet. The crawler is collecting more public data.",
    chartTitle: "Price history and forecast",
    chartSubtitle: "Historical prices and the 30-day forecast line in USD/tonne.",
    zoomLabel: "Chart zoom controls",
    zoomIn: "Zoom in",
    zoomOut: "Zoom out",
    all: "All",
    mobileHint: "Use + / - to zoom in or out, All to view the full series.",
    previousWindow: "Move to the previous time window",
    nextWindow: "Move to the next time window",
    rangeLabel: "Select the visible chart window",
    historyPrice: "Historical price",
    tooltipDatePrice: "Historical price",
    dailyChange: "Daily change",
    cumulativeChange: "Cumulative change",
    detailTabsLabel: "World fertilizer forecast details",
    analysis: "Analysis",
    technical: "Technical",
    data: "Data",
    assessment: "Market read",
    isRising: "is showing upside momentum",
    isFalling: "is showing downside pressure",
    latestReference: "The latest reference price is",
    sevenDayScenario: "The 7-day forecast is",
    thirtyDayScenario: "the 30-day scenario is",
    comparedCurrent: "versus today",
    dataBase: "Data base",
    reliability: "Reliability",
    historyWindow: "History window",
    technicalSignal: "Technical signal",
    technicalIntro: "The system compares the latest price with the 7-day average, 30-day average, nearby support and likely resistance. Use it as a global input-price signal for local quotes, not as a domestic retail price.",
    technicalCards: {
      summary: "Summary",
      sevenDay: "7-day average",
      thirtyDay: "30-day average",
      volatility: "30-day volatility",
      support: "Nearest support",
      current: "Current price",
      resistance: "Likely resistance"
    },
    cardDetails: {
      signals: "Based on trend, range and the 30-day forecast",
      sevenAbove: "Price is above the recent average",
      sevenBelow: "Price is below the recent average",
      thirtyAbove: "Price base remains firm",
      thirtyBelow: "Price base is weakening",
      volatility: "Movement around the average price"
    },
    technicalReason: "Data note",
    table: {
      date: "Date",
      type: "Type",
      price: "Price",
      daily: "Daily change",
      source: "Source",
      history: "History",
      forecast: "Forecast"
    },
    emptyChart: "No forecast data is available for this selection.",
    updating: "Updating",
    waiting: "waiting",
    qualityHigh: "High",
    qualityMedium: "Medium",
    qualityLow: "Needs more data",
    dailySource: "Daily source",
    monthlyAnchor: "Monthly anchor",
    insufficient: "Not enough data",
    benchmarkQuote: "Public 1-year Urea benchmark",
    generatedNote: "The LSTM model uses the latest daily benchmark series to forecast the next 30 days. This is a global fertilizer commodity signal in USD/tonne, not a domestic retail quote. Use the percentage change as a base signal and apply it to local dealer quotes with FX, logistics and inventory adjustments."
  }
} as const;

type WorldChartRow = {
  dateKey: string;
  price?: number;
  forecast?: number;
  dailyPct?: number;
  cumulativePct?: number;
};

type WorldInsightTab = "analysis" | "technical" | "data";
type TechnicalTone = "hold" | "uptrend" | "pullback" | "volatile";

type ChartColors = {
  grid: string;
  axisLine: string;
  tickFill: string;
  priceLine: string;
  priceArea: string;
  forecastLine: string;
  tooltipBg: string;
  tooltipText: string;
  tooltipBorder: string;
};

function locale(language: AppLanguage) {
  return language === "en" ? "en-US" : "vi-VN";
}

function formatUsd(value: number | null | undefined, language: AppLanguage) {
  if (typeof value !== "number" || !Number.isFinite(value)) return COPY[language].updating;
  const unit = language === "en" ? "USD/tonne" : "USD/tấn";
  return `${value.toLocaleString(locale(language), { maximumFractionDigits: 2 })} ${unit}`;
}

function formatDate(value: string | null | undefined, language: AppLanguage) {
  if (!value) return COPY[language].updating;
  return new Intl.DateTimeFormat(locale(language), { day: "2-digit", month: "2-digit", year: "numeric" }).format(new Date(value));
}

function formatCheckedAt(value: string | null | undefined, language: AppLanguage) {
  if (!value) return COPY[language].waiting;
  return new Intl.DateTimeFormat(locale(language), {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit"
  }).format(new Date(value));
}

function formatPct(value: number | null | undefined, language: AppLanguage) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "0.00%";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toLocaleString(locale(language), { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
}

function trendClass(value: number) {
  if (value > 0) return "up";
  if (value < 0) return "down";
  return "flat";
}

function qualityLabel(level: string | null | undefined, language: AppLanguage) {
  const copy = COPY[language];
  if (level === "high") return copy.qualityHigh;
  if (level === "medium") return copy.qualityMedium;
  if (level === "low") return copy.qualityLow;
  return copy.updating;
}

function sourceModeLabel(mode: string | null | undefined, language: AppLanguage) {
  const copy = COPY[language];
  if (mode === "daily_signal") return copy.dailySource;
  if (mode === "monthly_official_anchor") return copy.monthlyAnchor;
  return copy.insufficient;
}

function historyWindowLabel(points: WorldFertilizerHistoryPoint[], language: AppLanguage) {
  if (!points.length) return COPY[language].updating;
  return `${formatDate(points[0].observed_at, language)} - ${formatDate(points.at(-1)?.observed_at, language)}`;
}

function commodityName(item: WorldFertilizerCommodityInfo, language: AppLanguage) {
  return language === "en" ? item.name_en : item.name_vi;
}

function quoteTypeLabel(value: string | null | undefined, language: AppLanguage) {
  if (!value) return COPY[language].updating;
  if (value.includes("CommodityPriceAPI Urea benchmark")) return COPY[language].benchmarkQuote;
  if (language === "en") return value.replace("USD/tấn", "USD/tonne").replace("USD/tan", "USD/tonne");
  return value.replace("USD/tan", "USD/tấn");
}

const toDateKey = (value: string) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value.slice(0, 10) : date.toISOString().slice(0, 10);
};

const formatShortDate = (value: string, language: AppLanguage) =>
  new Intl.DateTimeFormat(locale(language), { day: "2-digit", month: "2-digit" }).format(new Date(`${value}T00:00:00`));

const formatFullDate = (value: string, language: AppLanguage) =>
  new Intl.DateTimeFormat(locale(language), { day: "2-digit", month: "2-digit", year: "numeric" }).format(new Date(`${value}T00:00:00`));

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

function useDarkChart(): boolean {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const check = () => setIsDark(Boolean(document.querySelector(".forecast-shell")));
    check();
    const observer = new MutationObserver(check);
    observer.observe(document.body, {
      attributes: true,
      attributeFilter: ["class"]
    });
    return () => observer.disconnect();
  }, []);

  return isDark;
}

function chartColors(isDark: boolean): ChartColors {
  return isDark
    ? {
        grid: "rgba(255,255,255,0.06)",
        axisLine: "rgba(255,255,255,0.18)",
        tickFill: "#b6c0bb",
        priceLine: "#4ade80",
        priceArea: "#4ade80",
        forecastLine: "#fbbf24",
        tooltipBg: "#181f1d",
        tooltipText: "#ecf2ee",
        tooltipBorder: "rgba(255,255,255,0.18)"
      }
    : {
        grid: "#e8ece6",
        axisLine: "#aab2a3",
        tickFill: "#6b746a",
        priceLine: "#0d4b38",
        priceArea: "#0d4b38",
        forecastLine: "#c4690b",
        tooltipBg: "#fffdf8",
        tooltipText: "#1f2a23",
        tooltipBorder: "#d3d8d0"
      };
}

function WorldForecastTooltip({
  active,
  payload,
  language
}: {
  active?: boolean;
  payload?: Array<{ payload?: WorldChartRow; dataKey?: string; value?: unknown; name?: string }>;
  language: AppLanguage;
}) {
  if (!active || !payload?.length) return null;
  const row = payload.find((item) => item.payload)?.payload;
  if (!row) return null;
  const copy = COPY[language];

  return (
    <div className="world-chart-tooltip">
      <strong>{formatFullDate(row.dateKey, language)}</strong>
      {typeof row.price === "number" ? (
        <span>
          {copy.tooltipDatePrice} <b>{formatUsd(row.price, language)}</b>
        </span>
      ) : null}
      {typeof row.forecast === "number" ? (
        <span>
          {copy.forecast} <b>{formatUsd(row.forecast, language)}</b>
        </span>
      ) : null}
      {typeof row.dailyPct === "number" ? (
        <span>
          {copy.dailyChange} <b className={trendClass(row.dailyPct)}>{formatPct(row.dailyPct, language)}</b>
        </span>
      ) : null}
      {typeof row.cumulativePct === "number" ? (
        <span>
          {copy.cumulativeChange} <b className={trendClass(row.cumulativePct)}>{formatPct(row.cumulativePct, language)}</b>
        </span>
      ) : null}
    </div>
  );
}

function WorldForecastChart({
  rows,
  showPrice,
  showForecast,
  language
}: {
  rows: WorldChartRow[];
  showPrice: boolean;
  showForecast: boolean;
  language: AppLanguage;
}) {
  const isDark = useDarkChart();
  const isCoarsePointer = useCoarseChartPointer();
  const colors = useMemo(() => chartColors(isDark), [isDark]);
  const chartViewport = useChartViewport(rows.length, isCoarsePointer);
  const { activeZoomRange, canZoom, maxWindowStart, panWindowStep, showBrush } = chartViewport;
  const chartRows = showBrush || !canZoom ? rows : rows.slice(activeZoomRange.startIndex, activeZoomRange.endIndex + 1);
  const copy = COPY[language];

  if (!rows.length) {
    return <div className="world-forecast-empty">{copy.emptyChart}</div>;
  }

  return (
    <section className="chart-section world-chart-section">
      <div className="section-heading">
        <div>
          <h2>{copy.chartTitle}</h2>
          <p>{copy.chartSubtitle}</p>
        </div>
        <div className="chart-heading-tools">
          <div className="legend">
            <span className="legend-price" style={{ "--legend-color": colors.priceLine } as CSSProperties}>
              {copy.price}
            </span>
            <span className="legend-forecast" style={{ "--legend-color": colors.forecastLine } as CSSProperties}>
              {copy.forecast}
            </span>
          </div>
          {canZoom ? (
            <div className="chart-zoom-controls" aria-label={copy.zoomLabel}>
              <button type="button" onClick={() => chartViewport.zoomBy(CHART_ZOOM_IN_FACTOR)} aria-label={copy.zoomIn}>
                +
              </button>
              <button type="button" onClick={() => chartViewport.zoomBy(CHART_ZOOM_OUT_FACTOR)} aria-label={copy.zoomOut}>
                -
              </button>
              <button type="button" onClick={chartViewport.resetZoom}>
                {copy.all}
              </button>
            </div>
          ) : null}
          {canZoom ? <small className="chart-mobile-hint">{copy.mobileHint}</small> : null}
          {canZoom && isCoarsePointer ? (
            <div className="mobile-chart-range-controls">
              <div className="mobile-chart-pan-buttons">
                <button
                  type="button"
                  onClick={() => chartViewport.panBy(-panWindowStep)}
                  aria-label={copy.previousWindow}
                >
                  {"<"}
                </button>
                <button
                  type="button"
                  onClick={() => chartViewport.panBy(panWindowStep)}
                  aria-label={copy.nextWindow}
                >
                  {">"}
                </button>
              </div>
              <label>
                <span>
                  {rows[activeZoomRange.startIndex]?.dateKey ? formatShortDate(rows[activeZoomRange.startIndex].dateKey, language) : "-"} -{" "}
                  {rows[activeZoomRange.endIndex]?.dateKey ? formatShortDate(rows[activeZoomRange.endIndex].dateKey, language) : "-"}
                </span>
                <input
                  type="range"
                  min={0}
                  max={maxWindowStart}
                  step={1}
                  value={Math.min(activeZoomRange.startIndex, maxWindowStart)}
                  onInput={(event) => chartViewport.setWindowStart(Number(event.currentTarget.value))}
                  onChange={(event) => chartViewport.setWindowStart(Number(event.currentTarget.value))}
                  aria-label={copy.rangeLabel}
                />
              </label>
            </div>
          ) : null}
        </div>
      </div>
      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height={430}>
          <ComposedChart data={chartRows} margin={{ top: 18, right: 16, left: 4, bottom: showBrush ? 4 : 0 }}>
            <defs>
              <linearGradient id="worldPriceArea" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor={colors.priceArea} stopOpacity={isDark ? 0.3 : 0.2} />
                <stop offset="100%" stopColor={colors.priceArea} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke={colors.grid} strokeDasharray="0" vertical={false} />
            <XAxis
              dataKey="dateKey"
              tickFormatter={(value) => formatShortDate(String(value), language)}
              minTickGap={30}
              axisLine={{ stroke: colors.axisLine }}
              tickLine={false}
              tick={{ fill: colors.tickFill, fontSize: 11, fontFamily: "JetBrains Mono, monospace" }}
            />
            <YAxis
              tickFormatter={(value) => `${Math.round(Number(value))}`}
              orientation="right"
              axisLine={false}
              tickLine={false}
              tick={{ fill: colors.tickFill, fontSize: 11, fontFamily: "JetBrains Mono, monospace" }}
              width={58}
            />
            <Tooltip
              cursor={{ stroke: colors.axisLine, strokeDasharray: "3 4" }}
              content={<WorldForecastTooltip language={language} />}
            />
            {showPrice ? (
              <Area
                type="monotone"
                dataKey="price"
                stroke={colors.priceLine}
                strokeWidth={2}
                fill="url(#worldPriceArea)"
                dot={false}
                activeDot={{ r: 4, fill: colors.priceLine, stroke: colors.tooltipBg, strokeWidth: 2 }}
                connectNulls
                isAnimationActive={false}
                name={copy.historyPrice}
              />
            ) : null}
            {showForecast ? (
              <Line
                type="monotone"
                dataKey="forecast"
                stroke={colors.forecastLine}
                strokeDasharray="4 4"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: colors.forecastLine, stroke: colors.tooltipBg, strokeWidth: 2 }}
                connectNulls
                isAnimationActive={false}
                name={copy.forecast}
              />
            ) : null}
            {showBrush ? (
              <Brush
                dataKey="dateKey"
                height={28}
                travellerWidth={8}
                startIndex={activeZoomRange.startIndex}
                endIndex={activeZoomRange.endIndex}
                tickFormatter={(value) => formatShortDate(String(value), language)}
                stroke={colors.priceLine}
                fill={isDark ? "#111918" : "#f4f6f3"}
                gap={8}
                onChange={(nextRange) => {
                  if (typeof nextRange?.startIndex === "number" && typeof nextRange.endIndex === "number") {
                    chartViewport.updateZoom({ startIndex: nextRange.startIndex, endIndex: nextRange.endIndex });
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
  const volatilityBuffer = Math.max(latest * 0.015, 2);
  return Math.max(0, latest - volatilityBuffer);
}

function nearestResistance(prices: number[], latest: number) {
  const values = uniqueSorted(prices.slice(-45));
  const above = values.filter((price) => price > latest);
  if (above.length) return above[0];
  const volatilityBuffer = Math.max(latest * 0.018, 2);
  return latest + volatilityBuffer;
}

function classifyTechnicalTone(summaryTrend: number, latest: number, sma7: number, sma30: number, volatility: number): TechnicalTone {
  if (volatility > 6) return "volatile";
  if (summaryTrend > 0.8 && latest >= sma7 && sma7 >= sma30) return "uptrend";
  if (summaryTrend < -0.8 || latest < sma7 || sma7 < sma30) return "pullback";
  return "hold";
}

function technicalToneCopy(language: AppLanguage, tone: TechnicalTone) {
  const byLanguage = {
    vi: {
      hold: {
        label: "Theo dõi thêm",
        title: "Giá đang đi ngang, nên dùng tín hiệu % làm nền tham chiếu",
        read: "bên mua và bên bán toàn cầu đang khá cân bằng, chưa tạo áp lực rõ theo một hướng"
      },
      uptrend: {
        label: "Đà tăng nhẹ",
        title: "Giá có lực tăng, cần theo dõi tác động lên báo giá đại lý",
        read: "giá đang cao hơn mặt bằng gần đây và dự báo vẫn nghiêng lên"
      },
      pullback: {
        label: "Áp lực giảm",
        title: "Giá đang yếu hơn mặt bằng gần đây, chưa nên vội tăng giả định chi phí",
        read: "giá hiện tại hoặc dự báo đang thấp hơn vùng trung bình ngắn hạn"
      },
      volatile: {
        label: "Dao động mạnh",
        title: "Biên độ giá cao, nên kiểm tra thêm báo giá thực tế trước khi chốt",
        read: "giá biến động mạnh hơn bình thường nên tín hiệu ngắn hạn có thể nhiễu"
      }
    },
    en: {
      hold: {
        label: "Watch",
        title: "Prices are moving sideways; use the percentage signal as a baseline",
        read: "global buyers and sellers look fairly balanced, without a strong directional push"
      },
      uptrend: {
        label: "Mild uptrend",
        title: "Prices have upside momentum; watch its impact on dealer quotes",
        read: "prices are above recent averages and the forecast still leans higher"
      },
      pullback: {
        label: "Downside pressure",
        title: "Prices are weaker than recent averages; avoid lifting cost assumptions too quickly",
        read: "current or forecast prices are below the short-term average zone"
      },
      volatile: {
        label: "High volatility",
        title: "The price range is wide; confirm with real dealer quotes before deciding",
        read: "prices are moving more than usual, so short-term signals can be noisy"
      }
    }
  };
  return byLanguage[language][tone];
}

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

export function WorldFertilizerForecastSection() {
  const { language } = useLanguage();
  const copy = COPY[language];
  const [commodities, setCommodities] = useState<WorldFertilizerCommodityInfo[]>(FALLBACK_COMMODITIES);
  const [selected, setSelected] = useState<WorldFertilizerCommodity>("urea");
  const [forecast, setForecast] = useState<WorldFertilizerForecast | null>(null);
  const [history, setHistory] = useState<WorldFertilizerHistoryPoint[]>([]);
  const [layers, setLayers] = useState({ price: true, forecast: true });
  const [insightTab, setInsightTab] = useState<WorldInsightTab>("analysis");
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
      fetchWorldFertilizerHistory(selected, { days: HISTORY_DAYS, signal: controller.signal })
    ])
      .then(([forecastPayload, historyPayload]) => {
        setForecast(forecastPayload);
        setHistory(historyPayload);
      })
      .catch((err) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError(copy.error);
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [copy.error, selected, refreshNonce]);

  const selectedCommodity = commodities.find((item) => item.commodity_slug === selected) ?? FALLBACK_COMMODITIES[0];
  const selectedName = commodityName(selectedCommodity, language);
  const daySeven = forecast?.forecast_daily[6];
  const dayThirty = forecast?.forecast_daily.at(-1);
  const summaryTrend = dayThirty?.cumulative_pct_from_today ?? 0;
  const SummaryIcon = summaryTrend > 0.5 ? TrendingUp : summaryTrend < -0.5 ? TrendingDown : Activity;
  const chartRows = useMemo(
    () => buildWorldChartRows(history, forecast?.forecast_daily ?? []),
    [forecast?.forecast_daily, history]
  );
  const historyPrices = useMemo(() => aggregateHistory(history).map((point) => point.price), [history]);
  const latestPrice = forecast?.base_price_usd_per_tonne ?? historyPrices.at(-1) ?? 0;
  const sma7 = average(historyPrices.slice(-7)) || latestPrice;
  const sma30 = average(historyPrices.slice(-30)) || latestPrice;
  const volatility30 = volatilityPct(historyPrices.slice(-30));
  const support = nearestSupport(historyPrices, latestPrice);
  const resistance = nearestResistance(historyPrices, latestPrice);
  const technicalTone = classifyTechnicalTone(summaryTrend, latestPrice, sma7, sma30, volatility30);
  const technicalCopy = technicalToneCopy(language, technicalTone);
  const TechnicalIcon = technicalTone === "uptrend" ? TrendingUp : technicalTone === "pullback" ? TrendingDown : Activity;
  const recentForecastRows = forecast?.forecast_daily ?? [];
  const dataRows = useMemo(
    () => [
      ...history.slice(-10).map((point) => ({
        key: `history-${point.observed_at}`,
        date: point.observed_at,
        price: point.price_usd_per_tonne,
        change: null as number | null,
        type: copy.table.history,
        source: point.source
      })),
      ...recentForecastRows.map((point) => ({
        key: `forecast-${point.date}`,
        date: point.date,
        price: point.price_usd_per_tonne,
        change: point.daily_pct_change,
        type: copy.table.forecast,
        source: forecast?.model_kind ?? "forecast"
      }))
    ],
    [copy.table.forecast, copy.table.history, forecast?.model_kind, history, recentForecastRows]
  );
  const note = language === "vi" ? forecast?.note_vi : copy.generatedNote;
  const dataReason =
    language === "vi"
      ? forecast?.data_quality?.reason_vi
      : "Recent daily benchmark data is available; World Bank Pink Sheet is kept as a cross-checking anchor.";

  return (
    <section id="world" className="input-price-panel world-fertilizer-section">
      <div className="input-section-heading world-heading">
        <div>
          <span className="world-kicker">
            <LineChart size={17} />
            {copy.kicker}
          </span>
          <h2>{copy.title}</h2>
          <p>{copy.subtitle}</p>
        </div>
        <button type="button" className="world-refresh-button" onClick={() => setRefreshNonce((value) => value + 1)} disabled={loading}>
          <RefreshCw size={16} />
          {loading ? copy.loading : copy.refresh}
        </button>
      </div>

      <div className="world-commodity-tabs" role="tablist" aria-label={copy.tabsLabel}>
        {commodities.map((item) => (
          <button
            key={item.commodity_slug}
            type="button"
            className={item.commodity_slug === selected ? "active" : ""}
            onClick={() => setSelected(item.commodity_slug)}
          >
            <span>{commodityName(item, language)}</span>
            <small>{quoteTypeLabel(item.quote_type, language)}</small>
          </button>
        ))}
      </div>

      {error ? <div className="input-price-error">{error}</div> : null}
      {loading && !forecast ? <LoadingSkeleton variant="chart" label={copy.loading} rows={5} /> : null}

      <div className="world-summary-grid">
        <div className="world-summary-main">
          <span>{selectedName}</span>
          <strong>{formatUsd(forecast?.base_price_usd_per_tonne, language)}</strong>
          <small>
            {copy.sourceDate} {formatDate(forecast?.base_observed_at, language)} · {copy.checkedAt}{" "}
            {formatCheckedAt(forecast?.data_quality?.last_source_check_at, language)}
          </small>
        </div>
        <div className={`world-trend-card ${trendClass(daySeven?.cumulative_pct_from_today ?? 0)}`}>
          <BarChart3 size={18} />
          <span>{copy.sevenDays}</span>
          <strong>{formatPct(daySeven?.cumulative_pct_from_today, language)}</strong>
          <small>{copy.vsToday}</small>
        </div>
        <div className={`world-trend-card ${trendClass(summaryTrend)}`}>
          <SummaryIcon size={18} />
          <span>{copy.thirtyDays}</span>
          <strong>{formatPct(summaryTrend, language)}</strong>
          <small>{copy.vsToday}</small>
        </div>
      </div>

      <section className="chart-toolbar world-chart-toolbar" aria-label={copy.layers}>
        <div className="chart-control-group chart-control-group--layers world-layer-control">
          <span className="control-label">{copy.layers}</span>
          <div className="layer-toggles">
            <button type="button" className={layers.price ? "active" : ""} onClick={() => setLayers((value) => ({ ...value, price: !value.price }))}>
              {copy.price}
            </button>
            <button type="button" className={layers.forecast ? "active" : ""} onClick={() => setLayers((value) => ({ ...value, forecast: !value.forecast }))}>
              {copy.forecast}
            </button>
          </div>
        </div>
      </section>

      {!loading && forecast?.forecast_daily.length === 0 ? <div className="world-forecast-empty">{copy.noForecast}</div> : null}

      {forecast?.forecast_daily.length ? (
        <>
          <WorldForecastChart rows={chartRows} showPrice={layers.price} showForecast={layers.forecast} language={language} />

          <nav className="world-insight-tabs" aria-label={copy.detailTabsLabel}>
            {[
              { value: "analysis", label: copy.analysis },
              { value: "technical", label: copy.technical },
              { value: "data", label: copy.data }
            ].map((tab) => (
              <button
                key={tab.value}
                type="button"
                className={insightTab === tab.value ? "active" : ""}
                onClick={() => setInsightTab(tab.value as WorldInsightTab)}
              >
                {tab.label}
              </button>
            ))}
          </nav>

          {insightTab === "analysis" ? (
            <section className="world-insight-panel world-analysis-panel">
              <div>
                <span className="world-insight-kicker">{copy.assessment}</span>
                <h3>
                  {selectedName} {summaryTrend >= 0 ? copy.isRising : copy.isFalling}
                </h3>
                <p>
                  {copy.latestReference} {formatUsd(forecast.base_price_usd_per_tonne, language)}. {copy.sevenDayScenario}{" "}
                  <strong className={trendClass(daySeven?.cumulative_pct_from_today ?? 0)}>
                    {formatPct(daySeven?.cumulative_pct_from_today, language)}
                  </strong>
                  , {copy.thirtyDayScenario} <strong className={trendClass(summaryTrend)}>{formatPct(summaryTrend, language)}</strong>{" "}
                  {copy.comparedCurrent}.
                </p>
                <p>{note}</p>
              </div>
              <div className="world-driver-list">
                <div>
                  <strong>{copy.dataBase}</strong>
                  <span>{sourceModeLabel(forecast.source_mode, language)}</span>
                </div>
                <div>
                  <strong>{copy.reliability}</strong>
                  <span>{qualityLabel(forecast.data_quality?.level, language)}</span>
                </div>
                <div>
                  <strong>{copy.historyWindow}</strong>
                  <span>{historyWindowLabel(history, language)}</span>
                </div>
              </div>
            </section>
          ) : null}

          {insightTab === "technical" ? (
            <section className="world-insight-panel world-technical-panel-v2 technical-panel">
              <div className="technical-summary">
                <span>
                  <Gauge size={17} />
                  {copy.technicalSignal}
                </span>
                <h2>{technicalCopy.title}</h2>
                <p>
                  {copy.technicalIntro} {language === "vi" ? "Hiện tại" : "Currently"}, {selectedName}{" "}
                  {latestPrice >= sma7
                    ? language === "vi"
                      ? "cao hơn mặt bằng 7 ngày"
                      : "is above its 7-day average"
                    : language === "vi"
                      ? "thấp hơn mặt bằng 7 ngày"
                      : "is below its 7-day average"}{" "}
                  {language === "vi" ? "và" : "and"}{" "}
                  {latestPrice >= sma30
                    ? language === "vi"
                      ? "cao hơn mặt bằng 30 ngày"
                      : "above its 30-day average"
                    : language === "vi"
                      ? "thấp hơn mặt bằng 30 ngày"
                      : "below its 30-day average"}
                  , {technicalCopy.read}.
                </p>
              </div>

              <div className="technical-cards">
                <TechnicalCard icon={TechnicalIcon} label={copy.technicalCards.summary} value={technicalCopy.label} detail={copy.cardDetails.signals} />
                <TechnicalCard
                  icon={LineChart}
                  label={copy.technicalCards.sevenDay}
                  value={formatUsd(sma7, language)}
                  detail={latestPrice >= sma7 ? copy.cardDetails.sevenAbove : copy.cardDetails.sevenBelow}
                />
                <TechnicalCard
                  icon={BarChart3}
                  label={copy.technicalCards.thirtyDay}
                  value={formatUsd(sma30, language)}
                  detail={latestPrice >= sma30 ? copy.cardDetails.thirtyAbove : copy.cardDetails.thirtyBelow}
                />
                <TechnicalCard
                  icon={Activity}
                  label={copy.technicalCards.volatility}
                  value={formatPct(forecast.volatility_daily ? forecast.volatility_daily * 100 : volatility30, language)}
                  detail={copy.cardDetails.volatility}
                />
              </div>

              <div className="technical-levels">
                <article>
                  <span>{copy.technicalCards.support}</span>
                  <strong>{formatUsd(support || latestPrice, language)}</strong>
                </article>
                <article>
                  <span>{copy.technicalCards.current}</span>
                  <strong>{formatUsd(latestPrice, language)}</strong>
                </article>
                <article>
                  <span>{copy.technicalCards.resistance}</span>
                  <strong>{formatUsd(resistance || latestPrice, language)}</strong>
                </article>
              </div>

              <p className="world-technical-reason">
                <strong>{copy.technicalReason}: </strong>
                {dataReason}
              </p>
            </section>
          ) : null}

          {insightTab === "data" ? (
            <div className="world-data-table">
              <table aria-label={copy.detailTabsLabel}>
                <thead>
                  <tr>
                    <th>{copy.table.date}</th>
                    <th>{copy.table.type}</th>
                    <th>{copy.table.price}</th>
                    <th>{copy.table.daily}</th>
                    <th>{copy.table.source}</th>
                  </tr>
                </thead>
                <tbody>
                  {dataRows.map((point) => (
                    <tr key={point.key}>
                      <td>{formatDate(point.date, language)}</td>
                      <td>{point.type}</td>
                      <td>{formatUsd(point.price, language)}</td>
                      <td className={point.change === null ? "flat" : trendClass(point.change)}>
                        {point.change === null ? "-" : formatPct(point.change, language)}
                      </td>
                      <td>{point.source}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
