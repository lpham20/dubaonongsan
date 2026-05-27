import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowRight, Calculator, Database, RefreshCw, X } from "./icons";
import { SeoHead } from "./SeoHead";
import {
  calculateRoi,
  fetchRegions,
  type CropType,
  type Region,
  type RoiCalculateResponse
} from "../lib/api";
import { useLanguage, type AppLanguage } from "../contexts/LanguageContext";
import { cropLabel, displayProvince } from "../lib/displayLabels";
import { withLanguagePrefix } from "../lib/localizedRoutes";
import { ROI_CROP_OPTIONS } from "../lib/cropOptions";
import { decimalInputValue, parseDecimalInput } from "../lib/numberInput";
import { messageFromError } from "../lib/errorMessages";

type InputMode = "simple" | "detail";

type FertilizerLineState = {
  id: string;
  name: string;
  kg_per_ha: string;
  price_vnd_per_kg: string;
};

function formatVnd(value: number | null | undefined, language: AppLanguage = "vi") {
  if (typeof value !== "number" || !Number.isFinite(value)) return language === "en" ? "Updating" : "Đang cập nhật";
  return `${Math.round(value).toLocaleString(language === "en" ? "en-US" : "vi-VN")} VND`;
}

function formatMoneyInput(value: number | string) {
  const raw = typeof value === "number" ? String(value) : value;
  const digits = raw.replace(/[^\d]/g, "");
  if (!digits) return "";
  return Number(digits).toLocaleString("en-US");
}

function parseMoneyInput(value: string) {
  const digits = value.replace(/[^\d]/g, "");
  return digits ? Number(digits) : 0;
}

function positiveNumber(value: string) {
  const number = Number(value.replace(/[^\d.]/g, ""));
  return Number.isFinite(number) && number > 0 ? number : 0;
}

function positiveMoneyNumber(value: string) {
  const number = parseMoneyInput(value);
  return Number.isFinite(number) && number > 0 ? number : 0;
}

function scenarioLabel(value: string) {
  if (value === "optimistic") return "Upside case";
  if (value === "pessimistic") return "Downside case";
  return "Base case";
}

function MoneyInput({
  value,
  onValueChange,
  ariaLabel
}: {
  value: number;
  onValueChange: (value: number) => void;
  ariaLabel?: string;
}) {
  return (
    <input
      aria-label={ariaLabel}
      className="roi-money-input"
      inputMode="numeric"
      value={formatMoneyInput(value)}
      onChange={(event) => onValueChange(parseMoneyInput(event.target.value))}
    />
  );
}

function MoneyTextInput({
  value,
  onValueChange,
  ariaLabel
}: {
  value: string;
  onValueChange: (value: string) => void;
  ariaLabel?: string;
}) {
  return (
    <input
      aria-label={ariaLabel}
      className="roi-money-input"
      inputMode="numeric"
      value={formatMoneyInput(value)}
      onChange={(event) => onValueChange(formatMoneyInput(event.target.value))}
    />
  );
}

