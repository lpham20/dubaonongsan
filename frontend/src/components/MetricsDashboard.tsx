import { memo } from "react";
import { Gauge, LineChart, Ruler, TimerReset } from "./icons";
import type { ModelMetrics } from "../lib/api";

type Props = {
  metrics: ModelMetrics | null;
};

function MetricsDashboardComponent({ metrics }: Props) {
  const hasBacktest = Boolean(metrics?.backtest_samples);
  const values = [
    {
      label: "RMSE",
      value: hasBacktest ? `${Math.round(metrics?.rmse_vnd_per_kg ?? 0).toLocaleString("vi-VN")}` : "-",
      suffix: "VND/kg",
      icon: Gauge
    },
    {
      label: "MAE",
      value: hasBacktest ? `${Math.round(metrics?.mae_vnd_per_kg ?? 0).toLocaleString("vi-VN")}` : "-",
      suffix: "VND/kg",
      icon: Ruler
    },
    {
      label: "Dữ liệu lùi",
      value: `${metrics?.lookback_days ?? 60}`,
      suffix: "ngày",
      icon: TimerReset
    },
    {
      label: "Dự báo",
      value: `${metrics?.forecast_horizon_days ?? 30}`,
      suffix: "ngày",
      icon: LineChart
    }
  ];

  return (
    <section className="metrics-grid" aria-label="Chỉ số mô hình">
      {values.map((item) => {
        const Icon = item.icon;
        return (
          <article className="metric-card" key={item.label}>
            <Icon size={20} />
            <span>{item.label}</span>
            <strong className="num">{item.value}</strong>
            <small>{item.suffix}</small>
          </article>
        );
      })}
      {metrics?.note ? <p className="metric-note">{metrics.note}</p> : null}
    </section>
  );
}

export const MetricsDashboard = memo(MetricsDashboardComponent);
