import { useEffect, useMemo, useState } from "react";
import { Activity, BarChart3, Database, Filter, PackageCheck, RefreshCw, TrendingUp } from "./icons";
import { SeoHead } from "./SeoHead";
import {
  fetchAgriInputForecast,
  fetchAgriInputHistory,
  fetchAgriInputLatest,
  fetchAgriInputProducts,
  type AgriInputForecastPoint,
  type AgriInputPricePoint,
  type AgriInputProduct
} from "../lib/api";

type SeriesPoint = {
  timestamp: string;
  value: number;
  low?: number;
  high?: number;
};

const COLLATOR = new Intl.Collator("vi-VN");

function formatVnd(value: number | null | undefined) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "Đang cập nhật";
  return `${Math.round(value).toLocaleString("vi-VN")} đ`;
}

function formatDate(value: string | null | undefined) {
  if (!value) return "Đang cập nhật";
  return new Intl.DateTimeFormat("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" }).format(new Date(value));
}

function aggregateHistory(rows: AgriInputPricePoint[]): SeriesPoint[] {
  const grouped = new Map<string, { total: number; count: number }>();
  rows.forEach((row) => {
    const key = row.observed_at.slice(0, 10);
    const current = grouped.get(key) ?? { total: 0, count: 0 };
    current.total += row.package_price_vnd ?? row.normalized_price_vnd * (row.package_size_kg ?? 1);
    current.count += 1;
    grouped.set(key, current);
  });
  return [...grouped.entries()]
    .map(([timestamp, item]) => ({ timestamp, value: item.total / item.count }))
    .sort((a, b) => a.timestamp.localeCompare(b.timestamp));
}

function average(values: number[]) {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
}

function priceChangePct(points: SeriesPoint[]) {
  if (points.length < 2) return 0;
  const latest = points[points.length - 1].value;
  const previous = points[Math.max(0, points.length - 4)].value;
  if (!previous) return 0;
  return ((latest - previous) / previous) * 100;
}

