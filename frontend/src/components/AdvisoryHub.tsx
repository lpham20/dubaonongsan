import { useEffect, useMemo, useState } from "react";
import { BarChart3, Calculator, GitCompareArrows, Leaf, RefreshCw, Sprout } from "./icons";
import { FertilizerAdvisor } from "./FertilizerAdvisor";
import { SeoHead } from "./SeoHead";
import {
  fetchArbitrage,
  fetchRegions,
  postCrossCommodity,
  postSellingTime,
  type ArbitrageResponse,
  type CropType,
  type CrossCommodityResponse,
  type Region,
  type SellingTimeResponse
} from "../lib/api";

export type AdvisoryTool = "fertilizer" | "sellingTime" | "arbitrage" | "crossCrop";

const toolMeta: Record<AdvisoryTool, { kicker: string; title: string; description: string; canonical: string; Icon: typeof Calculator }> = {
  fertilizer: {
    kicker: "Khuyến nghị",
    title: "Khuyến nghị bón phân",
    description: "Tính khuyến nghị bón phân theo cây trồng, vùng sản xuất, giai đoạn sinh trưởng và dữ liệu anh tự nhập.",
    canonical: "/khuyen-nghi-bon-phan",
    Icon: Leaf
  },
  sellingTime: {
    kicker: "Thời điểm bán",
    title: "Chọn ngày bán theo dự báo giá",
    description: "Xếp hạng các ngày bán tốt nhất trong 30 ngày tới theo dự báo giá nông sản và chi phí lưu kho.",
    canonical: "/thoi-diem-ban",
    Icon: BarChart3
  },
  arbitrage: {
    kicker: "Chênh lệch vùng",
    title: "Quét chênh lệch giá theo tỉnh",
    description: "So nhanh các cặp tỉnh có giá mua và giá bán chênh lệch sau khi trừ chi phí vận chuyển ước tính.",
    canonical: "/chenh-lech-vung",
    Icon: GitCompareArrows
  },
  crossCrop: {
    kicker: "So sánh cây trồng",
    title: "So sánh lợi nhuận theo cây và tỉnh",
    description: "Ước tính lợi nhuận tham khảo giữa sầu riêng, cà phê, hồ tiêu và lúa theo giá, năng suất và độ phù hợp của tỉnh.",
    canonical: "/so-sanh-cay-trong",
    Icon: Sprout
  }
};

const cropOptions: { value: CropType | ""; label: string }[] = [
  { value: "", label: "Tất cả" },
  { value: "sau_rieng", label: "Sầu riêng" },
  { value: "ca_phe", label: "Cà phê" },
  { value: "ho_tieu", label: "Hồ tiêu" },
  { value: "lua", label: "Lúa" }
];

function formatVnd(value: number) {
  return `${Math.round(value).toLocaleString("vi-VN")} đ`;
}

function regionLabel(region: Region) {
  return region.province ?? region.region_name;
}

export function AdvisoryHub({
  authToken,
  onRequireAuth,
  tool = "fertilizer"
}: {
  authToken: string | null;
  onRequireAuth: () => void;
  tool?: AdvisoryTool;
}) {
  const meta = toolMeta[tool];
  const ToolIcon = meta.Icon;

  return (
    <section className="advisory-page">
      {tool !== "fertilizer" ? (
        <>
          <SeoHead
            title={meta.title}
            description={meta.description}
            canonical={meta.canonical}
          />
          <header className="advisory-hero">
            <span><ToolIcon size={17} /> {meta.kicker}</span>
            <h1>{meta.title}</h1>
            <p>{meta.description}</p>
          </header>
        </>
      ) : null}

      <div className={tool === "fertilizer" ? "advisory-content advisory-content--flush" : "advisory-content"}>
        {tool === "fertilizer" ? <FertilizerAdvisor authToken={authToken} onRequireAuth={onRequireAuth} /> : null}
        {tool === "sellingTime" ? <SellingTimePanel /> : null}
        {tool === "arbitrage" ? <ArbitragePanel /> : null}
        {tool === "crossCrop" ? <CrossCropPanel /> : null}
      </div>
    </section>
  );
}

