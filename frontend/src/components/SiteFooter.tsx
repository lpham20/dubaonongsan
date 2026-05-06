import { FormEvent, useState } from "react";
import { subscribeNewsletter } from "../lib/api";

type Props = {
  onOpenNews: () => void;
  onOpenGuides: () => void;
  onOpenAnalytics: () => void;
};

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function SiteFooter({ onOpenNews, onOpenGuides, onOpenAnalytics }: Props) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedEmail = email.trim().toLowerCase();

    if (!emailPattern.test(normalizedEmail)) {
      setStatus("error");
      setMessage("Vui lòng nhập đúng định dạng email.");
      return;
    }

    setStatus("submitting");
    setMessage("");

    try {
      await subscribeNewsletter(normalizedEmail);
      setStatus("success");
      setEmail("");
      setMessage("Đã ghi nhận email đăng ký.");
    } catch {
      setStatus("error");
      setMessage("Chưa thể đăng ký lúc này. Vui lòng thử lại sau.");
    }
  }

  return (
    <footer className="site-footer">
      <div className="site-footer-grid">
        <section className="footer-brand-block" aria-label="Thông tin pháp lý">
          <h2>Dự báo nông sản</h2>
          <p>
            Đây là trang blog cá nhân lưu trữ và phân tích thông tin nông nghiệp nhằm mục đích chia sẻ kiến thức, hỗ trợ bà con nông dân phi lợi nhuận, không phải là cơ quan báo chí.
          </p>
          <a href="mailto:dubaonongsan@gmail.com">dubaonongsan@gmail.com</a>
        </section>

        <nav className="footer-links" aria-label="Liên kết nhanh">
          <h3>Liên kết nhanh</h3>
          <button type="button" onClick={onOpenNews}>Tin tức thị trường</button>
          <button type="button" onClick={onOpenGuides}>Quy trình kỹ thuật</button>
          <button type="button" onClick={onOpenAnalytics}>Dự báo giá nông sản</button>
        </nav>

        <section className="footer-subscribe" aria-label="Đăng ký nhận tin">
          <h3>Đừng bỏ lỡ biến động giá nông sản ngày mai. Đăng ký ngay!</h3>
          <form onSubmit={handleSubmit} noValidate>
            <label htmlFor="footer-email">Email</label>
            <div>
              <input
                id="footer-email"
                name="email"
                type="email"
                autoComplete="email"
                required
                inputMode="email"
                value={email}
                onChange={(event) => {
                  setEmail(event.target.value);
                  if (status !== "submitting") {
                    setStatus("idle");
                    setMessage("");
                  }
                }}
                placeholder="email@example.com"
                aria-invalid={status === "error"}
                aria-describedby={message ? "footer-email-feedback" : undefined}
              />
              <button type="submit" disabled={status === "submitting"}>
                {status === "submitting" ? "Đang gửi" : "Đăng ký"}
              </button>
            </div>
          </form>
          {message ? <p id="footer-email-feedback" className={`footer-form-message ${status}`}>{message}</p> : null}
        </section>
      </div>

      <div className="footer-bottom">© 2026 Dự báo nông sản. All rights reserved.</div>
    </footer>
  );
}
