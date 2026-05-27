import { useEffect, useMemo, useRef, useState } from "react";
import { BarChart3, Calculator, GitCompareArrows, Leaf, RefreshCw, ShieldCheck, Sprout } from "./icons";
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
import { useLanguage, type AppLanguage } from "../contexts/LanguageContext";
import { cropLabel, displayProvince } from "../lib/displayLabels";
import { MARKET_CROP_OPTIONS } from "../lib/cropOptions";
import { decimalInputValue, parseDecimalInput } from "../lib/numberInput";
import { messageFromError } from "../lib/errorMessages";

const toolMeta: Record<AppLanguage, Record<AdvisoryTool, { kicker: string; title: string; description: string; canonical: string; Icon: typeof Calculator }>> = {
  vi: {
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
  },
  en: {
    fertilizer: {
      kicker: "Advisory",
      title: "Fertilizer recommendation",
      description: "Calculate crop-specific fertilizer recommendations from production area, crop stage and field data you enter.",
      canonical: "/khuyen-nghi-bon-phan",
      Icon: Leaf
    },
    sellingTime: {
      kicker: "Selling timing",
      title: "Choose a selling window from the price forecast",
      description: "Rank the best selling days in the next 30 days using crop price forecasts and storage costs.",
      canonical: "/thoi-diem-ban",
      Icon: BarChart3
    },
    arbitrage: {
      kicker: "Regional spread",
      title: "Scan crop price spreads by province",
      description: "Compare low-price and high-price provinces after estimated transport costs.",
      canonical: "/chenh-lech-vung",
      Icon: GitCompareArrows
    },
    crossCrop: {
      kicker: "Crop comparison",
      title: "Compare farm profit by crop and province",
      description: "Estimate reference profit across durian, coffee, pepper and rice using price, yield and province suitability.",
      canonical: "/so-sanh-cay-trong",
      Icon: Sprout
    }
  }
};

export type AdvisoryTool = "fertilizer" | "sellingTime" | "arbitrage" | "crossCrop";

function formatVnd(value: number, language: AppLanguage = "vi") {
  return `${Math.round(value).toLocaleString(language === "en" ? "en-US" : "vi-VN")} VND`;
}

function regionLabel(region: Region) {
  return displayProvince(region.province, region.region_name);
}

function concreteCropOptions() {
  return MARKET_CROP_OPTIONS.filter((item): item is { value: CropType } => Boolean(item.value));
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
  const { language } = useLanguage();
  const meta = toolMeta[language][tool];
  const ToolIcon = meta.Icon;
  const locked = !authToken;
  const activeAuthToken = authToken ?? "";
  const pageClassName = tool === "fertilizer"
    ? "advisory-page"
    : "advisory-page fertilizer-page roi-standard-page advisory-standard-page";

  return (
    <section className={pageClassName}>
      {tool !== "fertilizer" ? (
        <>
          <SeoHead
            title={meta.title}
            description={meta.description}
            canonical={meta.canonical}
          />
          <header className="fertilizer-hero roi-hero advisory-standard-hero">
            <div className="roi-hero-copy">
              <span className="input-price-kicker"><ToolIcon size={17} /> {meta.kicker}</span>
              <h1>{meta.title}</h1>
              <p>{meta.description}</p>
            </div>
          </header>
        </>
      ) : null}

      <div className={tool === "fertilizer" ? "advisory-content advisory-content--flush" : "advisory-content advisory-standard-content"}>
        {locked ? <AdvisoryAccountGate onRequireAuth={onRequireAuth} /> : null}
        {!locked && tool === "fertilizer" ? <FertilizerAdvisor authToken={authToken} onRequireAuth={onRequireAuth} /> : null}
        {!locked && tool === "sellingTime" ? <SellingTimePanel authToken={activeAuthToken} /> : null}
        {!locked && tool === "arbitrage" ? <ArbitragePanel authToken={activeAuthToken} /> : null}
        {!locked && tool === "crossCrop" ? <CrossCropPanel authToken={activeAuthToken} /> : null}
      </div>
    </section>
  );
}

