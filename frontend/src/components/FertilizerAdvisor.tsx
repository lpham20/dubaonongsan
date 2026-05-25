import { useMemo, useState } from "react";
import { AlertTriangle, Calculator, ClipboardCheck, Gauge, Leaf, PackageCheck, Ruler, ShieldAlert, Sprout } from "./icons";
import { SeoHead } from "./SeoHead";
import { recommendFertilizer, type FertilizerCrop, type FertilizerKSource, type FertilizerRecommendation, type FertilizerRequest, type FertilizerStage, type SoilTexture } from "../lib/api";
import { useLanguage } from "../contexts/LanguageContext";
import { withLanguagePrefix } from "../lib/localizedRoutes";
import {
  confidenceLabel as localizedConfidenceLabel,
  fertilizerCropLabel,
  fertilizerStageLabel,
  soilTextureLabel,
  translateFertilizerProduct,
  translateFertilizerSplit
} from "../lib/displayLabels";

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

const fertilizerCopy = {
  vi: {
    seoTitle: "Khuyến nghị bón phân NPK theo phân tích đất",
    seoDescription: "Công cụ tính khuyến nghị NPK, vôi và hữu cơ cho cà phê Robusta, hồ tiêu và sầu riêng theo chỉ tiêu đất.",
    title: "Khuyến nghị bón phân theo phân tích đất",
    intro: "Nhập chỉ tiêu đất, năng suất mục tiêu và điều kiện vườn để nhận lượng phân thương mại theo kg/ha, kèm lịch chia đợt và cảnh báo an toàn.",
    resultIncludes: "Kết quả sau khi tính gồm",
    includeNpk: "N-P-K và vôi theo kg/ha/năm",
    includeSchedule: "Lịch bón theo từng đợt",
    includeSafety: "Cảnh báo an toàn và độ tin cậy",
    groups: "3 nhóm thông tin",
    gardenInfo: "Thông tin vườn",
    gardenNote: "Giữ giá trị mặc định nếu chưa có số liệu chính xác.",
    crop: "Cây trồng",
    stage: "Giai đoạn",
    durianVariety: "Giống sầu riêng",
    otherVariety: "Khác",
    kSource: "Nguồn kali dự kiến",
    targetYield: "Năng suất mục tiêu (tấn/ha)",
    density: "Mật độ cây/ha",
    province: "Tỉnh/vùng",
    soilMetrics: "Chỉ tiêu đất",
    soilNote: "Các trường có thể chỉnh theo phiếu phân tích đất.",
    soilType: "Loại đất",
    organicCarbon: "Chất hữu cơ OC (%)",
    totalNitrogen: "Đạm tổng số (%)",
    availableP: "Lân dễ tiêu (mg/100g)",
    exchangeableK: "Kali trao đổi (mg K2O/100g)",
    adjustment: "Điều kiện hiệu chỉnh",
    adjustmentNote: "Dùng để điều chỉnh liều theo điều kiện thực tế của vườn.",
    rainfall: "Lượng mưa năm (mm)",
    slope: "Độ dốc (%)",
    orchardAge: "Tuổi vườn",
    irrigation: "Có tưới chủ động",
    calculating: "Đang tính...",
    calculate: "Tính khuyến nghị",
    privacy: "Thông tin chỉ dùng để tính khuyến nghị bón phân hiện tại.",
    errorTitle: "Không tính được khuyến nghị",
    errorBody: "Không tính được khuyến nghị lúc này. Vui lòng thử lại sau ít phút.",
    noResult: "Chưa có kết quả",
    activeNutrients: "kg hoạt chất/ha/năm: Đạm N - Lân P2O5 - Kali K2O",
    confidence: "Độ tin cậy",
    previewLabel: "Kết quả sẽ gồm",
    previewNpkTitle: "N-P-K và vôi",
    previewNpkBody: "Tóm tắt lượng hoạt chất theo kg/ha/năm.",
    previewScheduleTitle: "Lịch bón theo đợt",
    previewScheduleBody: "Chia thành các cửa sổ bón phù hợp mùa vụ.",
    previewSafetyTitle: "Cảnh báo an toàn",
    previewSafetyBody: "Hiển thị rủi ro pH thấp, hữu cơ thấp hoặc liều cao.",
    lime: "Vôi",
    sessionTitle: "Mã phiên và độ tin cậy",
    sessionCode: "Mã khuyến nghị",
    yieldReport: "Báo cáo năng suất sau thu hoạch",
    calibrationLink: "Xem cách hiệu chuẩn",
    confidenceFallback: "Độ tin cậy phụ thuộc cây trồng, dữ liệu đất nhập vào và mức hiệu chỉnh đang có.",
    safetyTitle: "Cảnh báo an toàn",
    scheduleTitle: "Lịch bón theo phân thương mại",
    yearlyProductTitle: "Tổng lượng phân thương mại cả năm",
    bags50kg: "bao 50 kg",
    whyTitle: "Vì sao ra khuyến nghị này?",
    rationaleFallback: "Khuyến nghị được tính từ chỉ tiêu đất, năng suất mục tiêu và các hệ số điều chỉnh theo điều kiện vườn.",
    factorMultiplier: "Hệ số hiệu chỉnh",
    beforeAdjustment: "trước hiệu chỉnh",
    emptyTitle: "Nhập phiếu phân tích đất để bắt đầu",
    emptyBody: "Công cụ sẽ trả về lượng phân thương mại, cảnh báo, độ tin cậy và vết tính toán. Chỉ tiêu thiếu sẽ được giả định ở mức trung bình và ghi rõ trong kết quả.",
    warningCritical: "Cảnh báo quan trọng",
    warning: "Cần lưu ý",
    info: "Thông tin"
  },
  en: {
    seoTitle: "Soil-test fertilizer recommendation for NPK planning",
    seoDescription: "Estimate NPK, lime and organic matter needs for Robusta coffee, black pepper and durian from soil-test data.",
    title: "Fertilizer recommendation from soil-test data",
    intro: "Enter soil indicators, target yield and orchard conditions to estimate commercial fertilizer rates, split timing and safety flags.",
    resultIncludes: "After calculation you will get",
    includeNpk: "N-P-K and lime rates in kg/ha/year",
    includeSchedule: "Application schedule by split",
    includeSafety: "Safety warnings and confidence level",
    groups: "3 data groups",
    gardenInfo: "Orchard information",
    gardenNote: "Keep the defaults if you do not have precise field data yet.",
    crop: "Crop",
    stage: "Growth stage",
    durianVariety: "Durian variety",
    otherVariety: "Other",
    kSource: "Preferred potassium source",
    targetYield: "Target yield (tonnes/ha)",
    density: "Plant density/ha",
    province: "Province/area",
    soilMetrics: "Soil indicators",
    soilNote: "Adjust these fields to match your soil-test sheet.",
    soilType: "Soil type",
    organicCarbon: "Organic carbon OC (%)",
    totalNitrogen: "Total nitrogen (%)",
    availableP: "Available phosphorus (mg/100g)",
    exchangeableK: "Exchangeable potassium (mg K2O/100g)",
    adjustment: "Adjustment conditions",
    adjustmentNote: "Used to fine-tune the rate for real orchard conditions.",
    rainfall: "Annual rainfall (mm)",
    slope: "Slope (%)",
    orchardAge: "Orchard age",
    irrigation: "Active irrigation available",
    calculating: "Calculating...",
    calculate: "Calculate recommendation",
    privacy: "This information is used only for the current fertilizer calculation.",
    errorTitle: "Could not calculate recommendation",
    errorBody: "The recommendation could not be calculated right now. Please try again in a few minutes.",
    noResult: "No result yet",
    activeNutrients: "kg active nutrients/ha/year: Nitrogen N - Phosphate P2O5 - Potash K2O",
    confidence: "Confidence",
    previewLabel: "The result will include",
    previewNpkTitle: "N-P-K and lime",
    previewNpkBody: "A yearly active-nutrient summary in kg/ha.",
    previewScheduleTitle: "Split schedule",
    previewScheduleBody: "Suggested application windows for the season.",
    previewSafetyTitle: "Safety flags",
    previewSafetyBody: "Warnings for low pH, low organic matter or high rates.",
    lime: "Lime",
    sessionTitle: "Session code and confidence",
    sessionCode: "Recommendation code",
    yieldReport: "Report post-harvest yield",
    calibrationLink: "See calibration logic",
    confidenceFallback: "Confidence depends on the crop, soil data quality and the available calibration basis.",
    safetyTitle: "Safety warnings",
    scheduleTitle: "Commercial fertilizer schedule",
    yearlyProductTitle: "Total commercial fertilizer for the year",
    bags50kg: "50 kg bags",
    whyTitle: "Why this recommendation?",
    rationaleFallback: "The recommendation combines soil indicators, target yield and field-condition adjustment factors.",
    factorMultiplier: "Adjustment factor",
    beforeAdjustment: "before adjustment",
    emptyTitle: "Enter soil-test data to start",
    emptyBody: "The tool will return commercial fertilizer rates, warnings, confidence and a calculation trace. Missing indicators are estimated at a middle baseline and noted in the result.",
    warningCritical: "Critical warning",
    warning: "Watch carefully",
    info: "Information"
  }
} as const;

