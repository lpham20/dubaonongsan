import { memo } from "react";
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
  const items = buildForecastTicker(points);
  const repeated = [...items, ...items];

  return (
    <div className="home-price-ticker forecast-price-ticker" aria-label="Dải băng giá nông sản">
      <div className="home-price-ticker-label">
        Giá trực tuyến
      </div>
      <div className="home-price-track">
        <div className="home-price-content">
          {repeated.map((item, index) => (
            <span key={`${item.label}-${index}`}>
              <strong>{item.label}</strong>
              <b>{item.value}</b>
              <em className={item.tone}>{item.change}</em>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

export const TickerTape = memo(TickerTapeComponent);

function buildForecastTicker(points: PricePoint[]): TickerItem[] {
  const seen = new Set<string>();
  const items: TickerItem[] = [];

  for (const point of points) {
    if (!point.max_price_vnd) continue;

    const label = formatLabel(point);
    const key = label.toLocaleLowerCase("vi-VN");
    if (seen.has(key)) continue;
    seen.add(key);

    const series = points.filter((item) => formatLabel(item) === label && item.max_price_vnd);
    const latest = series[0]?.max_price_vnd ?? point.max_price_vnd;
    const previous = series[1]?.max_price_vnd;
    const change = previous ? ((latest - previous) / previous) * 100 : 0;

    items.push({
      label,
      value: `${Math.round(latest).toLocaleString("vi-VN")} đ/kg`,
      change: `${change >= 0 ? "+" : ""}${change.toLocaleString("vi-VN", { maximumFractionDigits: 1 })}%`,
      tone: change >= 0 ? "up" : "down"
    });

    if (items.length >= 4) break;
  }

  return items.length
    ? items
    : [
        { label: "Cà phê Robusta", value: "Đang cập nhật", change: "+0,0%", tone: "up" },
        { label: "Sầu riêng Ri6", value: "Đang cập nhật", change: "+0,0%", tone: "up" },
        { label: "Phân bón urê", value: "Đang cập nhật", change: "+0,0%", tone: "up" },
        { label: "Tỷ giá xuất khẩu", value: "Đang cập nhật", change: "+0,0%", tone: "up" }
      ];
}

function formatLabel(point: PricePoint) {
  const grade = point.quality_grade ? ` ${point.quality_grade}` : "";
  const market = point.province ?? point.region ?? "";
  return `${point.variety}${grade}${market ? ` ${market}` : ""}`.trim();
}
