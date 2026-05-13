import { useMemo, useState } from "react";
import { AlertTriangle, Calculator, ClipboardCheck, Gauge, Leaf, PackageCheck, Ruler, ShieldAlert, Sprout } from "./icons";
import { SeoHead } from "./SeoHead";
import { recommendFertilizer, type FertilizerCrop, type FertilizerRecommendation, type FertilizerRequest, type FertilizerStage, type SoilTexture } from "../lib/api";

const cropOptions: { value: FertilizerCrop; label: string; defaultDensity: number; defaultYield: number; texture: SoilTexture }[] = [
  { value: "robusta_coffee", label: "Cà phê Robusta", defaultDensity: 1100, defaultYield: 3.5, texture: "basaltic_red" },
  { value: "black_pepper", label: "Hồ tiêu", defaultDensity: 1600, defaultYield: 3, texture: "basaltic_red" },
  { value: "durian", label: "Sầu riêng", defaultDensity: 150, defaultYield: 15, texture: "basaltic_red" }
];

const stageOptions: { value: FertilizerStage; label: string }[] = [
  { value: "mature_kinh_doanh", label: "Vườn kinh doanh" },
  { value: "establishment_y1", label: "Kiến thiết năm 1" },
  { value: "establishment_y2", label: "Kiến thiết năm 2" },
  { value: "establishment_y3", label: "Kiến thiết năm 3" },
  { value: "establishment_y4", label: "Kiến thiết năm 4" },
  { value: "establishment_y5", label: "Kiến thiết năm 5" },
  { value: "fruit_fill", label: "Sầu riêng nuôi trái" }
];

const textureOptions: { value: SoilTexture; label: string }[] = [
  { value: "basaltic_red", label: "Đất bazan đỏ" },
  { value: "grey_granite", label: "Đất xám granite" },
  { value: "gneiss", label: "Đất gneiss" },
  { value: "acrisol", label: "Đất Acrisol" },
  { value: "alluvial", label: "Đất phù sa" }
];

type FormState = {
  crop: FertilizerCrop;
  growth_stage: FertilizerStage;
  yield_target_t_ha: string;
  tree_density_per_ha: string;
  texture: SoilTexture;
  ph_kcl: string;
  organic_carbon_pct: string;
  total_n_pct: string;
  available_p_mg_per_100g: string;
  exchangeable_k2o_mg_per_100g: string;
  cec_cmolc_per_kg: string;
  annual_rainfall_mm: string;
  irrigation_available: boolean;
  slope_pct: string;
  years_under_current_crop: string;
  province: string;
};

const initialForm: FormState = {
  crop: "robusta_coffee",
  growth_stage: "mature_kinh_doanh",
  yield_target_t_ha: "3.5",
  tree_density_per_ha: "1100",
  texture: "basaltic_red",
  ph_kcl: "4.3",
  organic_carbon_pct: "2.8",
  total_n_pct: "0.18",
  available_p_mg_per_100g: "4.5",
  exchangeable_k2o_mg_per_100g: "12",
  cec_cmolc_per_kg: "8",
  annual_rainfall_mm: "1900",
  irrigation_available: true,
  slope_pct: "5",
  years_under_current_crop: "10",
  province: "Đắk Lắk"
};

