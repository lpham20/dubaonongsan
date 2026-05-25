import { memo } from "react";
import { Gauge, LineChart, Ruler, TimerReset } from "./icons";
import type { ModelMetrics } from "../lib/api";
import { useLanguage } from "../contexts/LanguageContext";

type Props = {
  metrics: ModelMetrics | null;
};

function MetricsDashboardComponent({ metrics }: Props) {
  const { language } = useLanguage();
  const locale = language === "en" ? "en-US" : "vi-VN";
  const hasBacktest = Boolean(metrics?.backtest_samples);
  const values = [
    {
      label: "RMSE",
      value: hasBacktest ? `${Math.round(metrics?.rmse_vnd_per_kg ?? 0).toLocaleString(locale)}` : "-",
      suffix: "VND/kg",
      icon: Gauge
    },
    {
      label: "MAE",
      value: hasBacktest ? `${Math.round(metrics?.mae_vnd_per_kg ?? 0).toLocaleString(locale)}` : "-",
      suffix: "VND/kg",
      icon: Ruler
    },
    {
      label: language === "en" ? "Lookback" : "Dữ liệu lùi",
      value: `${metrics?.lookback_days ?? 60}`,
      suffix: language === "en" ? "days" : "ngày",
      icon: TimerReset
    },
    {
      label: language === "en" ? "Forecast" : "Dự báo",
      value: `${metrics?.forecast_horizon_days ?? 30}`,
      suffix: language === "en" ? "days" : "ngày",
      icon: LineChart
    }
  ];

  return (
    <section className="metrics-grid" aria-label={language === "en" ? "Model metrics" : "Chỉ số mô hình"}>
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
