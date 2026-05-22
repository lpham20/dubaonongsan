import { useEffect, useMemo, useState } from "react";
import { Calculator, Database, RefreshCw, X } from "./icons";
import { SeoHead } from "./SeoHead";
import {
  calculateRoi,
  fetchAgriInputProducts,
  type AgriInputProduct,
  type CropType,
  type RoiCalculateResponse
} from "../lib/api";

const cropOptions: { value: CropType; label: string; defaultYield: number; defaultPrice: number }[] = [
  { value: "ca_phe", label: "Cà phê", defaultYield: 3.5, defaultPrice: 95_000 },
  { value: "sau_rieng", label: "Sầu riêng", defaultYield: 18, defaultPrice: 72_000 },
  { value: "ho_tieu", label: "Hồ tiêu", defaultYield: 2.6, defaultPrice: 135_000 },
  { value: "lua", label: "Lúa", defaultYield: 6.5, defaultPrice: 8_500 }
];

function formatVnd(value: number | null | undefined) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "Đang cập nhật";
  return `${Math.round(value).toLocaleString("vi-VN")} đ`;
}

type FertilizerLineState = {
  product_slug: string;
  kg_per_ha: number;
};

export function RoiCalculatorPage({
  authToken,
  onRequireAuth
}: {
  authToken: string | null;
  onRequireAuth: () => void;
}) {
  const [products, setProducts] = useState<AgriInputProduct[]>([]);
  const [crop, setCrop] = useState<CropType>("ca_phe");
  const selectedCrop = cropOptions.find((item) => item.value === crop) ?? cropOptions[0];
  const [area, setArea] = useState(2);
  const [yieldTarget, setYieldTarget] = useState(selectedCrop.defaultYield);
  const [sellPrice, setSellPrice] = useState(selectedCrop.defaultPrice);
  const [otherCost, setOtherCost] = useState(5_000_000);
  const [laborCost, setLaborCost] = useState(8_000_000);
  const [fertilizerLines, setFertilizerLines] = useState<FertilizerLineState[]>([
    { product_slug: "ure", kg_per_ha: 300 },
    { product_slug: "kali-mop", kg_per_ha: 200 }
  ]);
  const [save, setSave] = useState(false);
  const [result, setResult] = useState<RoiCalculateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchAgriInputProducts(controller.signal)
      .then(setProducts)
      .catch(() => undefined);
    return () => controller.abort();
  }, []);

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
    const productSlug = products[0]?.slug ?? "ure";
    setFertilizerLines((current) => [...current, { product_slug: productSlug, kg_per_ha: 100 }].slice(0, 20));
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
        fertilizer_lines: fertilizerLines.filter((line) => line.kg_per_ha > 0),
        other_input_cost_vnd_per_ha: otherCost,
        labor_cost_vnd_per_ha: laborCost,
        save
      },
      controller.signal
    )
      .then(setResult)
      .catch((err) => setError(err instanceof Error ? err.message : "Không tính được ROI."))
      .finally(() => setLoading(false));
  }

  return (
    <section className="roi-page input-prices-page">
      <SeoHead
        title="Ước tính ROI nông vụ"
        description="Tính nhanh doanh thu, chi phí phân bón và ROI dự kiến dựa trên giá vật tư đầu vào mới nhất."
        canonical="/roi-uoc-tinh"
      />

      <header className="input-price-hero">
        <div>
          <span className="input-price-kicker">
            <Calculator size={18} />
            ROI nông vụ
          </span>
          <h1>Ước tính ROI</h1>
          <p>
            <span>Dựa trên giá phân bón mới nhất.</span>
            <span>So nhanh lợi nhuận theo năng suất và giá bán kỳ vọng.</span>
          </p>
        </div>
        <div className="input-price-head-metrics" aria-label="Tổng quan ROI">
          <div>
            <span>Diện tích</span>
            <strong>{area.toLocaleString("vi-VN")} ha</strong>
          </div>
          <div>
            <span>Năng suất</span>
            <strong>{yieldTarget.toLocaleString("vi-VN")} t/ha</strong>
          </div>
          <div>
            <span>Giá bán</span>
            <strong>{formatVnd(sellPrice)}</strong>
          </div>
        </div>
      </header>

      {error ? <div className="input-price-error">{error}</div> : null}

      <section className="input-price-grid roi-grid">
        <div className="input-price-panel">
          <div className="input-section-heading compact">
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
              Diện tích (ha)
              <input type="number" min="0.01" step="0.1" value={area} onChange={(event) => setArea(Number(event.target.value))} />
            </label>
            <label>
              Năng suất kỳ vọng (tấn/ha)
              <input type="number" min="0.1" step="0.1" value={yieldTarget} onChange={(event) => setYieldTarget(Number(event.target.value))} />
            </label>
            <label>
              Giá bán kỳ vọng (VND/kg)
              <input type="number" min="100" step="500" value={sellPrice} onChange={(event) => setSellPrice(Number(event.target.value))} />
            </label>
            <label>
              Chi phí vật tư khác/ha
              <input type="number" min="0" step="100000" value={otherCost} onChange={(event) => setOtherCost(Number(event.target.value))} />
            </label>
            <label>
              Chi phí nhân công/ha
              <input type="number" min="0" step="100000" value={laborCost} onChange={(event) => setLaborCost(Number(event.target.value))} />
            </label>
          </div>
        </div>

        <div className="input-price-panel">
          <div className="input-section-heading compact">
            <h2>Phân bón sử dụng</h2>
            <p>{fertilizerLines.length} dòng vật tư</p>
          </div>
          <div className="roi-lines">
            {fertilizerLines.map((line, index) => (
              <div className="roi-line" key={`${line.product_slug}-${index}`}>
                <select value={line.product_slug} onChange={(event) => updateLine(index, { product_slug: event.target.value })}>
                  {products.map((product) => (
                    <option key={product.slug} value={product.slug}>
                      {product.name}
                    </option>
                  ))}
                </select>
                <input
                  aria-label="kg mỗi ha"
                  type="number"
                  min="0"
                  step="10"
                  value={line.kg_per_ha}
                  onChange={(event) => updateLine(index, { kg_per_ha: Number(event.target.value) })}
                />
                <button type="button" onClick={() => removeLine(index)} aria-label="Xóa dòng phân bón" title="Xóa dòng phân bón">
                  <X size={16} />
                </button>
              </div>
            ))}
            <button type="button" className="roi-secondary-button" onClick={addLine}>
              Thêm dòng
            </button>
            <label className="roi-save-option">
              <input type="checkbox" checked={save} onChange={(event) => setSave(event.target.checked)} />
              Lưu kịch bản vào tài khoản
            </label>
            <button type="button" className="roi-primary-button" onClick={submit} disabled={loading}>
              <RefreshCw size={16} />
              {loading ? "Đang tính" : "Tính ROI"}
            </button>
          </div>
        </div>
      </section>

      {result ? (
        <section className="input-stat-grid roi-result-grid">
          <div className="input-stat">
            <Database size={18} />
            <span>Chi phí phân/ha</span>
            <strong>{formatVnd(result.fertilizer_cost_vnd_per_ha)}</strong>
            <small>{result.breakdown.length} dòng</small>
          </div>
          <div className="input-stat">
            <Calculator size={18} />
            <span>Tổng chi phí</span>
            <strong>{formatVnd(result.total_cost_vnd)}</strong>
            <small>Toàn diện tích</small>
          </div>
          <div className="input-stat">
            <Calculator size={18} />
            <span>Lợi nhuận ròng</span>
            <strong>{formatVnd(result.net_profit_vnd)}</strong>
            <small>{result.scenario_id ? `Đã lưu #${result.scenario_id}` : "Chưa lưu"}</small>
          </div>
          <div className="input-stat">
            <Calculator size={18} />
            <span>ROI</span>
            <strong className={result.roi_pct >= 0 ? "positive" : "negative"}>{result.roi_pct.toFixed(1)}%</strong>
            <small>{selectedCrop.label}</small>
          </div>
        </section>
      ) : null}

      {result ? (
        <section className="input-price-panel input-price-data">
          <div className="input-section-heading compact">
            <h2>Độ nhạy ROI</h2>
            <p>Giá bán ±10%, giá phân bón ±15%</p>
          </div>
          <div className="input-table-wrap">
            <table aria-label="Bảng độ nhạy ROI">
              <thead>
                <tr>
                  <th>Giá bán</th>
                  <th>Giá phân</th>
                  <th>ROI</th>
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
          <div className="input-price-note roi-notes">
            {result.notes_vi.map((note) => (
              <p key={note}>{note}</p>
            ))}
          </div>
        </section>
      ) : null}
    </section>
  );
}
