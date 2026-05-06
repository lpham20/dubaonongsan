import { memo } from "react";
import { AlertTriangle, ArrowDownRight, ArrowUpRight, BadgeCheck, Download, MapPinned, Pin } from "./icons";
import type { DataQuality, HeatmapCell, Mover, StrategyAlert } from "../lib/api";

type Props = {
  quality: DataQuality | null;
  gainers: Mover[];
  losers: Mover[];
  heatmap: HeatmapCell[];
  alerts: StrategyAlert[];
  watchlist: string[];
  onSelectWatch: (key: string) => void;
  exportUrl: string;
  exportXlsxUrl: string;
  exportPdfUrl: string;
};

const money = (value: number) => `${Math.round(value).toLocaleString("vi-VN")} VND/kg`;

function IntelligencePanelsComponent({
  quality,
  gainers,
  losers,
  heatmap,
  alerts,
  watchlist,
  onSelectWatch,
  exportUrl,
  exportXlsxUrl,
  exportPdfUrl
}: Props) {
  return (
    <section className="intel-grid">
      <article className="intel-panel data-quality">
        <div className="panel-heading">
          <BadgeCheck size={18} />
          <h3>Độ tin cậy dữ liệu</h3>
        </div>
        <div className="quality-score">{quality?.score ?? "-"}<span>/100</span></div>
        <p>{quality?.note ?? "Đang tính chất lượng dữ liệu."}</p>
        <div className="quality-tags">
          <span>{quality?.source_count ?? 0} nguồn</span>
          <span>{quality?.history_points ?? 0} điểm</span>
          <span>{quality?.observed_points ?? 0} quan sát</span>
          <span>{quality?.synthetic_points ?? 0} nội suy</span>
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

      <article className="intel-panel">
        <div className="panel-heading">
          <Pin size={18} />
          <h3>Danh sách ghim</h3>
        </div>
        {watchlist.length ? (
          <div className="watchlist">
            {watchlist.map((item) => {
              const label = item.split("|")[3] ?? item;
              return (
                <button type="button" key={item} onClick={() => onSelectWatch(item)}>
                  {label}
                </button>
              );
            })}
          </div>
        ) : (
          <p>Chưa có thị trường nào được ghim.</p>
        )}
      </article>

      <article className="intel-panel movers-panel">
        <div className="panel-heading">
          <ArrowUpRight size={18} />
          <h3>Tăng mạnh</h3>
        </div>
        <MoverList rows={gainers} positive />
      </article>

      <article className="intel-panel movers-panel">
        <div className="panel-heading">
          <ArrowDownRight size={18} />
          <h3>Giảm mạnh</h3>
        </div>
        <MoverList rows={losers} />
      </article>

      <article className="intel-panel heatmap-panel">
        <div className="panel-heading">
          <MapPinned size={18} />
          <h3>Bản đồ nhiệt vùng</h3>
        </div>
        <div className="heatmap-list">
          {heatmap.slice(0, 10).map((cell) => (
            <div className="heatmap-row" key={`${cell.region_id}-${cell.province}`}>
              <span>{cell.province ?? cell.region}</span>
              <strong>{money(cell.avg_price_vnd)}</strong>
              <em className={cell.change_pct >= 0 ? "positive" : "negative"}>
                {cell.change_pct >= 0 ? "+" : ""}
                {cell.change_pct}%
              </em>
            </div>
          ))}
        </div>
      </article>

      <article className="intel-panel alerts-panel">
        <div className="panel-heading">
          <AlertTriangle size={18} />
          <h3>Cảnh báo chiến lược</h3>
        </div>
        <div className="alerts-list">
          {alerts.map((alert) => (
            <div className="alert-row" key={`${alert.level}-${alert.title}`}>
              <span>{alert.level}</span>
              <strong>{alert.title}</strong>
              <p>{alert.message}</p>
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
            <strong>{row.province ?? row.region}</strong>
            <span>{row.variety}</span>
          </div>
          <em className={positive ? "positive" : "negative"}>
            {row.change_pct >= 0 ? "+" : ""}
            {row.change_pct}%
          </em>
        </div>
      ))}
    </div>
  );
}