export function FertilizerAdvisor() {
  const [form, setForm] = useState<FormState>(initialForm);
  const [result, setResult] = useState<FertilizerRecommendation | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selectedCrop = cropOptions.find((item) => item.value === form.crop) ?? cropOptions[0];
  const total = result?.recommendation.annual_total;
  const confidenceLabel = useMemo(() => {
    if (!result) return "Chưa tính";
    if (result.confidence.overall === "high") return "Cao";
    if (result.confidence.overall === "medium") return "Trung bình";
    return "Thấp";
  }, [result]);

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function chooseCrop(crop: FertilizerCrop) {
    const option = cropOptions.find((item) => item.value === crop) ?? cropOptions[0];
    setForm((current) => ({
      ...current,
      crop,
      texture: option.texture,
      yield_target_t_ha: String(option.defaultYield),
      tree_density_per_ha: String(option.defaultDensity),
      growth_stage: crop === "durian" && current.growth_stage === "establishment_y5" ? "establishment_y5" : "mature_kinh_doanh"
    }));
  }

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const payload: FertilizerRequest = {
        crop: form.crop,
        growth_stage: form.growth_stage,
        yield_target_t_ha: numberOrNull(form.yield_target_t_ha),
        tree_density_per_ha: numberOrNull(form.tree_density_per_ha),
        soil: {
          texture: form.texture,
          ph_kcl: Number(form.ph_kcl),
          organic_carbon_pct: numberOrNull(form.organic_carbon_pct),
          total_n_pct: numberOrNull(form.total_n_pct),
          available_p_method: "bray_ii",
          available_p_mg_per_100g: numberOrNull(form.available_p_mg_per_100g),
          exchangeable_k_method: "nh4oac",
          exchangeable_k2o_mg_per_100g: numberOrNull(form.exchangeable_k2o_mg_per_100g),
          cec_cmolc_per_kg: numberOrNull(form.cec_cmolc_per_kg),
          sample_depth_cm: 30,
          sample_date: new Date().toISOString().slice(0, 10)
        },
        location: { province: form.province || null },
        climate: { annual_rainfall_mm: numberOrNull(form.annual_rainfall_mm), irrigation_available: form.irrigation_available },
        field: { slope_pct: numberOrNull(form.slope_pct), years_under_current_crop: numberOrNull(form.years_under_current_crop) },
        preferences: { language: "vi", include_product_mix: true, preferred_brand: form.growth_stage === "fruit_fill" ? "phu_my_kcl_60" : null }
      };
      setResult(await recommendFertilizer(payload));
    } catch (err) {
      console.warn("[FertilizerAdvisor] recommendation failed", err);
      setError("Không tính được khuyến nghị lúc này. Vui lòng thử lại sau ít phút.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="fertilizer-page">
      <SeoHead
        title="Khuyến nghị bón phân NPK theo phân tích đất"
        description="Công cụ tính khuyến nghị NPK, vôi và hữu cơ cho cà phê Robusta, hồ tiêu và sầu riêng theo chỉ tiêu đất."
        canonical="/khuyen-nghi-bon-phan"
      />
      <header className="fertilizer-hero fertilizer-advisor-hero">
        <div>
          <h1>Khuyến nghị bón phân theo phân tích đất</h1>
          <p>Nhập chỉ tiêu đất, năng suất mục tiêu và điều kiện vườn để nhận lượng phân thương mại theo kg/ha, kèm lịch chia đợt và cảnh báo an toàn.</p>
        </div>
      </header>

      <div className="fertilizer-layout">
        <form className="fertilizer-form" onSubmit={(event) => { event.preventDefault(); void submit(); }}>
          <section>
            <h2><Sprout size={18} /> Thông tin vườn</h2>
            <label>
              Cây trồng
              <select value={form.crop} onChange={(event) => chooseCrop(event.target.value as FertilizerCrop)}>
                {cropOptions.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </label>
            <label>
              Giai đoạn
              <select value={form.growth_stage} onChange={(event) => update("growth_stage", event.target.value as FertilizerStage)}>
                {stageOptions.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </label>
            <div className="fertilizer-two">
              <label>
                Năng suất mục tiêu (tấn/ha)
                <input value={form.yield_target_t_ha} onChange={(event) => update("yield_target_t_ha", event.target.value)} inputMode="decimal" />
              </label>
              <label>
                Mật độ cây/ha
                <input value={form.tree_density_per_ha} onChange={(event) => update("tree_density_per_ha", event.target.value)} inputMode="numeric" />
              </label>
            </div>
            <label>
              Tỉnh/vùng
              <input value={form.province} onChange={(event) => update("province", event.target.value)} />
            </label>
          </section>

          <section>
            <h2><Ruler size={18} /> Chỉ tiêu đất</h2>
            <label>
              Loại đất
              <select value={form.texture} onChange={(event) => update("texture", event.target.value as SoilTexture)}>
                {textureOptions.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </label>
            <div className="fertilizer-two">
              <label>pH KCl<input value={form.ph_kcl} onChange={(event) => update("ph_kcl", event.target.value)} /></label>
              <label>Chất hữu cơ OC (%)<input value={form.organic_carbon_pct} onChange={(event) => update("organic_carbon_pct", event.target.value)} /></label>
              <label>Đạm tổng số (%)<input value={form.total_n_pct} onChange={(event) => update("total_n_pct", event.target.value)} /></label>
              <label>Lân dễ tiêu (mg/100g)<input value={form.available_p_mg_per_100g} onChange={(event) => update("available_p_mg_per_100g", event.target.value)} /></label>
              <label>Kali trao đổi (mg K2O/100g)<input value={form.exchangeable_k2o_mg_per_100g} onChange={(event) => update("exchangeable_k2o_mg_per_100g", event.target.value)} /></label>
              <label>CEC (cmolc/kg)<input value={form.cec_cmolc_per_kg} onChange={(event) => update("cec_cmolc_per_kg", event.target.value)} /></label>
            </div>
          </section>

          <section>
            <h2><Gauge size={18} /> Điều kiện hiệu chỉnh</h2>
            <div className="fertilizer-two">
              <label>Lượng mưa năm (mm)<input value={form.annual_rainfall_mm} onChange={(event) => update("annual_rainfall_mm", event.target.value)} /></label>
              <label>Độ dốc (%)<input value={form.slope_pct} onChange={(event) => update("slope_pct", event.target.value)} /></label>
              <label>Tuổi vườn<input value={form.years_under_current_crop} onChange={(event) => update("years_under_current_crop", event.target.value)} /></label>
              <label className="fertilizer-check"><input type="checkbox" checked={form.irrigation_available} onChange={(event) => update("irrigation_available", event.target.checked)} /> Có tưới chủ động</label>
            </div>
          </section>

          <button className="fertilizer-submit" type="submit" disabled={busy}>
            <Calculator size={18} />
            {busy ? "Đang tính..." : "Tính khuyến nghị"}
          </button>
          {error ? <p className="fertilizer-error">{error}</p> : null}
        </form>

        <div className="fertilizer-results">
          <section className="fertilizer-summary">
            <div>
              <span>{selectedCrop.label}</span>
              <h2>{total ? `${total.n_kg_ha} - ${total.p2o5_kg_ha} - ${total.k2o_kg_ha}` : "Chưa có kết quả"}</h2>
              <p>kg hoạt chất/ha/năm: Đạm N - Lân P2O5 - Kali K2O</p>
            </div>
            <div className={`fertilizer-confidence confidence-${result?.confidence.overall ?? "none"}`}>
              <ShieldAlert size={18} />
              Độ tin cậy: {confidenceLabel}
            </div>
          </section>

          {result ? (
            <>
              <section className="fertilizer-kpi-grid">
                <Kpi label="Đạm N" value={result.recommendation.annual_total.n_kg_ha} before={result.recommendation.annual_total.n_kg_ha_before_adjustment} />
                <Kpi label="Lân P2O5" value={result.recommendation.annual_total.p2o5_kg_ha} before={result.recommendation.annual_total.p2o5_kg_ha_before_adjustment} />
                <Kpi label="Kali K2O" value={result.recommendation.annual_total.k2o_kg_ha} before={result.recommendation.annual_total.k2o_kg_ha_before_adjustment} />
                <Kpi label="Vôi" value={result.recommendation.annual_total.lime_kg_ha} unit="kg/ha" />
              </section>

              <section className="fertilizer-panel">
                <h3><AlertTriangle size={17} /> Cảnh báo an toàn</h3>
                {result.warnings.map((warning) => (
                  <article key={`${warning.code}-${warning.message_vi}`} className={`fertilizer-warning ${warning.level}`}>
                    <strong>{warningLabel(warning.level)}</strong>
                    <p>{warning.message_vi}</p>
                  </article>
                ))}
              </section>

              <section className="fertilizer-panel">
                <h3><ClipboardCheck size={17} /> Lịch bón theo phân thương mại</h3>
                <div className="fertilizer-splits">
                  {result.recommendation.splits.map((split) => (
                    <article key={split.split_index}>
                      <span>{split.calendar_window}</span>
                      <strong>{split.name_vi}</strong>
                      <div className="fertilizer-split-products">
                        {split.commercial_products.map((product) => (
                          <small key={product.sku}>
                            {product.name_vi}: <b>{product.kg_ha_yr.toLocaleString("vi-VN")} kg/ha</b>
                            {product.bags_50kg_ha > 0 ? ` (${product.bags_50kg_ha} bao 50 kg)` : ""}
                          </small>
                        ))}
                      </div>
                    </article>
                  ))}
                </div>
              </section>

              <section className="fertilizer-panel">
                <h3><PackageCheck size={17} /> Tổng lượng phân thương mại cả năm</h3>
                {result.recommendation.product_mix_options[0]?.products.map((product) => (
                  <div className="fertilizer-product" key={product.sku}>
                    <span>{product.name_vi}</span>
                    <strong>{product.kg_ha_yr.toLocaleString("vi-VN")} kg/ha</strong>
                    <small>{product.bags_50kg_ha} bao 50 kg</small>
                  </div>
                ))}
              </section>

              <section className="fertilizer-panel">
                <h3><Leaf size={17} /> Vì sao ra khuyến nghị này?</h3>
                <p>{result.recommendation.annual_total.rationale_vi}</p>
                <div className="fertilizer-factor-grid">
                  {result.recommendation.annual_total.adjustment_factors.breakdown.map((factor) => (
                    <article key={factor.code}>
                      <strong>{factorName(factor.name)}</strong>
                      <span>Hệ số hiệu chỉnh</span>
                      <small>Đạm x{factor.n} - Lân x{factor.p} - Kali x{factor.k}</small>
                      {factor.rationale_vi ? <p>{factor.rationale_vi}</p> : null}
                    </article>
                  ))}
                </div>
              </section>
            </>
          ) : (
            <section className="fertilizer-empty">
              <Calculator size={36} />
              <h2>Nhập phiếu phân tích đất để bắt đầu</h2>
              <p>Công cụ sẽ trả về lượng phân thương mại, cảnh báo, độ tin cậy và vết tính toán. Chỉ tiêu thiếu sẽ được giả định ở mức trung bình và ghi rõ trong kết quả.</p>
            </section>
          )}
        </div>
      </div>
    </section>
  );
}

function Kpi({ label, value, before, unit = "kg/ha" }: { label: string; value: number; before?: number; unit?: string }) {
  return (
    <article>
      <span>{label}</span>
      <strong>{value.toLocaleString("vi-VN")}</strong>
      <small>{unit}{before !== undefined ? ` - trước hiệu chỉnh ${before.toLocaleString("vi-VN")}` : ""}</small>
    </article>
  );
}

function warningLabel(level: string) {
  if (level === "critical") return "Cảnh báo quan trọng";
  if (level === "warning") return "Cần lưu ý";
  return "Thông tin";
}

function factorName(name: string) {
  const normalized = name.toLowerCase();
  if (normalized.includes("moisture")) return "Nước tưới và lượng mưa";
  if (normalized.includes("texture")) return "Kết cấu đất";
  if (normalized.includes("slope")) return "Độ dốc lô đất";
  if (normalized.includes("age")) return "Tuổi vườn";
  if (normalized.includes("organic")) return "Chất hữu cơ";
  return name;
}

function numberOrNull(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed.replace(",", "."));
  return Number.isFinite(parsed) ? parsed : null;
}
