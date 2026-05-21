import { useMemo, useState } from "react";
import { AlertTriangle, Calculator, ClipboardCheck, Gauge, Leaf, PackageCheck, Ruler, ShieldAlert, Sprout } from "./icons";
import { SeoHead } from "./SeoHead";
import { recommendFertilizer, type FertilizerCrop, type FertilizerKSource, type FertilizerRecommendation, type FertilizerRequest, type FertilizerStage, type SoilTexture } from "../lib/api";

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
  { value: "fruit_set", label: "Sầu riêng đậu trái" },
  { value: "fruit_fill", label: "Sầu riêng nuôi trái" }
];

const textureOptions: { value: SoilTexture; label: string }[] = [
  { value: "basaltic_red", label: "Đất bazan đỏ" },
  { value: "grey_granite", label: "Đất xám granite" },
  { value: "gneiss", label: "Đất gneiss" },
  { value: "acrisol", label: "Đất Acrisol" },
  { value: "alluvial", label: "Đất phù sa" }
];

const durianVarieties = ["Ri6", "Monthong", "TR4", "TR9", "Musang King", "Khác"];

const kSourceOptions: { value: FertilizerKSource; label: string }[] = [
  { value: "kcl", label: "KCl 60%" },
  { value: "k2so4", label: "K2SO4 50%" },
  { value: "kno3", label: "KNO3" }
];

