import {
  Area,
  Bar,
  Brush,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { memo, useEffect, useMemo, useState, type CSSProperties } from "react";
import { TriangleAlert } from "./icons";
import type { ForecastPoint, PricePoint, TradingSignal } from "../lib/api";

type Props = {
  historical: PricePoint[];
  forecast: ForecastPoint[];
  signals: TradingSignal[];
  showPrice: boolean;
  showForecast: boolean;
  showRain: boolean;
  showSignals: boolean;
};

type ChartRow = {
  dateKey: string;
  price?: number;
  forecast?: number;
  rain?: number;
  signalPrice?: number;
};

const toDateKey = (value: string) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value.slice(0, 10) : date.toISOString().slice(0, 10);
};

const formatDate = (value: string) =>
  new Intl.DateTimeFormat("vi-VN", { day: "2-digit", month: "2-digit" }).format(
    new Date(`${value}T00:00:00`)
  );

const formatMoney = (value?: number) => (value ? `${Math.round(value).toLocaleString("vi-VN")} VND` : "-");

const average = (values: number[]) =>
  values.length ? values.reduce((total, value) => total + value, 0) / values.length : undefined;

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

function useCoarsePointer(): boolean {
  const [isCoarse, setIsCoarse] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(pointer: coarse), (max-width: 860px)");
    const update = () => setIsCoarse(mediaQuery.matches);
    update();
    if (typeof mediaQuery.addEventListener === "function") {
      mediaQuery.addEventListener("change", update);
      return () => mediaQuery.removeEventListener("change", update);
    }
    mediaQuery.addListener(update);
    return () => mediaQuery.removeListener(update);
  }, []);

  return isCoarse;
}

function pickDailyPoint(points: PricePoint[]) {
  return (
    points.find((point) => point.quality_grade?.toUpperCase().includes("A") && !point.is_synthetic) ??
    points.find((point) => !point.is_synthetic) ??
    points.find((point) => point.quality_grade?.toUpperCase().includes("A")) ??
    points[0]
  );
}

