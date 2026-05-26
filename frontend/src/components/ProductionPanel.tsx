import { KeyRound, Play, RefreshCw, ServerCog } from "./icons";
import type { AuthUser, ModelTrainingRun, PlatformJobRun } from "../lib/api";
import { useLanguage } from "../contexts/LanguageContext";

type Props = {
  user: AuthUser | null;
  jobs: PlatformJobRun[];
  modelRuns: ModelTrainingRun[];
  busy: boolean;
  onRefresh: () => void;
  onRunScrape: () => void;
  onRunNews: () => void;
  onRunDataQuality: () => void;
  onRunRetrain: () => void;
};

export function ProductionPanel({
  user,
  jobs,
  modelRuns,
  busy,
  onRefresh,
  onRunScrape,
  onRunNews,
  onRunDataQuality,
  onRunRetrain
}: Props) {
  const { language } = useLanguage();
  if (!user) return null;
  const latestJob = jobs[0];
  const latestModel = modelRuns[0];
  const latestQuality = jobs.find((job) => job.job_name === "data_quality_check");

  return (
    <section className="production-panel">
      <div className="production-head">
        <div>
          <span>
            <ServerCog size={17} />
            Nền tảng vận hành
          </span>
          <h2>Thu thập định kỳ, huấn luyện lại định kỳ và API công khai</h2>
        </div>
        <div className="production-actions">
          <button type="button" onClick={onRefresh} disabled={busy} title="Làm mới trạng thái">
            <RefreshCw size={16} />
          </button>
          <button type="button" onClick={onRunScrape} disabled={busy}>
            <Play size={16} />
            Quét giá
          </button>
          <button type="button" onClick={onRunNews} disabled={busy}>
            <Play size={16} />
            Quét tin tức
          </button>
          <button type="button" onClick={onRunDataQuality} disabled={busy}>
            <Play size={16} />
            Kiểm tra dữ liệu
          </button>
          <button type="button" onClick={onRunRetrain} disabled={busy}>
            <Play size={16} />
            Huấn luyện lại mô hình
          </button>
        </div>
      </div>
      <div className="production-grid">
        <StatusCell
          label="Lần thu thập gần nhất"
          value={latestJob ? formatStatus(latestJob.status) : "Chưa chạy"}
          detail={latestJob ? `${formatJobName(latestJob.job_name)} - ${formatDate(latestJob.started_at, language)}` : "Lịch chạy nền đang chờ chu kỳ"}
        />
        <StatusCell
          label="Kiểm tra dữ liệu gần nhất"
          value={latestQuality ? formatStatus(latestQuality.status) : "Chưa chạy"}
          detail={latestQuality ? formatDate(latestQuality.started_at, language) : "Chạy hằng ngày sau khi thu thập"}
        />
        <StatusCell
          label="Lần huấn luyện mô hình gần nhất"
          value={latestModel ? formatStatus(latestModel.status) : "Chưa chạy"}
          detail={
            latestModel?.rmse_vnd_per_kg
              ? `RMSE ${Math.round(latestModel.rmse_vnd_per_kg).toLocaleString(localeFor(language))} VND/kg`
              : "Có thể chạy thủ công hoặc theo chu kỳ"
          }
        />
        <StatusCell
          label="API công khai"
          value="Đã bật"
          detail="Tiêu đề HTTP x-api-key: marketai-public-demo-key"
        />
        <StatusCell
          label="Tài khoản"
          value={user.display_name}
          detail={user.email}
        />
      </div>
      <div className="public-api-note">
        <KeyRound size={16} />
        `/api/v1/public/prices` và `/api/v1/public/forecast` đã sẵn sàng cho tích hợp ngoài.
      </div>
    </section>
  );
}

function StatusCell({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="status-cell">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

function localeFor(language: "vi" | "en" = "vi") {
  return language === "en" ? "en-US" : "vi-VN";
}

function formatDate(value: string, language: "vi" | "en" = "vi") {
  return new Date(value).toLocaleString(localeFor(language));
}

function formatJobName(value: string) {
  const labels: Record<string, string> = {
    scrape_prices: "Thu thập giá",
    scrape_news: "Thu thập tin tức",
    data_quality_check: "Kiểm tra dữ liệu",
    retrain_models: "Huấn luyện lại mô hình",
    retrain: "Huấn luyện lại mô hình"
  };
  return labels[value] ?? value;
}

function formatStatus(value: string) {
  const labels: Record<string, string> = {
    success: "Hoàn tất",
    completed: "Hoàn tất",
    duplicate: "Trùng dữ liệu",
    empty: "Không có dữ liệu mới",
    skipped: "Bỏ qua",
    failed: "Lỗi",
    error: "Lỗi",
    running: "Đang chạy",
    pending: "Đang chờ"
  };
  return labels[value.toLowerCase()] ?? value;
}
