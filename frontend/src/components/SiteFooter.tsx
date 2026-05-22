import { FormEvent, useState } from "react";
import { subscribeNewsletter } from "../lib/api";
import { useMediaQuery } from "../hooks/useMediaQuery";

type Props = {
  onOpenNews: () => void;
  onOpenGuides: () => void;
  onOpenAnalytics: () => void;
  onOpenInputPrices: () => void;
};

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function SiteFooter({ onOpenNews, onOpenGuides, onOpenAnalytics, onOpenInputPrices }: Props) {
  const isMobile = useMediaQuery("(max-width: 860px)");
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
        <details className="footer-brand-block site-footer-section" aria-label="Thông tin pháp lý" open={!isMobile}>
          <summary><span className="footer-section-title">Dự báo nông sản</span></summary>
          <p>
            Đây là trang blog cá nhân lưu trữ và phân tích thông tin nông nghiệp nhằm mục đích chia sẻ kiến thức, hỗ trợ bà con nông dân phi lợi nhuận, không phải là cơ quan báo chí.
          </p>
          <a href="mailto:dubaonongsan@gmail.com">dubaonongsan@gmail.com</a>
        </details>

        <details className="footer-links site-footer-section" aria-label="Liên kết nhanh" open={!isMobile}>
          <summary><span className="footer-section-title">Liên kết nhanh</span></summary>
          <a
            href="/tin-tuc"
            onClick={(event) => {
              event.preventDefault();
              onOpenNews();
            }}
          >
            Tin tức thị trường
          </a>
          <a
            href="/huong-dan"
            onClick={(event) => {
              event.preventDefault();
              onOpenGuides();
            }}
          >
            Quy trình kỹ thuật
          </a>
          <a
            href="/du-bao-gia/sau_rieng"
            onClick={(event) => {
              event.preventDefault();
              onOpenAnalytics();
            }}
          >
            Dự báo giá nông sản
          </a>
          <a href="/du-bao-gia/ca_phe">Dự báo giá cà phê</a>
          <a href="/du-bao-gia/ho_tieu">Dự báo giá hồ tiêu</a>
          <a
            href="/du-bao-gia/phan-bon"
            onClick={(event) => {
              event.preventDefault();
              onOpenInputPrices();
            }}
          >
            Giá phân bón đầu vào
          </a>
          <a href="/khuyen-nghi-bon-phan">Khuyến nghị bón phân</a>
          <a href="/bao-cao-nang-suat">Báo cáo năng suất</a>
        </details>

        <details className="footer-subscribe site-footer-section" aria-label="Đăng ký nhận tin" open={!isMobile}>
          <summary><span className="footer-section-title">Nhận tin giá nông sản</span></summary>
          <p>Đừng bỏ lỡ biến động giá nông sản ngày mai. Đăng ký ngay!</p>
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
        </details>
      </div>

      <div className="footer-bottom">© 2026 Dự báo nông sản. All rights reserved.</div>
    </footer>
  );
}
