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

const cropOptions: { value: CropType; label: string; defaultYield: number; defaultPrice: number }[] = [
  { value: "ca_phe", label: "Cà phê", defaultYield: 3.5, defaultPrice: 95_000 },
  { value: "sau_rieng", label: "Sầu riêng", defaultYield: 18, defaultPrice: 72_000 },
  { value: "ho_tieu", label: "Hồ tiêu", defaultYield: 2.6, defaultPrice: 135_000 },
  { value: "lua", label: "Lúa", defaultYield: 6.5, defaultPrice: 8_500 }
];

type InputMode = "simple" | "detail";

type FertilizerLineState = {
  id: string;
  name: string;
  kg_per_ha: string;
  price_vnd_per_kg: string;
};

function formatVnd(value: number | null | undefined) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "Đang cập nhật";
  return `${Math.round(value).toLocaleString("vi-VN")} đ`;
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
  const [regions, setRegions] = useState<Region[]>([]);
  const [mode, setMode] = useState<InputMode>("simple");
  const [crop, setCrop] = useState<CropType>("ca_phe");
  const selectedCrop = cropOptions.find((item) => item.value === crop) ?? cropOptions[0];
  const [regionId, setRegionId] = useState<number | "">("");
  const [area, setArea] = useState(2);
  const [yieldTarget, setYieldTarget] = useState(selectedCrop.defaultYield);
  const [sellPrice, setSellPrice] = useState(selectedCrop.defaultPrice);
  const [fertilizerTotal, setFertilizerTotal] = useState(18_000_000);
  const [otherCost, setOtherCost] = useState(5_000_000);
  const [laborCost, setLaborCost] = useState(8_000_000);
  const [fertilizerLines, setFertilizerLines] = useState<FertilizerLineState[]>([
    { id: "line-1", name: "Urê", kg_per_ha: "250", price_vnd_per_kg: "11800" },
    { id: "line-2", name: "Kali", kg_per_ha: "180", price_vnd_per_kg: "15200" }
  ]);
  const nextLineId = useRef(2);
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
    const nextCrop = cropOptions.find((item) => item.value === crop) ?? cropOptions[0];
    setYieldTarget(nextCrop.defaultYield);
    setSellPrice(nextCrop.defaultPrice);
  }, [crop]);

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
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    calculateRoi(
      authToken,
      {
        crop,
        crop_area_ha: area,
        expected_yield_t_ha: yieldTarget,
        expected_sell_price_vnd_per_kg: sellPrice,
        region_id: typeof regionId === "number" ? regionId : null,
        fertilizer_total_cost_vnd_per_ha: mode === "simple" ? fertilizerTotal : null,
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
        other_input_cost_vnd_per_ha: otherCost,
        labor_cost_vnd_per_ha: laborCost,
        save
      },
      controller.signal
    )
      .then(setResult)
      .catch((err) => setError(err instanceof Error ? err.message : "Không tính được lợi nhuận."))
      .finally(() => setLoading(false));
  }

  return (
    <section className={embedded ? "roi-page roi-standard-page advisory-embedded-roi" : "roi-page fertilizer-page roi-standard-page"}>
      {!embedded ? (
        <SeoHead
          title="Ước tính lợi nhuận nông vụ"
          description="Ước tính lợi nhuận theo chi phí phân bón do nông dân tự nhập và dự báo giá nông sản."
          canonical="/roi-uoc-tinh"
        />
      ) : null}

      <header className="fertilizer-hero roi-hero">
        <div className="roi-hero-copy">
          <span className="input-price-kicker">
            <Calculator size={18} />
            Lợi nhuận nông vụ
          </span>
          <h1>Ước tính lợi nhuận nông vụ</h1>
        </div>
      </header>

      {error ? <div className="input-price-error">{error}</div> : null}

      <section className="fertilizer-layout roi-grid">
        <div className="input-price-panel roi-panel">
          <div className="input-section-heading compact roi-section-heading">
            <h2>Thông số nông vụ</h2>
            <p>Chi phí theo mỗi hecta</p>
          </div>
          <div className="roi-form">
            <label>
              Cây trồng
              <select value={crop} onChange={(event) => setCrop(event.target.value as CropType)}>
                {cropOptions.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Vùng sản xuất
              <select value={regionId} onChange={(event) => setRegionId(Number(event.target.value) || "")}>
                {regions.map((region) => (
                  <option key={region.region_id} value={region.region_id}>
                    {region.province ?? region.region_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Diện tích (ha)
              <input type="number" min="0.01" step="0.1" value={area} onChange={(event) => setArea(Number(event.target.value))} />
            </label>
            <label>
              Năng suất kỳ vọng (tấn/ha)
              <input type="number" min="0.1" step="0.1" value={yieldTarget} onChange={(event) => setYieldTarget(Number(event.target.value))} />
            </label>
            <label>
              Giá bán kỳ vọng (VND/kg)
              <MoneyInput value={sellPrice} onValueChange={setSellPrice} />
            </label>
            <label>
              Chi phí vật tư khác/ha
              <MoneyInput value={otherCost} onValueChange={setOtherCost} />
            </label>
            <label>
              Chi phí nhân công/ha
              <MoneyInput value={laborCost} onValueChange={setLaborCost} />
            </label>
          </div>
        </div>

        <div className="input-price-panel roi-panel">
          <div className="input-section-heading compact roi-section-heading roi-fertilizer-heading">
            <h2>Chi phí phân bón</h2>
          </div>
          <div className="roi-mode-toggle" role="tablist" aria-label="Chọn cách nhập chi phí phân bón">
            <button type="button" className={mode === "simple" ? "active" : ""} onClick={() => setMode("simple")}>
              Tổng tiền/ha
            </button>
            <button type="button" className={mode === "detail" ? "active" : ""} onClick={() => setMode("detail")}>
              Từng dòng phân
            </button>
          </div>

          {mode === "simple" ? (
            <div className="roi-form single">
              <label>
                Tổng tiền phân bón đã/sẽ chi mỗi ha
                <MoneyInput value={fertilizerTotal} onValueChange={setFertilizerTotal} />
              </label>
            </div>
          ) : (
            <div className="roi-lines detail">
              {fertilizerLines.map((line, index) => (
                <div className="roi-line detail" key={line.id}>
                  <input aria-label="Tên phân bón" value={line.name} onChange={(event) => updateLine(index, { name: event.target.value })} />
                  <input
                    aria-label="kg mỗi ha"
                    type="number"
                    min="0"
                    step="10"
                    value={line.kg_per_ha}
                    onChange={(event) => updateLine(index, { kg_per_ha: event.target.value })}
                  />
                  <MoneyTextInput
                    ariaLabel="giá mỗi kg"
                    value={line.price_vnd_per_kg}
                    onValueChange={(value) => updateLine(index, { price_vnd_per_kg: value })}
                  />
                  <strong>{formatVnd(positiveNumber(line.kg_per_ha) * positiveMoneyNumber(line.price_vnd_per_kg))}</strong>
                  <button type="button" onClick={() => removeLine(index)} aria-label="Xóa dòng phân bón" title="Xóa dòng phân bón">
                    <X size={16} />
                  </button>
                </div>
              ))}
              <button type="button" className="roi-secondary-button" onClick={addLine}>
                Thêm dòng phân
              </button>
            </div>
          )}

          <a className="roi-world-link" href="/du-bao-gia/phan-bon#world">
            Xem xu hướng Urê/DAP/Kali thế giới
            <ArrowRight size={16} />
          </a>
          <label className="roi-save-option">
            <input type="checkbox" checked={save} onChange={(event) => setSave(event.target.checked)} />
            Lưu kịch bản vào tài khoản
          </label>
          <button type="button" className="roi-primary-button" onClick={submit} disabled={loading}>
            <RefreshCw size={16} />
            {loading ? "Đang tính" : "Tính lợi nhuận"}
          </button>
        </div>
      </section>

      {result ? (
        <>
          <section className="input-stat-grid roi-result-grid">
            <div className="input-stat">
              <Database size={18} />
              <span>Chi phí phân/ha</span>
              <strong>{formatVnd(result.fertilizer_cost_vnd_per_ha)}</strong>
              <small>{result.fertilizer_input_mode === "simple" ? "Tổng tiền anh nhập" : `${result.breakdown.length} dòng phân`}</small>
            </div>
            <div className="input-stat">
              <Calculator size={18} />
              <span>Lợi nhuận kỳ vọng</span>
              <strong>{formatVnd(result.net_profit_vnd)}</strong>
              <small>{result.forecast_model_kind}</small>
            </div>
            <div className="input-stat">
              <Calculator size={18} />
              <span>Tỷ suất lợi nhuận</span>
              <strong className={result.roi_pct >= 0 ? "positive" : "negative"}>{result.roi_pct.toFixed(1)}%</strong>
              <small>Độ tin cậy {Math.round(result.confidence_score * 100)}%</small>
            </div>
          </section>

          <section className="roi-scenario-grid" aria-label="Kịch bản lợi nhuận cơ sở">
            {result.scenarios.map((scenario) => (
              <article key={scenario.scenario} className={`roi-scenario-card ${scenario.scenario}`}>
                <span>{scenario.label_vi}</span>
                <strong className={scenario.roi_pct >= 0 ? "positive" : "negative"}>{scenario.roi_pct.toFixed(1)}%</strong>
                <small>{formatVnd(scenario.net_profit_vnd)}</small>
                <p>{scenario.rationale_vi}</p>
              </article>
            ))}
          </section>

          <section className="input-price-panel input-price-data">
            <div className="input-section-heading compact">
              <h2>Khuyến nghị</h2>
              <p>Rút ra từ chi phí phân bón, dự báo giá nông sản và biên an toàn lợi nhuận</p>
            </div>
            <div className="roi-recommendations">
              {result.recommendations_vi.map((note) => (
                <p key={note}>{note}</p>
              ))}
            </div>
          </section>

          <section className="input-price-panel input-price-data">
            <div className="input-section-heading compact">
              <h2>Độ nhạy lợi nhuận</h2>
              <p>Giá bán ±10%, giá phân bón ±15%</p>
            </div>
            <div className="input-table-wrap">
              <table aria-label="Bảng độ nhạy lợi nhuận">
                <thead>
                  <tr>
                    <th>Giá bán</th>
                    <th>Giá phân</th>
                    <th>Tỷ suất</th>
                    <th>Lợi nhuận ròng</th>
                  </tr>
                </thead>
                <tbody>
                  {sensitivityRows.map((row) => (
                    <tr key={`${row.sell_price_delta_pct}-${row.fertilizer_price_delta_pct}`}>
                      <td>{row.sell_price_delta_pct > 0 ? "+" : ""}{row.sell_price_delta_pct}%</td>
                      <td>{row.fertilizer_price_delta_pct > 0 ? "+" : ""}{row.fertilizer_price_delta_pct}%</td>
                      <td>{row.roi_pct.toFixed(1)}%</td>
                      <td>{formatVnd(row.net_profit_vnd)}</td>
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