function AdvisoryAccountGate({ onRequireAuth }: { onRequireAuth: () => void }) {
  const { language } = useLanguage();
  return (
    <section className="input-price-panel roi-panel advisory-auth-gate">
      <div className="input-section-heading compact roi-section-heading">
        <h2><ShieldCheck size={18} /> {language === "en" ? "Account required" : "Cần tài khoản để sử dụng"}</h2>
        <p>{language === "en" ? "Log in or create an account to use this tool and save your work sessions." : "Đăng nhập hoặc đăng ký để mở công cụ tính toán và lưu phiên làm việc."}</p>
      </div>
      <div className="advisory-auth-gate-body">
        <p>{language === "en" ? "These decision tools use forecast and regional data, so an account helps keep calculations traceable and saved to the right workspace." : "Các công cụ quyết định dùng dữ liệu dự báo và dữ liệu vùng, nên hệ thống yêu cầu tài khoản để kiểm soát phiên tính và lịch sử sử dụng."}</p>
        <button type="button" className="roi-primary-button" onClick={onRequireAuth}>
          {language === "en" ? "Log in / register" : "Đăng nhập / đăng ký"}
        </button>
      </div>
    </section>
  );
}

function SellingTimePanel({ authToken }: { authToken: string }) {
  const { language } = useLanguage();
  const [crop, setCrop] = useState<CropType>("sau_rieng");
  const [regions, setRegions] = useState<Region[]>([]);
  const [regionId, setRegionId] = useState<number | "">("");
  const [quantity, setQuantity] = useState("1000");
  const [storageCost, setStorageCost] = useState("0");
  const [result, setResult] = useState<SellingTimeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const submitControllerRef = useRef<AbortController | null>(null);

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

  useEffect(() => () => submitControllerRef.current?.abort(), []);

  function submit() {
    const safeQuantity = Math.max(1, parseDecimalInput(quantity) ?? 0);
    const safeStorageCost = Math.max(0, parseDecimalInput(storageCost) ?? 0);
    setQuantity(String(safeQuantity));
    setStorageCost(String(safeStorageCost));
    submitControllerRef.current?.abort();
    const controller = new AbortController();
    submitControllerRef.current = controller;
    setLoading(true);
    setError(null);
    postSellingTime(authToken, { crop, region_id: typeof regionId === "number" ? regionId : null, quantity_kg: safeQuantity, storage_cost_vnd_per_kg_per_day: safeStorageCost }, controller.signal)
      .then(setResult, (err) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        throw err;
      })
      .catch((err) => setError(messageFromError(err, language === "en" ? "Could not calculate the selling window." : "Không tính được thời điểm bán.")))
      .finally(() => {
        if (submitControllerRef.current === controller) {
          submitControllerRef.current = null;
          setLoading(false);
        }
      });
  }

  return (
    <section className="advisory-tool">
      <div className="advisory-tool-head">
        <h2>{language === "en" ? "Crop selling timing" : "Thời điểm bán nông sản"}</h2>
        <p>{language === "en" ? "Rank the five strongest selling windows in the next 30 days using price forecasts and storage costs." : "Xếp hạng 5 ngày bán tốt nhất trong 30 ngày theo dự báo giá nông sản và chi phí lưu kho."}</p>
      </div>
      {error ? <div className="input-price-error">{error}</div> : null}
      <div className="advisory-form-row">
        <label>
          {language === "en" ? "Crop" : "Cây trồng"}
          <select value={crop} onChange={(event) => setCrop(event.target.value as CropType)}>
            {concreteCropOptions().map((item) => (
              <option key={item.value} value={item.value}>{cropLabel(item.value, language)}</option>
            ))}
          </select>
        </label>
        <label>
          {language === "en" ? "Province/production area" : "Tỉnh/vùng trồng"}
          <select value={regionId} onChange={(event) => setRegionId(Number(event.target.value) || "")}>
            {regions.map((region) => (
              <option key={region.region_id} value={region.region_id}>{regionLabel(region)}</option>
            ))}
          </select>
        </label>
        <label>
          {language === "en" ? "Quantity (kg)" : "Số lượng (kg)"}
          <input inputMode="numeric" value={quantity} onChange={(event) => setQuantity(decimalInputValue(event.target.value))} />
        </label>
        <label>
          {language === "en" ? "Storage cost VND/kg/day" : "Lưu kho đ/kg/ngày"}
          <input inputMode="numeric" value={storageCost} onChange={(event) => setStorageCost(decimalInputValue(event.target.value))} />
        </label>
        <button type="button" className="roi-primary-button" onClick={submit} disabled={loading}>
          <RefreshCw size={16} />
          {loading ? (language === "en" ? "Calculating" : "Đang tính") : (language === "en" ? "Calculate selling window" : "Tính thời điểm bán")}
        </button>
      </div>
      {result ? (
        <div className="advisory-result-grid">
          <article className="advisory-highlight">
            <span>{language === "en" ? "Best day" : "Ngày tốt nhất"}</span>
            <strong>{new Date(result.best_window.date).toLocaleDateString(language === "en" ? "en-US" : "vi-VN")}</strong>
            <small>{result.best_window.uplift_pct_vs_today > 0 ? "+" : ""}{result.best_window.uplift_pct_vs_today}% {language === "en" ? "vs today" : "so với hôm nay"}</small>
          </article>
          {result.top_5_windows.map((item) => (
            <article key={item.date}>
              <span>{new Date(item.date).toLocaleDateString(language === "en" ? "en-US" : "vi-VN")}</span>
              <strong>{formatVnd(item.forecast_price_vnd_per_kg, language)}/kg</strong>
              <small>{language === "en" ? "Net revenue" : "Doanh thu ròng"} {formatVnd(item.net_revenue_vnd, language)}</small>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function ArbitragePanel({ authToken }: { authToken: string }) {
  const { language } = useLanguage();
  const [crop, setCrop] = useState<CropType | "">("");
  const [result, setResult] = useState<ArbitrageResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const loadControllerRef = useRef<AbortController | null>(null);

  function load() {
    loadControllerRef.current?.abort();
    const controller = new AbortController();
    loadControllerRef.current = controller;
    setLoading(true);
    fetchArbitrage(authToken, { crop, signal: controller.signal })
      .then(setResult)
      .catch((err) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
      })
      .finally(() => {
        if (loadControllerRef.current === controller) {
          loadControllerRef.current = null;
          setLoading(false);
        }
      });
  }

  useEffect(() => {
    load();
    return () => loadControllerRef.current?.abort();
  }, []);

  return (
    <section className="advisory-tool">
      <div className="advisory-tool-head">
        <h2>{language === "en" ? "Regional price spread" : "Chênh lệch vùng giá"}</h2>
        <p>{language === "en" ? "Filter province pairs where the price spread remains positive after estimated transport cost." : "Lọc các cặp tỉnh có chênh lệch giá sau chi phí vận chuyển ước tính."}</p>
      </div>
      <div className="advisory-form-row compact">
        <label>
          {language === "en" ? "Crop" : "Cây trồng"}
          <select value={crop} onChange={(event) => setCrop(event.target.value as CropType | "")}>
            {MARKET_CROP_OPTIONS.map((item) => (
              <option key={item.value || "all"} value={item.value}>{cropLabel(item.value, language)}</option>
            ))}
          </select>
        </label>
        <button type="button" className="roi-primary-button" onClick={load} disabled={loading}>
          {loading ? (language === "en" ? "Scanning" : "Đang quét") : (language === "en" ? "Scan spreads" : "Quét chênh lệch")}
        </button>
      </div>
      <div className="input-table-wrap advisory-table">
        <table>
          <thead>
            <tr>
              <th>{language === "en" ? "Crop" : "Cây"}</th>
              <th>{language === "en" ? "Lower-price province" : "Tỉnh giá thấp"}</th>
              <th>{language === "en" ? "Higher-price province" : "Tỉnh giá cao"}</th>
              <th>{language === "en" ? "Net spread" : "Chênh lệch ròng"}</th>
              <th>%</th>
            </tr>
          </thead>
          <tbody>
            {(result?.items ?? []).map((item) => (
              <tr key={`${item.crop}-${item.from_region}-${item.to_region}`}>
                <td>{cropLabel(item.crop, language)}</td>
                <td>{item.from_region}</td>
                <td>{item.to_region}</td>
                <td>{formatVnd(item.net_spread_vnd_per_kg, language)}/kg</td>
                <td>{item.net_spread_pct.toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {result ? <p className="advisory-disclaimer">{language === "en" ? "Transport cost is estimated from the current regional data and should be checked against real logistics quotes." : result.assumption_vi}</p> : null}
    </section>
  );
}

function CrossCropPanel({ authToken }: { authToken: string }) {
  const { language } = useLanguage();
  const [regions, setRegions] = useState<Region[]>([]);
  const [regionId, setRegionId] = useState<number | "">("");
  const [area, setArea] = useState("1");
  const [result, setResult] = useState<CrossCommodityResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const submitControllerRef = useRef<AbortController | null>(null);
  const maxProfit = useMemo(() => Math.max(1, ...(result?.items.map((item) => Math.abs(item.estimated_profit_vnd)) ?? [1])), [result]);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all(concreteCropOptions().map((item) => fetchRegions(item.value, controller.signal)))
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

  useEffect(() => () => submitControllerRef.current?.abort(), []);

  function submit() {
    if (!regionId) return;
    const safeArea = Math.max(0.1, parseDecimalInput(area) ?? 0);
    setArea(String(safeArea));
    submitControllerRef.current?.abort();
    const controller = new AbortController();
    submitControllerRef.current = controller;
    setLoading(true);
    setError(null);
    postCrossCommodity(authToken, { region_id: Number(regionId), area_hectares: safeArea }, controller.signal)
      .then(setResult, (err) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        throw err;
      })
      .catch((err) => setError(messageFromError(err, language === "en" ? "Could not compare crops." : "Không so sánh được cây trồng.")))
      .finally(() => {
        if (submitControllerRef.current === controller) {
          submitControllerRef.current = null;
          setLoading(false);
        }
      });
  }

  return (
    <section className="advisory-tool">
      <div className="advisory-tool-head">
        <h2>{language === "en" ? "Crop comparison" : "So sánh cây trồng"}</h2>
        <p>{language === "en" ? "Quickly compare reference profit across four crops by price, yield and province suitability." : "So nhanh lợi nhuận tham khảo giữa 4 cây theo giá, năng suất và độ phù hợp của tỉnh."}</p>
      </div>
      {error ? <div className="input-price-error">{error}</div> : null}
      <div className="advisory-form-row compact">
        <label>
          {language === "en" ? "Province/production area" : "Tỉnh/vùng trồng"}
          <select value={regionId} onChange={(event) => setRegionId(Number(event.target.value) || "")}>
            {regions.map((region) => (
              <option key={region.region_id} value={region.region_id}>{regionLabel(region)}</option>
            ))}
          </select>
        </label>
        <label>
          {language === "en" ? "Area (ha)" : "Diện tích (ha)"}
          <input inputMode="decimal" value={area} onChange={(event) => setArea(decimalInputValue(event.target.value))} />
        </label>
        <button type="button" className="roi-primary-button" onClick={submit} disabled={loading}>
          {loading ? (language === "en" ? "Comparing" : "Đang so sánh") : (language === "en" ? "Compare" : "So sánh")}
        </button>
      </div>
      {result ? (
        <>
          <p className="advisory-context">{language === "en" ? "Province being compared" : "Tỉnh đang so sánh"}: <strong>{result.province ?? result.region_name}</strong></p>
          <div className="cross-crop-bars">
            {result.items.map((item) => (
              <article key={item.crop}>
                <div>
                  <span>{cropLabel(item.crop, language)}</span>
                  <strong>{formatVnd(item.estimated_profit_vnd, language)}</strong>
                </div>
                <i style={{ width: `${Math.max(8, (Math.abs(item.estimated_profit_vnd) / maxProfit) * 100)}%` }} />
                <small>{language === "en" ? "Suitability" : "Độ phù hợp"} {Math.round(item.suitability_score * 100)}% · {language === "en" ? "Profit ratio" : "Tỷ suất lợi nhuận"} {item.roi_score.toFixed(1)}%</small>
              </article>
            ))}
          </div>
          <div className="advisory-disclaimer">
            {language === "vi"
              ? result.intercropping_vi.map((note) => <p key={note}>{note}</p>)
              : <p>Use this comparison as a screening layer. Field suitability, disease pressure, cash flow and market access still need local checks.</p>}
            <p>{language === "en" ? "Profit figures are estimates for comparison only, not a guaranteed farm result." : result.disclaimer_vi}</p>
          </div>
        </>
      ) : null}
    </section>
  );
}
