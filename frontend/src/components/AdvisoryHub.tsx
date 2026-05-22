import { useEffect, useMemo, useState } from "react";
import { BarChart3, Calculator, GitCompareArrows, Leaf, RefreshCw, Sprout } from "./icons";
import { FertilizerAdvisor } from "./FertilizerAdvisor";
import { RoiCalculatorPage } from "./RoiCalculatorPage";
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

type AdvisoryTab = "fertilizer" | "roi" | "sellingTime" | "arbitrage" | "crossCrop";

const tabs: { value: AdvisoryTab; label: string; Icon: typeof Calculator }[] = [
  { value: "fertilizer", label: "Bón phân", Icon: Leaf },
  { value: "roi", label: "ROI", Icon: Calculator },
  { value: "sellingTime", label: "Thời điểm bán", Icon: BarChart3 },
  { value: "arbitrage", label: "Chênh lệch vùng", Icon: GitCompareArrows },
  { value: "crossCrop", label: "So sánh cây trồng", Icon: Sprout }
];

const cropOptions: { value: CropType | ""; label: string }[] = [
  { value: "", label: "Tất cả" },
  { value: "sau_rieng", label: "Sầu riêng" },
  { value: "ca_phe", label: "Cà phê" },
  { value: "ho_tieu", label: "Hồ tiêu" },
  { value: "lua", label: "Lúa" }
];

function initialTab(): AdvisoryTab {
  const tab = new URLSearchParams(window.location.search).get("tab") as AdvisoryTab | null;
  return tab && tabs.some((item) => item.value === tab) ? tab : "fertilizer";
}

function formatVnd(value: number) {
  return `${Math.round(value).toLocaleString("vi-VN")} đ`;
}

export function AdvisoryHub({ authToken, onRequireAuth }: { authToken: string | null; onRequireAuth: () => void }) {
  const [activeTab, setActiveTab] = useState<AdvisoryTab>(initialTab);

  function openTab(next: AdvisoryTab) {
    setActiveTab(next);
    const params = new URLSearchParams(window.location.search);
    params.set("tab", next);
    window.history.replaceState(null, "", `${window.location.pathname}?${params.toString()}`);
  }

  return (
    <section className="advisory-page">
      <SeoHead
        title="Khuyến nghị nông vụ"
        description="Bón phân, ROI, thời điểm bán, chênh lệch vùng và so sánh cây trồng trên cùng một tab khuyến nghị."
        canonical="/khuyen-nghi-bon-phan"
      />
      <header className="advisory-hero">
        <span>Khuyến nghị</span>
        <h1>Ra quyết định nông vụ bằng số liệu</h1>
        <p>Tab này gom bón phân, ROI, thời điểm bán và tín hiệu vùng giá. Phần phân bón thế giới vẫn nằm ở trang giá phân bón theo đúng spec.</p>
      </header>

      <div className="advisory-tabs" role="tablist" aria-label="Các công cụ khuyến nghị">
        {tabs.map(({ value, label, Icon }) => (
          <button key={value} type="button" className={activeTab === value ? "active" : ""} onClick={() => openTab(value)}>
            <Icon size={17} />
            {label}
          </button>
        ))}
      </div>

      <div className="advisory-content">
        {activeTab === "fertilizer" ? <FertilizerAdvisor authToken={authToken} onRequireAuth={onRequireAuth} /> : null}
        {activeTab === "roi" ? <RoiCalculatorPage authToken={authToken} onRequireAuth={onRequireAuth} embedded /> : null}
        {activeTab === "sellingTime" ? <SellingTimePanel /> : null}
        {activeTab === "arbitrage" ? <ArbitragePanel /> : null}
        {activeTab === "crossCrop" ? <CrossCropPanel /> : null}
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
        <p>Xếp hạng 5 ngày bán tốt nhất trong 30 ngày theo forecast giá nông sản và chi phí lưu kho.</p>
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
          Vùng
          <select value={regionId} onChange={(event) => setRegionId(Number(event.target.value) || "")}>
            {regions.map((region) => (
              <option key={region.region_id} value={region.region_id}>{region.region_name}</option>
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
        <p>Lọc các cặp vùng có spread sau chi phí vận chuyển ước tính.</p>
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
              <th>Từ vùng</th>
              <th>Đến vùng</th>
              <th>Net spread</th>
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
  const maxProfit = useMemo(() => Math.max(1, ...(result?.items.map((item) => Math.abs(item.estimated_profit_vnd)) ?? [1])), [result]);

  useEffect(() => {
    const controller = new AbortController();
    fetchRegions("sau_rieng", controller.signal)
      .then((items) => {
        setRegions(items);
        setRegionId(items[0]?.region_id || "");
      })
      .catch(() => setRegions([]));
    return () => controller.abort();
  }, []);

  function submit() {
    if (!regionId) return;
    postCrossCommodity({ region_id: Number(regionId), area_hectares: area }).then(setResult);
  }

  return (
    <section className="advisory-tool">
      <div className="advisory-tool-head">
        <h2>So sánh cây trồng</h2>
        <p>So nhanh lợi nhuận tham khảo giữa 4 cây, có tính suitability vùng.</p>
      </div>
      <div className="advisory-form-row compact">
        <label>
          Vùng
          <select value={regionId} onChange={(event) => setRegionId(Number(event.target.value) || "")}>
            {regions.map((region) => (
              <option key={region.region_id} value={region.region_id}>{region.region_name} - {region.province}</option>
            ))}
          </select>
        </label>
        <label>
          Diện tích (ha)
          <input type="number" min="0.1" step="0.1" value={area} onChange={(event) => setArea(Number(event.target.value))} />
        </label>
        <button type="button" className="roi-primary-button" onClick={submit}>So sánh</button>
      </div>
      {result ? (
        <>
          <div className="cross-crop-bars">
            {result.items.map((item) => (
              <article key={item.crop}>
                <div>
                  <span>{item.crop_label_vi}</span>
                  <strong>{formatVnd(item.estimated_profit_vnd)}</strong>
                </div>
                <i style={{ width: `${Math.max(8, (Math.abs(item.estimated_profit_vnd) / maxProfit) * 100)}%` }} />
                <small>Suitability {Math.round(item.suitability_score * 100)}% · ROI score {item.roi_score.toFixed(1)}%</small>
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
