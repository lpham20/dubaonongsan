import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { memo } from "react";
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

function pickDailyPoint(points: PricePoint[]) {
  return (
    points.find((point) => point.quality_grade?.toUpperCase().includes("A") && !point.is_synthetic) ??
    points.find((point) => !point.is_synthetic) ??
    points.find((point) => point.quality_grade?.toUpperCase().includes("A")) ??
    points[0]
  );
}

function MasterChartComponent({ historical, forecast, signals, showPrice, showForecast, showRain, showSignals }: Props) {
  const signalByDate = new Map(signals.map((signal) => [toDateKey(signal.timestamp), signal.price_vnd]));
  const historicalByDate = historical.reduce((groups, point) => {
    const dateKey = toDateKey(point.timestamp);
    groups.set(dateKey, [...(groups.get(dateKey) ?? []), point]);
    return groups;
  }, new Map<string, PricePoint[]>());

  const rows: ChartRow[] = [
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

  return (
    <section className="chart-section">
      <div className="section-heading">
        <div>
          <h2>Diễn biến giá và dự báo</h2>
          <p>Giá lịch sử, đường dự báo và tín hiệu cảnh báo theo bộ lọc đang chọn.</p>
        </div>
        <div className="legend">
          <span className="legend-price">Giá</span>
          <span className="legend-forecast">Dự báo</span>
          <span className="legend-rain">Mưa</span>
        </div>
      </div>
      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height={430}>
          <ComposedChart data={rows} margin={{ top: 18, right: 16, left: 4, bottom: 4 }}>
            <defs>
              <linearGradient id="priceArea" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="#1a4d2e" stopOpacity={0.14} />
                <stop offset="100%" stopColor="#1a4d2e" stopOpacity={0.025} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#eef2f4" strokeDasharray="0" vertical={false} />
            <XAxis
              dataKey="dateKey"
              tickFormatter={formatDate}
              minTickGap={30}
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#64748b", fontSize: 11, fontFamily: "Inter, sans-serif" }}
            />
            <YAxis
              yAxisId="price"
              tickFormatter={(value) => `${Math.round(Number(value) / 1000)}k`}
              orientation="right"
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#64748b", fontSize: 11, fontFamily: "Inter, sans-serif" }}
              width={58}
            />
            <YAxis yAxisId="rain" hide />
            <Tooltip
              labelFormatter={(label) => formatDate(String(label))}
              formatter={(value, name) => {
                if (name === "rain") return [`${value} mm`, "Mưa"];
                return [formatMoney(Number(value)), name === "forecast" ? "Dự báo" : "Giá"];
              }}
            />
            {showRain ? (
              <Bar
                yAxisId="rain"
                dataKey="rain"
                fill="#a8d5b8"
                opacity={0.36}
                radius={[4, 4, 0, 0]}
                name="rain"
              />
            ) : null}
            {showPrice ? (
              <Area
                yAxisId="price"
                type="monotone"
                dataKey="price"
                stroke="#1a4d2e"
                strokeWidth={1.7}
                fill="url(#priceArea)"
                dot={false}
                activeDot={{ r: 4, fill: "#1a4d2e", stroke: "#fff", strokeWidth: 2 }}
                connectNulls
                name="price"
              />
            ) : null}
            {showForecast ? (
              <Line
                yAxisId="price"
                type="monotone"
                dataKey="forecast"
                stroke="#c47a2c"
                strokeDasharray="5 5"
                strokeWidth={1.7}
                dot={false}
                connectNulls
                name="forecast"
              />
            ) : null}
            {showSignals
              ? rows
                  .filter((row) => typeof row.signalPrice === "number")
                  .map((row) => (
                    <ReferenceDot
                      key={`${row.dateKey}-${row.signalPrice}`}
                      yAxisId="price"
                      x={row.dateKey}
                      y={row.signalPrice}
                      r={6}
                      fill="#c43d3d"
                      stroke="#fff"
                      strokeWidth={2}
                      label={{ value: "Bán", position: "top", fill: "#8f1d1d", fontSize: 11, fontWeight: 700 }}
                    />
                  ))
              : null}
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

export const MasterChart = memo(MasterChartComponent);