export function FertilizerAdvisor({ authToken, onRequireAuth }: FertilizerAdvisorProps) {
  const { language } = useLanguage();
  const copy = fertilizerCopy[language];
  const [form, setForm] = useState<FormState>(initialForm);
  const [result, setResult] = useState<FertilizerRecommendation | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selectedCrop = cropOptions.find((item) => item.value === form.crop) ?? cropOptions[0];
  const selectedCropLabel = fertilizerCropLabel(selectedCrop.value, language);
  const total = result?.recommendation.annual_total;
  const confidenceLabel = useMemo(() => {
    if (!result) return language === "en" ? "Not calculated" : "Chưa tính";
    if (language === "vi" && result.confidence.badge_vi) return result.confidence.badge_vi;
    return localizedConfidenceLabel(result.confidence.overall, language);
  }, [language, result]);

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
          language,
          include_product_mix: true,
          preferred_brand: kSourceToBrand(form.preferred_k_source),
          preferred_k_source: form.preferred_k_source
        }
      };
      setResult(await recommendFertilizer(payload, authToken));
    } catch (err) {
      console.warn("[FertilizerAdvisor] recommendation failed", err);
      setError(copy.errorBody);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="fertilizer-page">
      <SeoHead
        title={copy.seoTitle}
        description={copy.seoDescription}
        canonical="/khuyen-nghi-bon-phan"
      />
      <header className="fertilizer-hero fertilizer-advisor-hero">
        <div>
          <h1>{copy.title}</h1>
          <p>{copy.intro}</p>
        </div>
        <aside className="fertilizer-intro-card" aria-label={copy.resultIncludes}>
          <strong>{copy.resultIncludes}</strong>
          <ul>
            <li>{copy.includeNpk}</li>
            <li>{copy.includeSchedule}</li>
            <li>{copy.includeSafety}</li>
          </ul>
        </aside>
      </header>

      <div className="fertilizer-layout">
        <form className="fertilizer-form" onSubmit={(event) => { event.preventDefault(); void submit(); }}>
          <div className="fertilizer-form-head">
            <strong>{selectedCropLabel}</strong>
            <span>{copy.groups}</span>
          </div>

          <section className="fertilizer-form-section">
            <SectionTitle step="1" Icon={Sprout} title={copy.gardenInfo} note={copy.gardenNote} />
            <label>
              {copy.crop}
              <select value={form.crop} onChange={(event) => chooseCrop(event.target.value as FertilizerCrop)}>
                {cropOptions.map((item) => <option key={item.value} value={item.value}>{fertilizerCropLabel(item.value, language)}</option>)}
              </select>
            </label>
            <label>
              {copy.stage}
              <select value={form.growth_stage} onChange={(event) => update("growth_stage", event.target.value as FertilizerStage)}>
                {stageOptions.map((item) => <option key={item.value} value={item.value}>{fertilizerStageLabel(item.value, language)}</option>)}
              </select>
            </label>
            {form.crop === "durian" ? (
              <div className="fertilizer-two">
                <label>
                  {copy.durianVariety}
                  <select value={form.variety || "Ri6"} onChange={(event) => update("variety", event.target.value)}>
                    {durianVarieties.map((item) => <option key={item} value={item}>{language === "en" && item === "Khác" ? copy.otherVariety : item}</option>)}
                  </select>
                </label>
                <label>
                  {copy.kSource}
                  <select value={form.preferred_k_source} onChange={(event) => update("preferred_k_source", event.target.value as FertilizerKSource)}>
                    {kSourceOptions.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                  </select>
                </label>
              </div>
            ) : null}
            <div className="fertilizer-two">
              <label>
                {copy.targetYield}
                <input value={form.yield_target_t_ha} onChange={(event) => update("yield_target_t_ha", event.target.value)} inputMode="decimal" />
              </label>
              <label>
                {copy.density}
                <input value={form.tree_density_per_ha} onChange={(event) => update("tree_density_per_ha", event.target.value)} inputMode="numeric" />
              </label>
            </div>
            <label>
              {copy.province}
              <input value={form.province} onChange={(event) => update("province", event.target.value)} />
            </label>
          </section>

          <section className="fertilizer-form-section">
            <SectionTitle step="2" Icon={Ruler} title={copy.soilMetrics} note={copy.soilNote} />
            <label>
              {copy.soilType}
              <select value={form.texture} onChange={(event) => update("texture", event.target.value as SoilTexture)}>
                {textureOptions.map((item) => <option key={item.value} value={item.value}>{soilTextureLabel(item.value, language)}</option>)}
              </select>
            </label>
            <div className="fertilizer-two">
              <label>pH KCl<input value={form.ph_kcl} onChange={(event) => update("ph_kcl", event.target.value)} inputMode="decimal" /></label>
              <label>{copy.organicCarbon}<input value={form.organic_carbon_pct} onChange={(event) => update("organic_carbon_pct", event.target.value)} inputMode="decimal" /></label>
              <label>{copy.totalNitrogen}<input value={form.total_n_pct} onChange={(event) => update("total_n_pct", event.target.value)} inputMode="decimal" /></label>
              <label>{copy.availableP}<input value={form.available_p_mg_per_100g} onChange={(event) => update("available_p_mg_per_100g", event.target.value)} inputMode="decimal" /></label>
              <label>{copy.exchangeableK}<input value={form.exchangeable_k2o_mg_per_100g} onChange={(event) => update("exchangeable_k2o_mg_per_100g", event.target.value)} inputMode="decimal" /></label>
              <label>CEC (cmolc/kg)<input value={form.cec_cmolc_per_kg} onChange={(event) => update("cec_cmolc_per_kg", event.target.value)} inputMode="decimal" /></label>
            </div>
          </section>

          <section className="fertilizer-form-section">
            <SectionTitle step="3" Icon={Gauge} title={copy.adjustment} note={copy.adjustmentNote} />
            <div className="fertilizer-two">
              <label>{copy.rainfall}<input value={form.annual_rainfall_mm} onChange={(event) => update("annual_rainfall_mm", event.target.value)} inputMode="numeric" /></label>
              <label>{copy.slope}<input value={form.slope_pct} onChange={(event) => update("slope_pct", event.target.value)} inputMode="decimal" /></label>
              <label>{copy.orchardAge}<input value={form.years_under_current_crop} onChange={(event) => update("years_under_current_crop", event.target.value)} inputMode="numeric" /></label>
              <label className="fertilizer-check"><input type="checkbox" checked={form.irrigation_available} onChange={(event) => update("irrigation_available", event.target.checked)} /> {copy.irrigation}</label>
            </div>
          </section>

          <div className="fertilizer-submit-card">
            <button className="fertilizer-submit" type="submit" disabled={busy}>
              <Calculator size={18} />
              {busy ? copy.calculating : copy.calculate}
            </button>
            <p>{copy.privacy}</p>
            {error ? <div className="fertilizer-error" role="alert"><strong>{copy.errorTitle}</strong><span>{error}</span></div> : null}
          </div>
        </form>

        <div className={`fertilizer-results ${result ? "has-result" : "is-empty"}`}>
          <section className="fertilizer-summary">
            <div>
              <span>{selectedCropLabel}</span>
              <h2>{total ? `${total.n_kg_ha} - ${total.p2o5_kg_ha} - ${total.k2o_kg_ha}` : copy.noResult}</h2>
              <p>{copy.activeNutrients}</p>
            </div>
            <div
              className={`fertilizer-confidence confidence-${result?.confidence.calibration_tier ?? result?.confidence.overall ?? "none"}`}
              title={language === "vi" ? result?.confidence.explain_vi ?? undefined : copy.confidenceFallback}
            >
              <ShieldAlert size={18} />
              {result ? confidenceLabel : `${copy.confidence}: ${confidenceLabel}`}
            </div>
            {!result ? (
              <div className="fertilizer-preview-list" aria-label={copy.previewLabel}>
                <article><strong>{copy.previewNpkTitle}</strong><span>{copy.previewNpkBody}</span></article>
                <article><strong>{copy.previewScheduleTitle}</strong><span>{copy.previewScheduleBody}</span></article>
                <article><strong>{copy.previewSafetyTitle}</strong><span>{copy.previewSafetyBody}</span></article>
              </div>
            ) : null}
          </section>

          {result ? (
            <>
              <section className="fertilizer-kpi-grid">
                <Kpi label={language === "en" ? "Nitrogen N" : "Đạm N"} value={result.recommendation.annual_total.n_kg_ha} before={result.recommendation.annual_total.n_kg_ha_before_adjustment} beforeLabel={copy.beforeAdjustment} />
                <Kpi label={language === "en" ? "Phosphate P2O5" : "Lân P2O5"} value={result.recommendation.annual_total.p2o5_kg_ha} before={result.recommendation.annual_total.p2o5_kg_ha_before_adjustment} beforeLabel={copy.beforeAdjustment} />
                <Kpi label={language === "en" ? "Potash K2O" : "Kali K2O"} value={result.recommendation.annual_total.k2o_kg_ha} before={result.recommendation.annual_total.k2o_kg_ha_before_adjustment} beforeLabel={copy.beforeAdjustment} />
                <Kpi label={copy.lime} value={result.recommendation.annual_total.lime_kg_ha} unit="kg/ha" beforeLabel={copy.beforeAdjustment} />
              </section>

              <section className="fertilizer-panel fertilizer-session-panel">
                <h3><ClipboardCheck size={17} /> {copy.sessionTitle}</h3>
                <div className="fertilizer-session-row">
                  <div>
                    <span>{copy.sessionCode}</span>
                    <strong>{result.session_code ?? result.request_id.slice(0, 8).toUpperCase()}</strong>
                  </div>
                  <a href={withLanguagePrefix(`/bao-cao-nang-suat?sid=${encodeURIComponent(result.session_code ?? result.request_id.slice(0, 8).toUpperCase())}`, language)}>
                    {copy.yieldReport}
                  </a>
                </div>
                <p>
                  {language === "vi" ? result.confidence.explain_vi ?? copy.confidenceFallback : copy.confidenceFallback}{" "}
                  <a href={withLanguagePrefix("/khuyen-nghi-bon-phan/logic", language)}>{copy.calibrationLink}</a>
                </p>
              </section>

              <section className="fertilizer-panel">
                <h3><AlertTriangle size={17} /> {copy.safetyTitle}</h3>
                {result.warnings.map((warning) => (
                  <article key={`${warning.code}-${warning.message_vi}`} className={`fertilizer-warning ${warning.level}`}>
                    <strong>{warningLabel(warning.level, language)}</strong>
                    <p>{language === "en" ? warning.message_en : warning.message_vi}</p>
                  </article>
                ))}
              </section>

              <section className="fertilizer-panel">
                <h3><ClipboardCheck size={17} /> {copy.scheduleTitle}</h3>
                <div className="fertilizer-splits">
                  {result.recommendation.splits.map((split) => (
                    <article key={split.split_index}>
                      <span>{split.calendar_window}</span>
                      <strong>{translateFertilizerSplit(split.name_vi, language)}</strong>
                      <div className="fertilizer-split-products">
                        {split.commercial_products.map((product) => (
                          <small key={product.sku}>
                            {translateFertilizerProduct(product.name_vi, language)}: <b>{product.kg_ha_yr.toLocaleString(language === "en" ? "en-US" : "vi-VN")} kg/ha</b>
                            {product.bags_50kg_ha > 0 ? ` (${product.bags_50kg_ha} ${copy.bags50kg})` : ""}
                          </small>
                        ))}
                      </div>
                    </article>
                  ))}
                </div>
              </section>

              <section className="fertilizer-panel">
                <h3><PackageCheck size={17} /> {copy.yearlyProductTitle}</h3>
                {result.recommendation.product_mix_options[0]?.products.map((product) => (
                  <div className="fertilizer-product" key={product.sku}>
                    <span>{translateFertilizerProduct(product.name_vi, language)}</span>
                    <strong>{product.kg_ha_yr.toLocaleString(language === "en" ? "en-US" : "vi-VN")} kg/ha</strong>
                    <small>{product.bags_50kg_ha} {copy.bags50kg}</small>
                  </div>
                ))}
              </section>

              <section className="fertilizer-panel">
                <h3><Leaf size={17} /> {copy.whyTitle}</h3>
                <p>{language === "vi" ? result.recommendation.annual_total.rationale_vi : copy.rationaleFallback}</p>
                <div className="fertilizer-factor-grid">
                  {result.recommendation.annual_total.adjustment_factors.breakdown.map((factor) => (
                    <article key={factor.code}>
                      <strong>{factorName(factor.name, language)}</strong>
                      <span>{copy.factorMultiplier}</span>
                      <small>Đạm x{factor.n} - Lân x{factor.p} - Kali x{factor.k}</small>
                      {language === "vi" && factor.rationale_vi ? <p>{factor.rationale_vi}</p> : null}
                    </article>
                  ))}
                </div>
              </section>
            </>
          ) : (
            <section className="fertilizer-empty">
              <h2>{copy.emptyTitle}</h2>
              <p>{copy.emptyBody}</p>
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

function Kpi({ label, value, before, unit = "kg/ha", beforeLabel = "trước hiệu chỉnh" }: { label: string; value: number; before?: number; unit?: string; beforeLabel?: string }) {
  return (
    <article>
      <span>{label}</span>
      <strong>{value.toLocaleString("vi-VN")}</strong>
      <small>{unit}{before !== undefined ? ` - ${beforeLabel} ${before.toLocaleString("vi-VN")}` : ""}</small>
    </article>
  );
}

function warningLabel(level: string, language: "vi" | "en" = "vi") {
  if (language === "en") {
    if (level === "critical") return "Critical warning";
    if (level === "warning") return "Watch carefully";
    return "Information";
  }
  if (level === "critical") return "Cảnh báo quan trọng";
  if (level === "warning") return "Cần lưu ý";
  return "Thông tin";
}

function factorName(name: string, language: "vi" | "en" = "vi") {
  const normalized = name.toLowerCase();
  if (language === "en") {
    if (normalized.includes("moisture")) return "Irrigation and rainfall";
    if (normalized.includes("texture")) return "Soil texture";
    if (normalized.includes("slope")) return "Field slope";
    if (normalized.includes("age")) return "Orchard age";
    if (normalized.includes("organic")) return "Organic matter";
    return name;
  }
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