type FormState = {
  crop: FertilizerCrop;
  variety: string;
  growth_stage: FertilizerStage;
  preferred_k_source: FertilizerKSource;
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

type FertilizerAdvisorProps = {
  authToken: string | null;
  onRequireAuth: () => void;
};

const initialForm: FormState = {
  crop: "robusta_coffee",
  variety: "",
  growth_stage: "mature_kinh_doanh",
  preferred_k_source: "kcl",
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

export function FertilizerAdvisor({ authToken, onRequireAuth }: FertilizerAdvisorProps) {
  const [form, setForm] = useState<FormState>(initialForm);
  const [result, setResult] = useState<FertilizerRecommendation | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selectedCrop = cropOptions.find((item) => item.value === form.crop) ?? cropOptions[0];
  const total = result?.recommendation.annual_total;
  const confidenceLabel = useMemo(() => {
    if (!result) return "Chưa tính";
    if (result.confidence.badge_vi) return result.confidence.badge_vi;
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
      variety: crop === "durian" ? current.variety || "Ri6" : "",
      texture: option.texture,
      yield_target_t_ha: String(option.defaultYield),
      tree_density_per_ha: String(option.defaultDensity),
      preferred_k_source: crop === "durian" ? current.preferred_k_source : "kcl",
      growth_stage: crop === "durian" && current.growth_stage === "establishment_y5" ? "establishment_y5" : "mature_kinh_doanh"
    }));
  }

  async function submit() {
    if (!authToken) {
      setError(null);
      onRequireAuth();
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const payload: FertilizerRequest = {
        crop: form.crop,
        variety: form.crop === "durian" ? form.variety || "Ri6" : null,
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
        preferences: {
          language: "vi",
          include_product_mix: true,
          preferred_brand: kSourceToBrand(form.preferred_k_source),
          preferred_k_source: form.preferred_k_source
        }
      };
      setResult(await recommendFertilizer(payload, authToken));
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
        <aside className="fertilizer-intro-card" aria-label="Nội dung kết quả">
          <strong>Kết quả sau khi tính gồm</strong>
          <ul>
            <li>N-P-K và vôi theo kg/ha/năm</li>
            <li>Lịch bón theo từng đợt</li>
            <li>Cảnh báo an toàn và độ tin cậy</li>
          </ul>
        </aside>
      </header>

      <div className="fertilizer-layout">
        <form className="fertilizer-form" onSubmit={(event) => { event.preventDefault(); void submit(); }}>
          <div className="fertilizer-form-head">
            <strong>{selectedCrop.label}</strong>
            <span>3 nhóm thông tin</span>
          </div>

          <section className="fertilizer-form-section">
            <SectionTitle step="1" Icon={Sprout} title="Thông tin vườn" note="Giữ giá trị mặc định nếu chưa có số liệu chính xác." />
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
            {form.crop === "durian" ? (
              <div className="fertilizer-two">
                <label>
                  Giống sầu riêng
                  <select value={form.variety || "Ri6"} onChange={(event) => update("variety", event.target.value)}>
                    {durianVarieties.map((item) => <option key={item} value={item}>{item}</option>)}
                  </select>
                </label>
                <label>
                  Nguồn kali dự kiến
                  <select value={form.preferred_k_source} onChange={(event) => update("preferred_k_source", event.target.value as FertilizerKSource)}>
                    {kSourceOptions.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                  </select>
                </label>
              </div>
            ) : null}
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

          <section className="fertilizer-form-section">
            <SectionTitle step="2" Icon={Ruler} title="Chỉ tiêu đất" note="Các trường có thể chỉnh theo phiếu phân tích đất." />
            <label>
              Loại đất
              <select value={form.texture} onChange={(event) => update("texture", event.target.value as SoilTexture)}>
                {textureOptions.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </label>
            <div className="fertilizer-two">
              <label>pH KCl<input value={form.ph_kcl} onChange={(event) => update("ph_kcl", event.target.value)} inputMode="decimal" /></label>
              <label>Chất hữu cơ OC (%)<input value={form.organic_carbon_pct} onChange={(event) => update("organic_carbon_pct", event.target.value)} inputMode="decimal" /></label>
              <label>Đạm tổng số (%)<input value={form.total_n_pct} onChange={(event) => update("total_n_pct", event.target.value)} inputMode="decimal" /></label>
              <label>Lân dễ tiêu (mg/100g)<input value={form.available_p_mg_per_100g} onChange={(event) => update("available_p_mg_per_100g", event.target.value)} inputMode="decimal" /></label>
              <label>Kali trao đổi (mg K2O/100g)<input value={form.exchangeable_k2o_mg_per_100g} onChange={(event) => update("exchangeable_k2o_mg_per_100g", event.target.value)} inputMode="decimal" /></label>
              <label>CEC (cmolc/kg)<input value={form.cec_cmolc_per_kg} onChange={(event) => update("cec_cmolc_per_kg", event.target.value)} inputMode="decimal" /></label>
            </div>
          </section>

          <section className="fertilizer-form-section">
            <SectionTitle step="3" Icon={Gauge} title="Điều kiện hiệu chỉnh" note="Dùng để điều chỉnh liều theo điều kiện thực tế của vườn." />
            <div className="fertilizer-two">
              <label>Lượng mưa năm (mm)<input value={form.annual_rainfall_mm} onChange={(event) => update("annual_rainfall_mm", event.target.value)} inputMode="numeric" /></label>
              <label>Độ dốc (%)<input value={form.slope_pct} onChange={(event) => update("slope_pct", event.target.value)} inputMode="decimal" /></label>
              <label>Tuổi vườn<input value={form.years_under_current_crop} onChange={(event) => update("years_under_current_crop", event.target.value)} inputMode="numeric" /></label>
              <label className="fertilizer-check"><input type="checkbox" checked={form.irrigation_available} onChange={(event) => update("irrigation_available", event.target.checked)} /> Có tưới chủ động</label>
            </div>
          </section>

          <div className="fertilizer-submit-card">
            <button className="fertilizer-submit" type="submit" disabled={busy}>
              <Calculator size={18} />
              {busy ? "Đang tính..." : "Tính khuyến nghị"}
            </button>
            <p>Thông tin chỉ dùng để tính khuyến nghị bón phân hiện tại.</p>
            {error ? <div className="fertilizer-error" role="alert"><strong>Không tính được khuyến nghị</strong><span>{error}</span></div> : null}
          </div>
        </form>

        <div className={`fertilizer-results ${result ? "has-result" : "is-empty"}`}>
          <section className="fertilizer-summary">
            <div>
              <span>{selectedCrop.label}</span>
              <h2>{total ? `${total.n_kg_ha} - ${total.p2o5_kg_ha} - ${total.k2o_kg_ha}` : "Chưa có kết quả"}</h2>
              <p>kg hoạt chất/ha/năm: Đạm N - Lân P2O5 - Kali K2O</p>
            </div>
            <div
              className={`fertilizer-confidence confidence-${result?.confidence.calibration_tier ?? result?.confidence.overall ?? "none"}`}
              title={result?.confidence.explain_vi ?? undefined}
            >
              <ShieldAlert size={18} />
              {result ? confidenceLabel : `Độ tin cậy: ${confidenceLabel}`}
            </div>
            {!result ? (
              <div className="fertilizer-preview-list" aria-label="Kết quả sẽ gồm">
                <article><strong>N-P-K và vôi</strong><span>Tóm tắt lượng hoạt chất theo kg/ha/năm.</span></article>
                <article><strong>Lịch bón theo đợt</strong><span>Chia thành các cửa sổ bón phù hợp mùa vụ.</span></article>
                <article><strong>Cảnh báo an toàn</strong><span>Hiển thị rủi ro pH thấp, hữu cơ thấp hoặc liều cao.</span></article>
              </div>
            ) : null}
          </section>

          {result ? (
            <>
              <section className="fertilizer-kpi-grid">
                <Kpi label="Đạm N" value={result.recommendation.annual_total.n_kg_ha} before={result.recommendation.annual_total.n_kg_ha_before_adjustment} />
                <Kpi label="Lân P2O5" value={result.recommendation.annual_total.p2o5_kg_ha} before={result.recommendation.annual_total.p2o5_kg_ha_before_adjustment} />
                <Kpi label="Kali K2O" value={result.recommendation.annual_total.k2o_kg_ha} before={result.recommendation.annual_total.k2o_kg_ha_before_adjustment} />
                <Kpi label="Vôi" value={result.recommendation.annual_total.lime_kg_ha} unit="kg/ha" />
              </section>

              <section className="fertilizer-panel fertilizer-session-panel">
                <h3><ClipboardCheck size={17} /> Mã phiên và độ tin cậy</h3>
                <div className="fertilizer-session-row">
                  <div>
                    <span>Mã khuyến nghị</span>
                    <strong>{result.session_code ?? result.request_id.slice(0, 8).toUpperCase()}</strong>
                  </div>
                  <a href={`/bao-cao-nang-suat?sid=${encodeURIComponent(result.session_code ?? result.request_id.slice(0, 8).toUpperCase())}`}>
                    Báo cáo năng suất sau thu hoạch
                  </a>
                </div>
                <p>
                  {result.confidence.explain_vi ?? "Độ tin cậy phụ thuộc cây trồng, dữ liệu đất nhập vào và mức hiệu chỉnh đang có."}{" "}
                  <a href="/khuyen-nghi-bon-phan/logic">Xem cách hiệu chuẩn</a>
                </p>
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
              <h2>Nhập phiếu phân tích đất để bắt đầu</h2>
              <p>Công cụ sẽ trả về lượng phân thương mại, cảnh báo, độ tin cậy và vết tính toán. Chỉ tiêu thiếu sẽ được giả định ở mức trung bình và ghi rõ trong kết quả.</p>
            </section>
          )}
        </div>
      </div>
    </section>
  );
}

function SectionTitle({ step, Icon, title, note }: { step: string; Icon: typeof Sprout; title: string; note: string }) {
  return (
    <div className="fertilizer-section-title">
      <span className="fertilizer-step-dot">{step}</span>
      <div>
        <h2><Icon size={18} /> {title}</h2>
        <p>{note}</p>
      </div>
    </div>
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

function kSourceToBrand(value: FertilizerKSource) {
  if (value === "k2so4") return "phu_my_k2so4_50";
  if (value === "kno3") return "potassium_nitrate_13_0_46";
  return "phu_my_kcl_60";
}

function numberOrNull(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed.replace(",", "."));
  return Number.isFinite(parsed) ? parsed : null;
}
