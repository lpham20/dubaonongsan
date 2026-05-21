import { useMemo, useState } from "react";
import { ClipboardCheck, Leaf } from "./icons";
import { SeoHead } from "./SeoHead";
import { submitYieldFeedback, type YieldFeedbackResponse } from "../lib/api";

type FormState = {
  session_code: string;
  actual_yield_t_ha: string;
  harvest_date: string;
  fertilizer_followed_pct: string;
  rating: string;
  contact_phone: string;
  note: string;
};

const initialSessionCode = new URLSearchParams(window.location.search).get("sid") ?? "";

const initialForm: FormState = {
  session_code: initialSessionCode,
  actual_yield_t_ha: "",
  harvest_date: "",
  fertilizer_followed_pct: "",
  rating: "",
  contact_phone: "",
  note: ""
};

export function YieldFeedbackPage() {
  const [form, setForm] = useState<FormState>(initialForm);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<YieldFeedbackResponse | null>(null);
  const sessionPreview = useMemo(() => form.session_code.trim().slice(0, 8).toUpperCase(), [form.session_code]);

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function submit() {
    setError(null);
    setResult(null);
    const sessionCode = form.session_code.trim();
    const actualYield = numberOrNull(form.actual_yield_t_ha);
    if (sessionCode.length < 8) {
      setError("Vui lòng nhập mã khuyến nghị tối thiểu 8 ký tự.");
      return;
    }
    if (actualYield === null || actualYield <= 0) {
      setError("Vui lòng nhập năng suất thực tế theo tấn/ha.");
      return;
    }
    setBusy(true);
    try {
      const payload = {
        actual_yield_t_ha: actualYield,
        harvest_date: form.harvest_date || null,
        fertilizer_followed_pct: numberOrNull(form.fertilizer_followed_pct),
        rating: numberOrNull(form.rating),
        contact_phone: form.contact_phone.trim() || null,
        note: form.note.trim() || null
      };
      setResult(await submitYieldFeedback(sessionCode, payload));
    } catch (err) {
      console.warn("[YieldFeedbackPage] feedback failed", err);
      setError(err instanceof Error ? err.message : "Không gửi được báo cáo năng suất lúc này.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="fertilizer-page yield-feedback-page">
      <SeoHead
        title="Báo cáo năng suất sau khuyến nghị bón phân"
        description="Gửi năng suất thực tế sau khi dùng khuyến nghị bón phân để Dubaonongsan hiệu chỉnh dữ liệu Tier 2."
        canonical="/bao-cao-nang-suat"
      />
      <header className="fertilizer-hero fertilizer-method-hero">
        <div>
          <h1>Báo cáo năng suất sau khuyến nghị bón phân</h1>
          <p>Dữ liệu thực tế giúp hệ thống so sánh khuyến nghị với kết quả vườn và chuẩn bị hiệu chỉnh Tier 2 cho từng cây, giống và vùng trồng.</p>
        </div>
      </header>

      <div className="yield-feedback-layout">
        <form className="fertilizer-form yield-feedback-form" onSubmit={(event) => { event.preventDefault(); void submit(); }}>
          <section className="fertilizer-form-section">
            <div className="fertilizer-section-title">
              <span className="fertilizer-step-dot">1</span>
              <div>
                <h2><ClipboardCheck size={18} /> Mã khuyến nghị</h2>
                <p>Mã này nằm trong phần kết quả sau khi bấm Tính khuyến nghị.</p>
              </div>
            </div>
            <label>
              Mã phiên
              <input value={form.session_code} onChange={(event) => update("session_code", event.target.value)} autoCapitalize="characters" />
            </label>
          </section>

          <section className="fertilizer-form-section">
            <div className="fertilizer-section-title">
              <span className="fertilizer-step-dot">2</span>
              <div>
                <h2><Leaf size={18} /> Kết quả thu hoạch</h2>
                <p>Nhập số liệu thực tế sau vụ để đối chiếu với khuyến nghị trước đó.</p>
              </div>
            </div>
            <div className="fertilizer-two">
              <label>Năng suất thực tế (tấn/ha)<input value={form.actual_yield_t_ha} onChange={(event) => update("actual_yield_t_ha", event.target.value)} inputMode="decimal" /></label>
              <label>Ngày thu hoạch<input type="date" value={form.harvest_date} onChange={(event) => update("harvest_date", event.target.value)} /></label>
              <label>Mức làm theo khuyến nghị (%)<input value={form.fertilizer_followed_pct} onChange={(event) => update("fertilizer_followed_pct", event.target.value)} inputMode="decimal" /></label>
              <label>Đánh giá 1-5<input value={form.rating} onChange={(event) => update("rating", event.target.value)} inputMode="numeric" /></label>
            </div>
            <label>Số điện thoại liên hệ<input value={form.contact_phone} onChange={(event) => update("contact_phone", event.target.value)} inputMode="tel" /></label>
            <label>Ghi chú<textarea value={form.note} onChange={(event) => update("note", event.target.value)} rows={5} /></label>
          </section>

          <div className="fertilizer-submit-card">
            <button className="fertilizer-submit" type="submit" disabled={busy}>
              <ClipboardCheck size={18} />
              {busy ? "Đang gửi..." : "Gửi báo cáo"}
            </button>
            {error ? <div className="fertilizer-error" role="alert"><strong>Chưa gửi được</strong><span>{error}</span></div> : null}
          </div>
        </form>

        <aside className="fertilizer-panel yield-feedback-summary">
          <h3><ClipboardCheck size={17} /> Phiên đang báo cáo</h3>
          <strong>{sessionPreview || "Chưa nhập mã"}</strong>
          <p>Mỗi mã khuyến nghị có thể cập nhật báo cáo năng suất. Nếu gửi lại, hệ thống ghi nhận bản mới nhất cho cùng phiên.</p>
          {result ? (
            <div className="fertilizer-success" role="status">
              <strong>{result.session_code}</strong>
              <span>{result.message}</span>
            </div>
          ) : null}
        </aside>
      </div>
    </section>
  );
}

function numberOrNull(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed.replace(",", "."));
  return Number.isFinite(parsed) ? parsed : null;
}
