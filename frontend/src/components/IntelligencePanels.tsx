import { memo } from "react";
import { AlertTriangle, ArrowDownRight, ArrowUpRight, BadgeCheck, Download, MapPinned, Pin, X } from "./icons";
import type { DataQuality, HeatmapCell, Mover, StrategyAlert } from "../lib/api";
import { useLanguage, type AppLanguage } from "../contexts/LanguageContext";
import { displayProvince } from "../lib/displayLabels";

type Props = {
  quality: DataQuality | null;
  gainers: Mover[];
  losers: Mover[];
  heatmap: HeatmapCell[];
  alerts: StrategyAlert[];
  watchlist: string[];
  onSelectWatch: (key: string) => void;
  onRemoveWatch: (key: string) => void;
  exportUrl: string;
  exportXlsxUrl: string;
  exportPdfUrl: string;
};

const money = (value: number, language: AppLanguage = "vi") => `${Math.round(value).toLocaleString(language === "en" ? "en-US" : "vi-VN")} VND/kg`;

function IntelligencePanelsComponent({
  quality,
  gainers,
  losers,
  heatmap,
  alerts,
  watchlist,
  onSelectWatch,
  onRemoveWatch,
  exportUrl,
  exportXlsxUrl,
  exportPdfUrl
}: Props) {
  const { language } = useLanguage();
  return (
    <section className="terminal-intel intel-grid">
      <article className="terminal-panel intel-panel data-quality">
        <div className="terminal-panel-head panel-heading">
          <BadgeCheck size={18} />
          <h3>{language === "en" ? "Data confidence" : "Độ tin cậy dữ liệu"}</h3>
        </div>
        <div className="quality-score num">{quality?.score ?? "-"}<span>/100</span></div>
        <p>{language === "en" ? "Data quality is scored from source coverage, history depth and observed-versus-filled points." : quality?.note ?? "Đang tính chất lượng dữ liệu."}</p>
        <div className="quality-tags">
          <span>{quality?.source_count ?? 0} {language === "en" ? "sources" : "nguồn"}</span>
          <span>{quality?.history_points ?? 0} {language === "en" ? "points" : "điểm"}</span>
          <span>{quality?.observed_points ?? 0} {language === "en" ? "observed" : "quan sát"}</span>
          <span>{quality?.synthetic_points ?? 0} {language === "en" ? "filled" : "nội suy"}</span>
        </div>
        {quality?.risk_flags?.length ? (
          <div className="risk-flags">
            {quality.risk_flags.map((flag) => (
              <span key={flag}>{flag}</span>
            ))}
          </div>
        ) : null}
        <div className="export-actions">
          <a className="export-link" href={exportUrl}>
            <Download size={16} />
            CSV
          </a>
          <a className="export-link" href={exportXlsxUrl}>
            Excel
          </a>
          <a className="export-link" href={exportPdfUrl}>
            PDF
          </a>
        </div>
      </article>

      <article className="terminal-panel intel-panel">
        <div className="terminal-panel-head panel-heading">
          <Pin size={18} />
          <h3>{language === "en" ? "Watchlist" : "Danh sách ghim"}</h3>
        </div>
        {watchlist.length ? (
          <div className="watchlist">
            {watchlist.map((item) => {
              const label = item.split("|")[3] ?? item;
              return (
                <span className="watchlist-item" key={item}>
                  <button type="button" onClick={() => onSelectWatch(item)}>
                    {label}
                  </button>
                  <button
                    type="button"
                    className="watchlist-remove-button"
                    onClick={() => onRemoveWatch(item)}
                    aria-label={language === "en" ? `Remove ${label} from watchlist` : `Xóa ${label} khỏi danh sách ghim`}
                    title={language === "en" ? "Remove pinned market" : "Xóa mục ghim"}
                  >
                    <X size={13} />
                  </button>
                </span>
              );
            })}
          </div>
        ) : (
          <p>{language === "en" ? "No markets pinned yet." : "Chưa có thị trường nào được ghim."}</p>
        )}
      </article>

      <article className="terminal-panel intel-panel movers-panel">
        <div className="terminal-panel-head panel-heading">
          <ArrowUpRight size={18} />
          <h3>{language === "en" ? "Strong gainers" : "Tăng mạnh"}</h3>
        </div>
        <MoverList rows={gainers} positive />
      </article>

      <article className="terminal-panel intel-panel movers-panel">
        <div className="terminal-panel-head panel-heading">
          <ArrowDownRight size={18} />
          <h3>{language === "en" ? "Strong decliners" : "Giảm mạnh"}</h3>
        </div>
        <MoverList rows={losers} />
      </article>

      <article className="terminal-panel intel-panel heatmap-panel">
        <div className="terminal-panel-head panel-heading">
          <MapPinned size={18} />
          <h3>{language === "en" ? "Regional heatmap" : "Bản đồ nhiệt vùng"}</h3>
        </div>
        <div className="heatmap-list">
          {heatmap.slice(0, 10).map((cell) => (
            <div className="heatmap-row" key={`${cell.region_id}-${cell.province}`}>
              <span>{displayProvince(cell.province, cell.region)}</span>
              <strong className="num">{money(cell.avg_price_vnd, language)}</strong>
              <em className={cell.change_pct >= 0 ? "pos num" : "neg num"}>
                {cell.change_pct >= 0 ? "+" : ""}
                {cell.change_pct}%
              </em>
            </div>
          ))}
        </div>
      </article>

      <article className="terminal-panel intel-panel alerts-panel">
        <div className="terminal-panel-head panel-heading">
          <AlertTriangle size={18} />
          <h3>{language === "en" ? "Strategy alerts" : "Cảnh báo chiến lược"}</h3>
        </div>
        <div className="alerts-list">
          {alerts.map((alert) => (
            <div className="alert-row" key={`${alert.level}-${alert.title}`}>
              <span>{alert.level}</span>
              <strong>{language === "en" ? "Market alert" : alert.title}</strong>
              <p>{language === "en" ? "Review the current price, trend and forecast range before making a sales decision." : alert.message}</p>
            </div>
          ))}
        </div>
      </article>
    </section>
  );
}

export const IntelligencePanels = memo(IntelligencePanelsComponent);

function MoverList({ rows, positive = false }: { rows: Mover[]; positive?: boolean }) {
  return (
    <div className="mover-list">
      {rows.slice(0, 5).map((row) => (
        <div className="mover-row" key={`${row.province}-${row.variety}`}>
          <div>
            <strong>{displayProvince(row.province, row.region)}</strong>
            <span>{row.variety}</span>
          </div>
          <em className={positive ? "pos num" : "neg num"}>
            {row.change_pct >= 0 ? "+" : ""}
            {row.change_pct}%
          </em>
        </div>
      ))}
    </div>
  );
}