function SellingTimePanel() {
  const [crop, setCrop] = useState<CropType>("sau_rieng");
  const [regions, setRegions] = useState<Region[]>([]);
  const [regionId, setRegionId] = useState<number | "">("");
  const [quantity, setQuantity] = useState(1000);
  const [storageCost, setStorageCost] = useState(0);
  const [result, setResult] = useState<SellingTimeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetchRegions(crop, controller.signal)
      .then((items) => {
        setRegions(items);
        setRegionId(items[0]?.region_id || "");
      })
      .catch(() => setRegions([]));
    return () => controller.abort();
  }, [crop]);

  function submit() {
    setLoading(true);
    setError(null);
    postSellingTime({ crop, region_id: typeof regionId === "number" ? regionId : null, quantity_kg: quantity, storage_cost_vnd_per_kg_per_day: storageCost })
      .then(setResult)
      .catch((err) => setError(err instanceof Error ? err.message : "Không tính được thời điểm bán."))
      .finally(() => setLoading(false));
  }

  return (
    <section className="advisory-tool">
      <div className="advisory-tool-head">
        <h2>Thời điểm bán nông sản</h2>
        <p>Xếp hạng 5 ngày bán tốt nhất trong 30 ngày theo dự báo giá nông sản và chi phí lưu kho.</p>
      </div>
      {error ? <div className="input-price-error">{error}</div> : null}
      <div className="advisory-form-row">
        <label>
          Cây trồng
          <select value={crop} onChange={(event) => setCrop(event.target.value as CropType)}>
            {cropOptions.filter((item) => item.value).map((item) => (
              <option key={item.value} value={item.value}>{item.label}</option>
            ))}
          </select>
        </label>
        <label>
          Tỉnh/vùng trồng
          <select value={regionId} onChange={(event) => setRegionId(Number(event.target.value) || "")}>
            {regions.map((region) => (
              <option key={region.region_id} value={region.region_id}>{regionLabel(region)}</option>
            ))}
          </select>
        </label>
        <label>
          Số lượng (kg)
          <input type="number" min="1" value={quantity} onChange={(event) => setQuantity(Number(event.target.value))} />
        </label>
        <label>
          Lưu kho đ/kg/ngày
          <input type="number" min="0" value={storageCost} onChange={(event) => setStorageCost(Number(event.target.value))} />
        </label>
        <button type="button" className="roi-primary-button" onClick={submit} disabled={loading}>
          <RefreshCw size={16} />
          {loading ? "Đang tính" : "Tính thời điểm bán"}
        </button>
      </div>
      {result ? (
        <div className="advisory-result-grid">
          <article className="advisory-highlight">
            <span>Ngày tốt nhất</span>
            <strong>{new Date(result.best_window.date).toLocaleDateString("vi-VN")}</strong>
            <small>{result.best_window.uplift_pct_vs_today > 0 ? "+" : ""}{result.best_window.uplift_pct_vs_today}% so với hôm nay</small>
          </article>
          {result.top_5_windows.map((item) => (
            <article key={item.date}>
              <span>{new Date(item.date).toLocaleDateString("vi-VN")}</span>
              <strong>{formatVnd(item.forecast_price_vnd_per_kg)}/kg</strong>
              <small>Doanh thu ròng {formatVnd(item.net_revenue_vnd)}</small>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function ArbitragePanel() {
  const [crop, setCrop] = useState<CropType | "">("");
  const [result, setResult] = useState<ArbitrageResponse | null>(null);
  const [loading, setLoading] = useState(false);

  function load() {
    setLoading(true);
    fetchArbitrage({ crop })
      .then(setResult)
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  return (
    <section className="advisory-tool">
      <div className="advisory-tool-head">
        <h2>Chênh lệch vùng giá</h2>
        <p>Lọc các cặp tỉnh có chênh lệch giá sau chi phí vận chuyển ước tính.</p>
      </div>
      <div className="advisory-form-row compact">
        <label>
          Cây trồng
          <select value={crop} onChange={(event) => setCrop(event.target.value as CropType | "")}>
            {cropOptions.map((item) => (
              <option key={item.value || "all"} value={item.value}>{item.label}</option>
            ))}
          </select>
        </label>
        <button type="button" className="roi-primary-button" onClick={load} disabled={loading}>
          {loading ? "Đang quét" : "Quét chênh lệch"}
        </button>
      </div>
      <div className="input-table-wrap advisory-table">
        <table>
          <thead>
            <tr>
              <th>Cây</th>
              <th>Tỉnh giá thấp</th>
              <th>Tỉnh giá cao</th>
              <th>Chênh lệch ròng</th>
              <th>%</th>
            </tr>
          </thead>
          <tbody>
            {(result?.items ?? []).map((item) => (
              <tr key={`${item.crop}-${item.from_region}-${item.to_region}`}>
                <td>{item.crop_label_vi}</td>
                <td>{item.from_region}</td>
                <td>{item.to_region}</td>
                <td>{formatVnd(item.net_spread_vnd_per_kg)}/kg</td>
                <td>{item.net_spread_pct.toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {result ? <p className="advisory-disclaimer">{result.assumption_vi}</p> : null}
    </section>
  );
}

function CrossCropPanel() {
  const [regions, setRegions] = useState<Region[]>([]);
  const [regionId, setRegionId] = useState<number | "">("");
  const [area, setArea] = useState(1);
  const [result, setResult] = useState<CrossCommodityResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const maxProfit = useMemo(() => Math.max(1, ...(result?.items.map((item) => Math.abs(item.estimated_profit_vnd)) ?? [1])), [result]);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all(cropOptions.filter((item): item is { value: CropType; label: string } => Boolean(item.value)).map((item) => fetchRegions(item.value, controller.signal)))
      .then((groups) => {
        const byProvince = new Map<string, Region>();
        groups.flat().forEach((region) => {
          const key = region.province ?? region.region_name;
          if (!byProvince.has(key)) byProvince.set(key, region);
        });
        const items = [...byProvince.values()].sort((a, b) => regionLabel(a).localeCompare(regionLabel(b), "vi-VN"));
        setRegions(items);
        setRegionId((current) => current || items[0]?.region_id || "");
      })
      .catch(() => setRegions([]));
    return () => controller.abort();
  }, []);

  function submit() {
    if (!regionId) return;
    setLoading(true);
    setError(null);
    postCrossCommodity({ region_id: Number(regionId), area_hectares: area })
      .then(setResult)
      .catch((err) => setError(err instanceof Error ? err.message : "Không so sánh được cây trồng."))
      .finally(() => setLoading(false));
  }

  return (
    <section className="advisory-tool">
      <div className="advisory-tool-head">
        <h2>So sánh cây trồng</h2>
        <p>So nhanh lợi nhuận tham khảo giữa 4 cây theo giá, năng suất và độ phù hợp của tỉnh.</p>
      </div>
      {error ? <div className="input-price-error">{error}</div> : null}
      <div className="advisory-form-row compact">
        <label>
          Tỉnh/vùng trồng
          <select value={regionId} onChange={(event) => setRegionId(Number(event.target.value) || "")}>
            {regions.map((region) => (
              <option key={region.region_id} value={region.region_id}>{regionLabel(region)}</option>
            ))}
          </select>
        </label>
        <label>
          Diện tích (ha)
          <input type="number" min="0.1" step="0.1" value={area} onChange={(event) => setArea(Number(event.target.value))} />
        </label>
        <button type="button" className="roi-primary-button" onClick={submit} disabled={loading}>
          {loading ? "Đang so sánh" : "So sánh"}
        </button>
      </div>
      {result ? (
        <>
          <p className="advisory-context">Tỉnh đang so sánh: <strong>{result.province ?? result.region_name}</strong></p>
          <div className="cross-crop-bars">
            {result.items.map((item) => (
              <article key={item.crop}>
                <div>
                  <span>{item.crop_label_vi}</span>
                  <strong>{formatVnd(item.estimated_profit_vnd)}</strong>
                </div>
                <i style={{ width: `${Math.max(8, (Math.abs(item.estimated_profit_vnd) / maxProfit) * 100)}%` }} />
                <small>Độ phù hợp {Math.round(item.suitability_score * 100)}% · Tỷ suất lợi nhuận {item.roi_score.toFixed(1)}%</small>
              </article>
            ))}
          </div>
          <div className="advisory-disclaimer">
            {result.intercropping_vi.map((note) => <p key={note}>{note}</p>)}
            <p>{result.disclaimer_vi}</p>
          </div>
        </>
      ) : null}
    </section>
  );
}
