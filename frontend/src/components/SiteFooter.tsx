import { FormEvent, useState } from "react";
import { useLanguage } from "../contexts/LanguageContext";
import { subscribeNewsletter } from "../lib/api";
import { useMediaQuery } from "../hooks/useMediaQuery";

type Props = {
  onOpenNews: () => void;
  onOpenGuides: () => void;
  onOpenAnalytics: () => void;
  onOpenInputPrices: () => void;
};

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const footerCopy = {
  vi: {
    legalLabel: "Thông tin pháp lý",
    brand: "Dự báo nông sản",
    legal:
      "Đây là trang blog cá nhân lưu trữ và phân tích thông tin nông nghiệp nhằm mục đích chia sẻ kiến thức, hỗ trợ bà con nông dân phi lợi nhuận, không phải là cơ quan báo chí.",
    quickLinks: "Liên kết nhanh",
    marketNews: "Tin tức thị trường",
    guides: "Quy trình kỹ thuật",
    agriForecast: "Dự báo giá nông sản",
    coffeeForecast: "Dự báo giá cà phê",
    pepperForecast: "Dự báo giá hồ tiêu",
    fertilizerForecast: "Giá phân bón thế giới",
    fertilizerAdvisory: "Khuyến nghị bón phân",
    yieldFeedback: "Báo cáo năng suất",
    subscribeLabel: "Đăng ký nhận tin",
    subscribeTitle: "Nhận tin giá nông sản",
    subscribeText: "Đừng bỏ lỡ biến động giá nông sản ngày mai. Đăng ký ngay!",
    invalidEmail: "Vui lòng nhập đúng định dạng email.",
    success: "Đã ghi nhận email đăng ký.",
    error: "Chưa thể đăng ký lúc này. Vui lòng thử lại sau.",
    sending: "Đang gửi",
    submit: "Đăng ký",
    rights: "© 2026 Dự báo nông sản. All rights reserved."
  },
  en: {
    legalLabel: "Legal information",
    brand: "Agri Price Forecast",
    legal:
      "This is a personal knowledge site that stores and analyzes agricultural information for educational, non-profit farmer support. It is not a press agency.",
    quickLinks: "Quick links",
    marketNews: "Market news",
    guides: "Technical guides",
    agriForecast: "Agricultural price forecast",
    coffeeForecast: "Coffee price forecast",
    pepperForecast: "Pepper price forecast",
    fertilizerForecast: "World fertilizer prices",
    fertilizerAdvisory: "Fertilizer recommendation",
    yieldFeedback: "Yield feedback",
    subscribeLabel: "Subscribe",
    subscribeTitle: "Agricultural price updates",
    subscribeText: "Get notified before important agricultural price moves. Subscribe now.",
    invalidEmail: "Please enter a valid email address.",
    success: "Your subscription email has been recorded.",
    error: "Subscription is not available right now. Please try again later.",
    sending: "Sending",
    submit: "Subscribe",
    rights: "© 2026 Agri Price Forecast. All rights reserved."
  }
} as const;

export function SiteFooter({ onOpenNews, onOpenGuides, onOpenAnalytics, onOpenInputPrices }: Props) {
  const { language } = useLanguage();
  const copy = footerCopy[language];
  const isMobile = useMediaQuery("(max-width: 860px)");
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedEmail = email.trim().toLowerCase();

    if (!emailPattern.test(normalizedEmail)) {
      setStatus("error");
      setMessage(copy.invalidEmail);
      return;
    }

    setStatus("submitting");
    setMessage("");

    try {
      await subscribeNewsletter(normalizedEmail);
      setStatus("success");
      setEmail("");
      setMessage(copy.success);
    } catch {
      setStatus("error");
      setMessage(copy.error);
    }
  }

  return (
    <footer className="site-footer">
      <div className="site-footer-grid">
        <details className="footer-brand-block site-footer-section" aria-label={copy.legalLabel} open={!isMobile}>
          <summary>
            <span className="footer-section-title">{copy.brand}</span>
          </summary>
          <p>{copy.legal}</p>
          <a href="mailto:dubaonongsan@gmail.com">dubaonongsan@gmail.com</a>
        </details>

        <details className="footer-links site-footer-section" aria-label={copy.quickLinks} open={!isMobile}>
          <summary>
            <span className="footer-section-title">{copy.quickLinks}</span>
          </summary>
          <a
            href="/tin-tuc"
            onClick={(event) => {
              event.preventDefault();
              onOpenNews();
            }}
          >
            {copy.marketNews}
          </a>
          <a
            href="/huong-dan"
            onClick={(event) => {
              event.preventDefault();
              onOpenGuides();
            }}
          >
            {copy.guides}
          </a>
          <a
            href="/du-bao-gia/sau_rieng"
            onClick={(event) => {
              event.preventDefault();
              onOpenAnalytics();
            }}
          >
            {copy.agriForecast}
          </a>
          <a href="/du-bao-gia/ca_phe">{copy.coffeeForecast}</a>
          <a href="/du-bao-gia/ho_tieu">{copy.pepperForecast}</a>
          <a
            href="/du-bao-gia/phan-bon"
            onClick={(event) => {
              event.preventDefault();
              onOpenInputPrices();
            }}
          >
            {copy.fertilizerForecast}
          </a>
          <a href="/khuyen-nghi-bon-phan">{copy.fertilizerAdvisory}</a>
          <a href="/bao-cao-nang-suat">{copy.yieldFeedback}</a>
        </details>

        <details className="footer-subscribe site-footer-section" aria-label={copy.subscribeLabel} open={!isMobile}>
          <summary>
            <span className="footer-section-title">{copy.subscribeTitle}</span>
          </summary>
          <p>{copy.subscribeText}</p>
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
                {status === "submitting" ? copy.sending : copy.submit}
              </button>
            </div>
          </form>
          {message ? (
            <p id="footer-email-feedback" className={`footer-form-message ${status}`}>
              {message}
            </p>
          ) : null}
        </details>
      </div>

      <div className="footer-bottom">{copy.rights}</div>
    </footer>
  );
}