function MasterChartComponent({ historical, forecast, signals, showPrice, showForecast, showRain, showSignals }: Props) {
  const isDark = useDarkChart();
  const isCoarsePointer = useCoarsePointer();
  const [zoomRange, setZoomRange] = useState<{ startIndex: number; endIndex: number } | null>(null);

  const colors = isDark
    ? {
        grid: "rgba(255,255,255,0.06)",
        axisLine: "rgba(255,255,255,0.18)",
        tickFill: "#b6c0bb",
        priceLine: "#4ade80",
        priceArea: "#4ade80",
        forecastLine: "#fbbf24",
        rainBar: "#60a5fa",
        signal: "#f87171",
        signalText: "#fca5a5",
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
        rainBar: "#1d4ed8",
        signal: "#b91c1c",
        signalText: "#7f1d1d",
        tooltipBg: "#fffdf8",
        tooltipText: "#1f2a23",
        tooltipBorder: "#d3d8d0"
      };

  const rows = useMemo<ChartRow[]>(() => {
    const signalByDate = new Map(signals.map((signal) => [toDateKey(signal.timestamp), signal.price_vnd]));
    const historicalByDate = historical.reduce((groups, point) => {
      const dateKey = toDateKey(point.timestamp);
      groups.set(dateKey, [...(groups.get(dateKey) ?? []), point]);
      return groups;
    }, new Map<string, PricePoint[]>());

    return [
      ...Array.from(historicalByDate.entries())
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([dateKey, points]) => {
          const point = pickDailyPoint(points);
          const rain = average(
            points.map((row) => row.precipitation_mm).filter((value): value is number => typeof value === "number")
          );

          return {
            dateKey,
            price: point.max_price_vnd ?? undefined,
            rain,
            signalPrice: signalByDate.get(dateKey)
          };
        }),
      ...forecast.map((point) => ({
        dateKey: toDateKey(point.timestamp),
        forecast: point.forecast_price_vnd
      }))
    ];
  }, [forecast, historical, signals]);

  const maxRain = Math.max(0, ...rows.map((row) => row.rain ?? 0));
  const rainDomain: [number, number] = [0, Math.max(50, Math.ceil(maxRain * 1.4))];
  const hasRainData = rows.some((row) => typeof row.rain === "number" && row.rain > 0);
  const fullEndIndex = Math.max(rows.length - 1, 0);
  const defaultVisiblePoints = isCoarsePointer ? 72 : 120;
  const defaultZoomRange = { startIndex: Math.max(0, fullEndIndex - defaultVisiblePoints + 1), endIndex: fullEndIndex };
  const activeZoomRange = clampZoomRange(zoomRange ?? defaultZoomRange, fullEndIndex);
  const canZoom = rows.length > 14;
  const showBrush = canZoom && !isCoarsePointer;
  const chartRows = showBrush || !canZoom ? rows : rows.slice(activeZoomRange.startIndex, activeZoomRange.endIndex + 1);

  useEffect(() => {
    setZoomRange(null);
  }, [isCoarsePointer, rows.length]);

  function updateZoom(nextRange: { startIndex: number; endIndex: number }) {
    const clamped = clampZoomRange(nextRange, fullEndIndex);
    setZoomRange((current) => {
      const previous = clampZoomRange(current ?? defaultZoomRange, fullEndIndex);
      if (previous.startIndex === clamped.startIndex && previous.endIndex === clamped.endIndex) {
        return current;
      }
      return clamped;
    });
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
    const startIndex = Math.round(center - nextLength / 2);
    updateZoom({ startIndex, endIndex: startIndex + nextLength - 1 });
  }

  function resetZoom() {
    setZoomRange({ startIndex: 0, endIndex: fullEndIndex });
  }

  return (
    <section className="chart-section">
      <div className="section-heading">
        <div>
          <h2>Diễn biến giá và dự báo</h2>
          <p>Giá lịch sử, đường dự báo và lượng mưa theo bộ lọc đang chọn.</p>
        </div>
        <div className="chart-heading-tools">
          <div className="legend">
            <span className="legend-price" style={{ "--legend-color": colors.priceLine } as CSSProperties}>
              Giá
            </span>
            <span className="legend-forecast" style={{ "--legend-color": colors.forecastLine } as CSSProperties}>
              Dự báo
            </span>
            <span
              className={`legend-rain ${hasRainData ? "" : "legend-disabled"}`}
              style={{ "--legend-color": colors.rainBar } as CSSProperties}
              title={hasRainData ? undefined : "Chưa có dữ liệu lượng mưa"}
            >
              Mưa{hasRainData ? "" : " (chưa có dữ liệu)"}
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
              <button type="button" onClick={resetZoom}>
                Tất cả
              </button>
            </div>
          ) : null}
          {canZoom ? (
            <small className="chart-mobile-hint">Dùng + / - để phóng gần hoặc thu ra, Tất cả để xem toàn bộ chuỗi.</small>
          ) : null}
        </div>
      </div>
      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height={430}>
          <ComposedChart data={chartRows} margin={{ top: 18, right: 16, left: 4, bottom: showBrush ? 4 : 0 }}>
            <defs>
              <linearGradient id="priceArea" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor={colors.priceArea} stopOpacity={isDark ? 0.3 : 0.2} />
                <stop offset="100%" stopColor={colors.priceArea} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke={colors.grid} strokeDasharray="0" vertical={false} />
            <XAxis
              dataKey="dateKey"
              tickFormatter={formatDate}
              minTickGap={30}
              axisLine={{ stroke: colors.axisLine }}
              tickLine={false}
              tick={{ fill: colors.tickFill, fontSize: 11, fontFamily: "JetBrains Mono, monospace" }}
            />
            <YAxis
              yAxisId="price"
              tickFormatter={(value) => `${Math.round(Number(value) / 1000)}K`}
              orientation="right"
              axisLine={false}
              tickLine={false}
              tick={{ fill: colors.tickFill, fontSize: 11, fontFamily: "JetBrains Mono, monospace" }}
              width={56}
            />
            <YAxis yAxisId="rain" orientation="left" domain={rainDomain} hide />
            <Tooltip
              labelFormatter={(label) => formatDate(String(label))}
              contentStyle={{
                background: colors.tooltipBg,
                border: `1px solid ${colors.tooltipBorder}`,
                borderRadius: 2,
                color: colors.tooltipText,
                fontFamily: "Inter, sans-serif",
                fontSize: 12,
                padding: "8px 12px"
              }}
              labelStyle={{ color: colors.tooltipText, fontWeight: 700, marginBottom: 4 }}
              itemStyle={{ color: colors.tooltipText }}
              formatter={(value, name) => {
                if (name === "Mưa (mm)") return [`${value} mm`, "Mưa"];
                return [formatMoney(Number(value)), name === "Dự báo" ? "Dự báo" : "Giá"];
              }}
            />
            {showRain ? (
              <Bar
                yAxisId="rain"
                dataKey="rain"
                fill={colors.rainBar}
                opacity={isDark ? 0.55 : 0.35}
                radius={[2, 2, 0, 0]}
                name="Mưa (mm)"
              />
            ) : null}
            {showPrice ? (
              <Area
                yAxisId="price"
                type="monotone"
                dataKey="price"
                stroke={colors.priceLine}
                strokeWidth={2}
                fill="url(#priceArea)"
                dot={false}
                activeDot={{ r: 4, fill: colors.priceLine, stroke: colors.tooltipBg, strokeWidth: 2 }}
                connectNulls
                name="Giá"
              />
            ) : null}
            {showForecast ? (
              <Line
                yAxisId="price"
                type="monotone"
                dataKey="forecast"
                stroke={colors.forecastLine}
                strokeDasharray="4 4"
                strokeWidth={2}
                dot={false}
                connectNulls
                name="Dự báo"
              />
            ) : null}
            {showSignals
              ? chartRows
                  .filter((row) => typeof row.signalPrice === "number")
                  .map((row) => (
                    <ReferenceDot
                      key={`${row.dateKey}-${row.signalPrice}`}
                      yAxisId="price"
                      x={row.dateKey}
                      y={row.signalPrice}
                      r={isCoarsePointer ? 4 : 6}
                      fill={colors.signal}
                      stroke={colors.tooltipBg}
                      strokeWidth={2}
                      label={
                        isCoarsePointer
                          ? undefined
                          : {
                              value: "Bán",
                              position: "top",
                              fill: colors.signalText,
                              fontSize: 11,
                              fontWeight: 700
                            }
                      }
                    />
                  ))
              : null}
            {showBrush ? (
              <Brush
                dataKey="dateKey"
                height={28}
                travellerWidth={8}
                startIndex={activeZoomRange.startIndex}
                endIndex={activeZoomRange.endIndex}
                tickFormatter={formatDate}
                stroke={colors.priceLine}
                fill={isDark ? "#111918" : "#f4f6f3"}
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
        <div className="signal-chip">
          <TriangleAlert size={16} />
          {signals.length} CẢNH BÁO BÁN
        </div>
      </div>
    </section>
  );
}

function clampZoomRange(range: { startIndex: number; endIndex: number }, fullEndIndex: number) {
  const endLimit = Math.max(0, fullEndIndex);
  const startIndex = Math.min(Math.max(0, range.startIndex), endLimit);
  const endIndex = Math.min(Math.max(startIndex, range.endIndex), endLimit);
  return { startIndex, endIndex };
}

export const MasterChart = memo(MasterChartComponent);