function InputPriceChart({ history, forecast }: { history: SeriesPoint[]; forecast: AgriInputForecastPoint[] }) {
  const forecastSeries: SeriesPoint[] = forecast.map((point) => ({
    timestamp: point.timestamp,
    value: point.forecast_price_vnd,
    low: point.confidence_low_vnd,
    high: point.confidence_high_vnd
  }));
  const all = [...history, ...forecastSeries];
  const width = 920;
  const height = 320;
  const padding = { top: 28, right: 28, bottom: 42, left: 74 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const values = all.flatMap((point) => [point.value, point.low, point.high]).filter((value): value is number => typeof value === "number");
  const minValue = values.length ? Math.min(...values) * 0.97 : 0;
  const maxValue = values.length ? Math.max(...values) * 1.03 : 1;
  const span = Math.max(1, maxValue - minValue);

  function x(index: number, length: number) {
    if (length <= 1) return padding.left;
    return padding.left + (index / (length - 1)) * plotWidth;
  }

  function y(value: number) {
    return padding.top + (1 - (value - minValue) / span) * plotHeight;
  }

  function pointsPath(points: SeriesPoint[], startIndex = 0) {
    return points
      .map((point, index) => `${x(startIndex + index, Math.max(all.length, 2)).toFixed(2)},${y(point.value).toFixed(2)}`)
      .join(" ");
  }

  const forecastOffset = history.length ? history.length - 1 : 0;
  const forecastPoints = history.length ? [history[history.length - 1], ...forecastSeries] : forecastSeries;
  const forecastPath = forecastPoints
    .map((point, index) => {
      const globalIndex = forecastOffset + index;
      return `${x(globalIndex, Math.max(all.length, 2)).toFixed(2)},${y(point.value).toFixed(2)}`;
    })
    .join(" ");
  const gridValues = [0, 0.25, 0.5, 0.75, 1].map((ratio) => minValue + span * ratio);

  if (!all.length) {
    return <div className="input-chart-empty">Chưa có dữ liệu giá cho lựa chọn này.</div>;
  }

  return (
    <svg className="input-price-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Biểu đồ giá phân bón">
      {gridValues.map((value) => (
        <g key={value}>
          <line x1={padding.left} x2={width - padding.right} y1={y(value)} y2={y(value)} />
          <text x={padding.left - 12} y={y(value) + 4} textAnchor="end">
            {Math.round(value / 1000).toLocaleString("vi-VN")}k
          </text>
        </g>
      ))}
      {history.length ? <polyline className="input-history-line" points={pointsPath(history)} /> : null}
      {forecastSeries.length ? <polyline className="input-forecast-line" points={forecastPath} /> : null}
      {history.map((point, index) => (
        <circle key={`${point.timestamp}-${index}`} className="input-history-dot" cx={x(index, Math.max(all.length, 2))} cy={y(point.value)} r="4" />
      ))}
      {forecastSeries.map((point, index) => {
        const globalIndex = forecastOffset + index + 1;
        return (
          <circle
            key={`${point.timestamp}-${index}`}
            className="input-forecast-dot"
            cx={x(globalIndex, Math.max(all.length, 2))}
            cy={y(point.value)}
            r="3.5"
          />
        );
      })}
      <text x={padding.left} y={height - 12}>
        {history[0] ? formatDate(history[0].timestamp) : ""}
      </text>
      <text x={width - padding.right} y={height - 12} textAnchor="end">
        {forecastSeries.at(-1) ? formatDate(forecastSeries.at(-1)?.timestamp) : history.at(-1) ? formatDate(history.at(-1)?.timestamp) : ""}
      </text>
    </svg>
  );
}

export function InputPricesPage() {
  const [products, setProducts] = useState<AgriInputProduct[]>([]);
  const [latest, setLatest] = useState<AgriInputPricePoint[]>([]);
  const [history, setHistory] = useState<AgriInputPricePoint[]>([]);
  const [forecast, setForecast] = useState<AgriInputForecastPoint[]>([]);
  const [productSlug, setProductSlug] = useState("");
  const [province, setProvince] = useState("");
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    Promise.all([fetchAgriInputProducts(controller.signal), fetchAgriInputLatest({ signal: controller.signal })])
      .then(([productPayload, latestPayload]) => {
        setProducts(productPayload);
        setLatest(latestPayload);
        const preferredLatest = latestPayload.find((row) => row.data_kind === "scraped") ?? latestPayload[0];
        setProductSlug((current) => current || preferredLatest?.product_slug || productPayload[0]?.slug || "");
        const provinces = [...new Set(latestPayload.map((row) => row.province))].sort(COLLATOR.compare);
        setProvince((current) => current || preferredLatest?.province || provinces[0] || "");
      })
      .catch((err) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Không tải được dữ liệu giá phân bón.");
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!productSlug) return;
    const controller = new AbortController();
    setDetailLoading(true);
    setError(null);
    Promise.all([
      fetchAgriInputHistory(productSlug, { province: province || undefined, months: 12, signal: controller.signal }),
      fetchAgriInputForecast(productSlug, { province: province || undefined, days: 30, signal: controller.signal }),
      fetchAgriInputLatest({ productSlug, province: province || undefined, signal: controller.signal })
    ])
      .then(([historyPayload, forecastPayload, latestPayload]) => {
        setHistory(historyPayload);
        setForecast(forecastPayload);
        setLatest((current) => {
          const remaining = current.filter((row) =>
            province ? row.product_slug !== productSlug || row.province !== province : row.product_slug !== productSlug
          );
          return [...latestPayload, ...remaining];
        });
      })
      .catch((err) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Không tải được dữ liệu chi tiết.");
      })
      .finally(() => setDetailLoading(false));
    return () => controller.abort();
  }, [productSlug, province]);

  const selectedProduct = products.find((product) => product.slug === productSlug) ?? products[0];
  const provinceOptions = useMemo(() => [...new Set(latest.map((row) => row.province))].sort(COLLATOR.compare), [latest]);
  const productOptions = useMemo(() => [...products].sort((a, b) => COLLATOR.compare(a.name, b.name)), [products]);
  const comparisonRows = useMemo(
    () =>
      latest
        .filter((row) => row.product_slug === productSlug && (!province || row.province === province))
        .sort((a, b) => (a.package_price_vnd ?? 0) - (b.package_price_vnd ?? 0)),
    [latest, productSlug, province]
  );
  const latestSelected = comparisonRows[0];
  const historySeries = useMemo(() => aggregateHistory(history), [history]);
  const changePct = priceChangePct(historySeries);
  const avgLatestPackage = average(comparisonRows.map((row) => row.package_price_vnd ?? 0).filter(Boolean));
  const avgLatestKg = average(comparisonRows.map((row) => row.normalized_price_vnd).filter(Boolean));
  const forecastLast = forecast.at(-1);
  const productCount = products.length;
  const provinceCount = provinceOptions.length;

  return (
    <section className="input-prices-page">
      <SeoHead
        title="Giá phân bón hôm nay & dự báo vật tư đầu vào"
        description="Theo dõi giá phân bón theo vùng giá, thương hiệu và quy cách bao 50 kg. Xem bảng giá, so sánh thương hiệu, lịch sử 12 tháng và dự báo ngắn hạn."
        canonical="/du-bao-gia/phan-bon"
        schemaJsonLd={{
          "@context": "https://schema.org",
          "@type": "Dataset",
          name: "Giá phân bón đầu vào Việt Nam",
          description: "Bảng giá phân bón theo sản phẩm, vùng giá, thương hiệu, quy cách bao và giá quy đổi VND/kg.",
          url: "https://dubaonongsan.com/du-bao-gia/phan-bon",
          creator: { "@type": "Organization", name: "dubaonongsan.com" }
        }}
      />

      <header className="input-price-hero">
        <div>
          <span className="input-price-kicker">
            <PackageCheck size={18} />
            Giá vật tư đầu vào
          </span>
          <h1>Giá phân bón hôm nay</h1>
          <p>
            <span>Theo dõi giá bao, giá quy đổi VND/kg.</span>
            <span>Theo vùng giá và thương hiệu.</span>
          </p>
        </div>
        <div className="input-price-head-metrics" aria-label="Tổng quan dữ liệu">
          <div>
            <span>Sản phẩm</span>
            <strong>{productCount}</strong>
          </div>
          <div>
            <span>Vùng giá</span>
            <strong>{provinceCount}</strong>
          </div>
          <div>
            <span>Cập nhật</span>
            <strong>{formatDate(latestSelected?.observed_at)}</strong>
          </div>
        </div>
      </header>

      <section className="input-price-controls">
        <div className="input-filter-group">
          <Filter size={18} />
          <label>
            Sản phẩm
            <select value={productSlug} onChange={(event) => setProductSlug(event.target.value)} disabled={!productOptions.length}>
              {productOptions.map((product) => (
                <option key={product.slug} value={product.slug}>
                  {product.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Vùng giá
            <select value={province} onChange={(event) => setProvince(event.target.value)} disabled={!provinceOptions.length}>
              {provinceOptions.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
        </div>
        <button type="button" onClick={() => window.location.reload()} disabled={loading || detailLoading}>
          <RefreshCw size={16} />
          {loading || detailLoading ? "Đang tải" : "Làm mới"}
        </button>
      </section>

      {error ? <div className="input-price-error">{error}</div> : null}

      <section className="input-stat-grid">
        <div className="input-stat">
          <Database size={18} />
          <span>Giá trung bình/bao</span>
          <strong>{formatVnd(avgLatestPackage || latestSelected?.package_price_vnd)}</strong>
          <small>{selectedProduct?.package_label ?? "Bao"}</small>
        </div>
        <div className="input-stat">
          <BarChart3 size={18} />
          <span>Giá quy đổi</span>
          <strong>{formatVnd(avgLatestKg || latestSelected?.normalized_price_vnd)}</strong>
          <small>VND/kg</small>
        </div>
        <div className="input-stat">
          <TrendingUp size={18} />
          <span>Biến động 3 tháng</span>
          <strong className={changePct >= 0 ? "positive" : "negative"}>
            {changePct >= 0 ? "+" : ""}
            {changePct.toFixed(2)}%
          </strong>
          <small>{province || "Toàn bộ vùng"}</small>
        </div>
        <div className="input-stat">
          <Activity size={18} />
          <span>Dự báo 30 ngày</span>
          <strong>{formatVnd(forecastLast?.forecast_price_vnd)}</strong>
          <small>{forecastLast?.model_kind ?? "input-price-baseline-v1"}</small>
        </div>
      </section>

      <section className="input-chart-section">
        <div className="input-section-heading">
          <div>
            <h2>Lịch sử 12 tháng và dự báo ngắn hạn</h2>
            <p>{selectedProduct ? `${selectedProduct.name} tại ${province || "các vùng giá theo dõi"}` : "Đang tải sản phẩm"}</p>
          </div>
          <div className="input-chart-legend">
            <span className="history">Lịch sử</span>
            <span className="forecast">Dự báo</span>
          </div>
        </div>
        <InputPriceChart history={historySeries} forecast={forecast} />
      </section>

      <section className="input-price-grid">
        <div className="input-price-panel">
          <div className="input-section-heading compact">
            <h2>So sánh thương hiệu</h2>
            <p>{comparisonRows.length} báo giá mới nhất</p>
          </div>
          <div className="input-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Thương hiệu</th>
                  <th>Giá bao</th>
                  <th>VND/kg</th>
                  <th>Nguồn</th>
                </tr>
              </thead>
              <tbody>
                {comparisonRows.map((row) => (
                  <tr key={row.observation_id}>
                    <td>{row.brand ?? "Chưa rõ"}</td>
                    <td>{formatVnd(row.package_price_vnd)}</td>
                    <td>{formatVnd(row.normalized_price_vnd)}</td>
                    <td>{row.source_name}</td>
                  </tr>
                ))}
                {!comparisonRows.length ? (
                  <tr>
                    <td colSpan={4}>Chưa có dữ liệu cho lựa chọn này.</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </div>

        <div className="input-price-panel">
          <div className="input-section-heading compact">
            <h2>Danh mục đang theo dõi</h2>
            <p>Chuẩn hóa theo sản phẩm và quy cách</p>
          </div>
          <div className="input-product-list">
            {products.map((product) => (
              <button
                key={product.slug}
                type="button"
                className={product.slug === productSlug ? "active" : ""}
                onClick={() => setProductSlug(product.slug)}
              >
                <strong>{product.name}</strong>
                <span>{product.nutrient_profile ?? product.product_type}</span>
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="input-price-panel input-price-data">
        <div className="input-section-heading compact">
          <h2>Bảng giá mới nhất</h2>
          <p>Giá bao và giá quy đổi theo kg</p>
        </div>
        <div className="input-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Vùng giá</th>
                <th>Sản phẩm</th>
                <th>Thương hiệu</th>
                <th>Quy cách</th>
                <th>Giá bao</th>
                <th>VND/kg</th>
                <th>Ngày</th>
              </tr>
            </thead>
            <tbody>
              {latest.slice(0, 80).map((row) => (
                <tr key={row.observation_id}>
                  <td>{row.province}</td>
                  <td>{row.product_name}</td>
                  <td>{row.brand ?? "Chưa rõ"}</td>
                  <td>{row.package_label ?? `${row.package_size_kg ?? ""} kg`}</td>
                  <td>{formatVnd(row.package_price_vnd)}</td>
                  <td>{formatVnd(row.normalized_price_vnd)}</td>
                  <td>{formatDate(row.observed_at)}</td>
                </tr>
              ))}
              {!latest.length && !loading ? (
                <tr>
                  <td colSpan={7}>Chưa có dữ liệu giá phân bón.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      <section className="input-price-note">
        <strong>Ghi chú dữ liệu</strong>
        <p>
          Giá phân bón được tách thành lớp dữ liệu riêng để chuẩn hóa sản phẩm, vùng giá, thương hiệu và quy cách bao. Các dòng có nguồn
          công khai như vietnga.vn là dữ liệu đã crawl; các dòng “Dữ liệu tham chiếu nền” chỉ dùng làm nền khi nguồn thật chưa có đủ lịch sử.
        </p>
      </section>
    </section>
  );
}