export function RoiCalculatorPage({
  authToken,
  onRequireAuth,
  embedded = false
}: {
  authToken: string | null;
  onRequireAuth: () => void;
  embedded?: boolean;
}) {
  const { language } = useLanguage();
  const [regions, setRegions] = useState<Region[]>([]);
  const [mode, setMode] = useState<InputMode>("simple");
  const [crop, setCrop] = useState<CropType>("ca_phe");
  const selectedCrop = ROI_CROP_OPTIONS.find((item) => item.value === crop) ?? ROI_CROP_OPTIONS[0];
  const [regionId, setRegionId] = useState<number | "">("");
  const [area, setArea] = useState("2");
  const [yieldTarget, setYieldTarget] = useState(String(selectedCrop.defaultYield));
  const [sellPrice, setSellPrice] = useState(selectedCrop.defaultPrice);
  const [fertilizerTotal, setFertilizerTotal] = useState(18_000_000);
  const [otherCost, setOtherCost] = useState(5_000_000);
  const [laborCost, setLaborCost] = useState(8_000_000);
  const [fertilizerLines, setFertilizerLines] = useState<FertilizerLineState[]>([
    { id: "line-1", name: "Urê", kg_per_ha: "250", price_vnd_per_kg: "11800" },
    { id: "line-2", name: "Kali", kg_per_ha: "180", price_vnd_per_kg: "15200" }
  ]);
  const nextLineId = useRef(2);
  const submitControllerRef = useRef<AbortController | null>(null);
  const [save, setSave] = useState(false);
  const [result, setResult] = useState<RoiCalculateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchRegions(crop, controller.signal)
      .then((items) => {
        setRegions(items);
        setRegionId((current) => current || items[0]?.region_id || "");
      })
      .catch(() => setRegions([]));
    return () => controller.abort();
  }, [crop]);

  useEffect(() => {
    const nextCrop = ROI_CROP_OPTIONS.find((item) => item.value === crop) ?? ROI_CROP_OPTIONS[0];
    setYieldTarget(String(nextCrop.defaultYield));
    setSellPrice(nextCrop.defaultPrice);
  }, [crop]);

  useEffect(() => () => submitControllerRef.current?.abort(), []);

  const sensitivityRows = useMemo(() => result?.sensitivity.matrix ?? [], [result]);

  function updateLine(index: number, patch: Partial<FertilizerLineState>) {
    setFertilizerLines((current) => current.map((line, lineIndex) => (lineIndex === index ? { ...line, ...patch } : line)));
  }

  function addLine() {
    setFertilizerLines((current) => {
      nextLineId.current += 1;
      return [...current, { id: `line-${nextLineId.current}`, name: "NPK", kg_per_ha: "100", price_vnd_per_kg: "13500" }].slice(0, 20);
    });
  }

  function removeLine(index: number) {
    setFertilizerLines((current) => current.filter((_, lineIndex) => lineIndex !== index));
  }

  function submit() {
    if (!authToken) {
      onRequireAuth();
      return;
    }
    const safeArea = Math.max(0.01, parseDecimalInput(area) ?? 0);
    const safeYield = Math.max(0.01, parseDecimalInput(yieldTarget) ?? 0);
    const safeSellPrice = Math.max(0, Number(sellPrice) || 0);
    const safeFertilizerTotal = Math.max(0, Number(fertilizerTotal) || 0);
    const safeOtherCost = Math.max(0, Number(otherCost) || 0);
    const safeLaborCost = Math.max(0, Number(laborCost) || 0);
    setArea(String(safeArea));
    setYieldTarget(String(safeYield));
    setSellPrice(safeSellPrice);
    setFertilizerTotal(safeFertilizerTotal);
    setOtherCost(safeOtherCost);
    setLaborCost(safeLaborCost);
    submitControllerRef.current?.abort();
    const controller = new AbortController();
    submitControllerRef.current = controller;
    setLoading(true);
    setError(null);
    calculateRoi(
      authToken,
      {
        crop,
        crop_area_ha: safeArea,
        expected_yield_t_ha: safeYield,
        expected_sell_price_vnd_per_kg: safeSellPrice,
        region_id: typeof regionId === "number" ? regionId : null,
        fertilizer_total_cost_vnd_per_ha: mode === "simple" ? safeFertilizerTotal : null,
        fertilizer_lines:
          mode === "detail"
            ? fertilizerLines
                .filter((line) => line.name.trim() && positiveNumber(line.kg_per_ha) > 0 && positiveMoneyNumber(line.price_vnd_per_kg) > 0)
                .map((line) => ({
                  name: line.name.trim(),
                  kg_per_ha: positiveNumber(line.kg_per_ha),
                  price_vnd_per_kg: positiveMoneyNumber(line.price_vnd_per_kg)
                }))
            : [],
        other_input_cost_vnd_per_ha: safeOtherCost,
        labor_cost_vnd_per_ha: safeLaborCost,
        save
      },
      controller.signal
    )
      .then(setResult, (err) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        throw err;
      })
      .catch((err) => setError(messageFromError(err, language === "en" ? "Could not calculate profit." : "Không tính được lợi nhuận.")))
      .finally(() => {
        if (submitControllerRef.current === controller) {
          submitControllerRef.current = null;
          setLoading(false);
        }
      });
  }

  return (
    <section className={embedded ? "roi-page roi-standard-page advisory-embedded-roi" : "roi-page fertilizer-page roi-standard-page"}>
      {!embedded ? (
        <SeoHead
          title={language === "en" ? "Farm profit calculator" : "Ước tính lợi nhuận nông vụ"}
          description={language === "en" ? "Estimate farm profit from fertilizer cost, other input costs, labour and expected crop price." : "Ước tính lợi nhuận theo chi phí phân bón do nông dân tự nhập và dự báo giá nông sản."}
          canonical="/roi-uoc-tinh"
        />
      ) : null}

      <header className="fertilizer-hero roi-hero">
        <div className="roi-hero-copy">
          <span className="input-price-kicker">
            <Calculator size={18} />
            {language === "en" ? "Farm profit" : "Lợi nhuận nông vụ"}
          </span>
          <h1>{language === "en" ? "Estimate farm profit" : "Ước tính lợi nhuận nông vụ"}</h1>
        </div>
      </header>

      {error ? <div className="input-price-error">{error}</div> : null}

      <section className="fertilizer-layout roi-grid">
        <div className="input-price-panel roi-panel">
          <div className="input-section-heading compact roi-section-heading">
            <h2>{language === "en" ? "Farm season inputs" : "Thông số nông vụ"}</h2>
            <p>{language === "en" ? "Costs are entered per hectare" : "Chi phí theo mỗi hecta"}</p>
          </div>
          <div className="roi-form">
            <label>
              {language === "en" ? "Crop" : "Cây trồng"}
              <select value={crop} onChange={(event) => setCrop(event.target.value as CropType)}>
                {ROI_CROP_OPTIONS.map((item) => (
                  <option key={item.value} value={item.value}>
                    {cropLabel(item.value, language)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {language === "en" ? "Production area" : "Vùng sản xuất"}
              <select value={regionId} onChange={(event) => setRegionId(Number(event.target.value) || "")}>
                {regions.map((region) => (
                  <option key={region.region_id} value={region.region_id}>
                    {displayProvince(region.province, region.region_name)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {language === "en" ? "Area (ha)" : "Diện tích (ha)"}
              <input inputMode="decimal" value={area} onChange={(event) => setArea(decimalInputValue(event.target.value))} />
            </label>
            <label>
              {language === "en" ? "Expected yield (tonnes/ha)" : "Năng suất kỳ vọng (tấn/ha)"}
              <input inputMode="decimal" value={yieldTarget} onChange={(event) => setYieldTarget(decimalInputValue(event.target.value))} />
            </label>
            <label>
              {language === "en" ? "Expected selling price (VND/kg)" : "Giá bán kỳ vọng (VND/kg)"}
              <MoneyInput value={sellPrice} onValueChange={setSellPrice} />
            </label>
            <label>
              {language === "en" ? "Other input cost/ha" : "Chi phí vật tư khác/ha"}
              <MoneyInput value={otherCost} onValueChange={setOtherCost} />
            </label>
            <label>
              {language === "en" ? "Labour cost/ha" : "Chi phí nhân công/ha"}
              <MoneyInput value={laborCost} onValueChange={setLaborCost} />
            </label>
          </div>
        </div>

        <div className="input-price-panel roi-panel">
          <div className="input-section-heading compact roi-section-heading roi-fertilizer-heading">
            <h2>{language === "en" ? "Fertilizer cost" : "Chi phí phân bón"}</h2>
          </div>
          <div className="roi-mode-toggle" role="tablist" aria-label={language === "en" ? "Choose fertilizer cost input mode" : "Chọn cách nhập chi phí phân bón"}>
            <button type="button" className={mode === "simple" ? "active" : ""} onClick={() => setMode("simple")}>
              {language === "en" ? "Total/ha" : "Tổng tiền/ha"}
            </button>
            <button type="button" className={mode === "detail" ? "active" : ""} onClick={() => setMode("detail")}>
              {language === "en" ? "By fertilizer line" : "Từng dòng phân"}
            </button>
          </div>

          {mode === "simple" ? (
            <div className="roi-form single">
              <label>
                {language === "en" ? "Total fertilizer cost spent/planned per ha" : "Tổng tiền phân bón đã/sẽ chi mỗi ha"}
                <MoneyInput value={fertilizerTotal} onValueChange={setFertilizerTotal} />
              </label>
            </div>
          ) : (
            <div className="roi-lines detail">
              {fertilizerLines.map((line, index) => (
                <div className="roi-line detail" key={line.id}>
                  <input aria-label={language === "en" ? "Fertilizer name" : "Tên phân bón"} value={line.name} onChange={(event) => updateLine(index, { name: event.target.value })} />
                  <input
                    aria-label={language === "en" ? "kg per ha" : "kg mỗi ha"}
                    value={line.kg_per_ha}
                    inputMode="decimal"
                    onChange={(event) => updateLine(index, { kg_per_ha: decimalInputValue(event.target.value) })}
                  />
                  <MoneyTextInput
                    ariaLabel={language === "en" ? "price per kg" : "giá mỗi kg"}
                    value={line.price_vnd_per_kg}
                    onValueChange={(value) => updateLine(index, { price_vnd_per_kg: value })}
                  />
                  <strong>{formatVnd(positiveNumber(line.kg_per_ha) * positiveMoneyNumber(line.price_vnd_per_kg), language)}</strong>
                  <button type="button" onClick={() => removeLine(index)} aria-label={language === "en" ? "Remove fertilizer line" : "Xóa dòng phân bón"} title={language === "en" ? "Remove fertilizer line" : "Xóa dòng phân bón"}>
                    <X size={16} />
                  </button>
                </div>
              ))}
              <button type="button" className="roi-secondary-button" onClick={addLine}>
                {language === "en" ? "Add fertilizer line" : "Thêm dòng phân"}
              </button>
            </div>
          )}

          <a className="roi-world-link" href={withLanguagePrefix("/du-bao-gia/phan-bon#world", language)}>
            {language === "en" ? "View world Urea/DAP/Potash trend" : "Xem xu hướng Urê/DAP/Kali thế giới"}
            <ArrowRight size={16} />
          </a>
          <label className="roi-save-option">
            <input type="checkbox" checked={save} onChange={(event) => setSave(event.target.checked)} />
            {language === "en" ? "Save scenario to account" : "Lưu kịch bản vào tài khoản"}
          </label>
          <button type="button" className="roi-primary-button" onClick={submit} disabled={loading}>
            <RefreshCw size={16} />
            {loading ? (language === "en" ? "Calculating" : "Đang tính") : (language === "en" ? "Calculate profit" : "Tính lợi nhuận")}
          </button>
        </div>
      </section>

      {result ? (
        <>
          <section className="input-stat-grid roi-result-grid">
            <div className="input-stat">
              <Database size={18} />
              <span>{language === "en" ? "Fertilizer cost/ha" : "Chi phí phân/ha"}</span>
              <strong>{formatVnd(result.fertilizer_cost_vnd_per_ha, language)}</strong>
              <small>{result.fertilizer_input_mode === "simple" ? (language === "en" ? "Your total input" : "Tổng tiền anh nhập") : `${result.breakdown.length} ${language === "en" ? "fertilizer lines" : "dòng phân"}`}</small>
            </div>
            <div className="input-stat">
              <Calculator size={18} />
              <span>{language === "en" ? "Expected profit" : "Lợi nhuận kỳ vọng"}</span>
              <strong>{formatVnd(result.net_profit_vnd, language)}</strong>
              <small>{result.forecast_model_kind}</small>
            </div>
            <div className="input-stat">
              <Calculator size={18} />
              <span>{language === "en" ? "Profit ratio" : "Tỷ suất lợi nhuận"}</span>
              <strong className={result.roi_pct >= 0 ? "positive" : "negative"}>{result.roi_pct.toFixed(1)}%</strong>
              <small>{language === "en" ? "Confidence" : "Độ tin cậy"} {Math.round(result.confidence_score * 100)}%</small>
            </div>
          </section>

          <section className="roi-scenario-grid" aria-label={language === "en" ? "Base profit scenarios" : "Kịch bản lợi nhuận cơ sở"}>
            {result.scenarios.map((scenario) => (
              <article key={scenario.scenario} className={`roi-scenario-card ${scenario.scenario}`}>
                <span>{language === "en" ? scenarioLabel(scenario.scenario) : scenario.label_vi}</span>
                <strong className={scenario.roi_pct >= 0 ? "positive" : "negative"}>{scenario.roi_pct.toFixed(1)}%</strong>
                <small>{formatVnd(scenario.net_profit_vnd, language)}</small>
                <p>{language === "en" ? "Scenario based on expected yield, selling price and input-cost assumptions." : scenario.rationale_vi}</p>
              </article>
            ))}
          </section>

          <section className="input-price-panel input-price-data">
            <div className="input-section-heading compact">
              <h2>{language === "en" ? "Recommendation" : "Khuyến nghị"}</h2>
              <p>{language === "en" ? "Based on fertilizer cost, crop price forecast and the profit safety margin" : "Rút ra từ chi phí phân bón, dự báo giá nông sản và biên an toàn lợi nhuận"}</p>
            </div>
            <div className="roi-recommendations">
              {language === "vi"
                ? result.recommendations_vi.map((note) => <p key={note}>{note}</p>)
                : <p>Use the result as a working estimate. Recheck real fertilizer quotes and selling prices before making a large purchase or sales decision.</p>}
            </div>
          </section>

          <section className="input-price-panel input-price-data">
            <div className="input-section-heading compact">
              <h2>{language === "en" ? "Profit sensitivity" : "Độ nhạy lợi nhuận"}</h2>
              <p>{language === "en" ? "Selling price +/-10%, fertilizer price +/-15%" : "Giá bán ±10%, giá phân bón ±15%"}</p>
            </div>
            <div className="input-table-wrap">
              <table aria-label={language === "en" ? "Profit sensitivity table" : "Bảng độ nhạy lợi nhuận"}>
                <thead>
                  <tr>
                    <th>{language === "en" ? "Selling price" : "Giá bán"}</th>
                    <th>{language === "en" ? "Fertilizer price" : "Giá phân"}</th>
                    <th>{language === "en" ? "Ratio" : "Tỷ suất"}</th>
                    <th>{language === "en" ? "Net profit" : "Lợi nhuận ròng"}</th>
                  </tr>
                </thead>
                <tbody>
                  {sensitivityRows.map((row) => (
                    <tr key={`${row.sell_price_delta_pct}-${row.fertilizer_price_delta_pct}`}>
                      <td>{row.sell_price_delta_pct > 0 ? "+" : ""}{row.sell_price_delta_pct}%</td>
                      <td>{row.fertilizer_price_delta_pct > 0 ? "+" : ""}{row.fertilizer_price_delta_pct}%</td>
                      <td>{row.roi_pct.toFixed(1)}%</td>
                      <td>{formatVnd(row.net_profit_vnd, language)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      ) : null}
    </section>
  );
}
