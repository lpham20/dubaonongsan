import { memo } from "react";
import { BarChart3, Brain, GitCompareArrows } from "./icons";
import type { ChangeExplanation, MarketComparison, MarketIndex } from "../lib/api";
import { useLanguage } from "../contexts/LanguageContext";

type Props = {
  marketIndex: MarketIndex | null;
  explanation: ChangeExplanation | null;
  comparison: MarketComparison | null;
};

const money = (value: number, language: "vi" | "en") => `${Math.round(value).toLocaleString(language === "en" ? "en-US" : "vi-VN")} VND/kg`;

function MarketBrainComponent({ marketIndex, explanation, comparison }: Props) {
  const { language } = useLanguage();
  return (
    <section className="brain-grid">
      <article className="brain-panel index-panel">
        <div className="panel-heading">
          <BarChart3 size={18} />
          <h3>{marketIndex?.name ?? "Chỉ số thị trường"}</h3>
        </div>
        <strong className="brain-number">{money(marketIndex?.latest_value_vnd ?? 0, language)}</strong>
        <span className={(marketIndex?.change_pct_7d ?? 0) >= 0 ? "positive" : "negative"}>
          {(marketIndex?.change_pct_7d ?? 0) >= 0 ? "+" : ""}
          {marketIndex?.change_pct_7d ?? 0}% / 7 ngày
        </span>
      </article>

      <article className="brain-panel explanation-panel">
        <div className="panel-heading">
          <Brain size={18} />
          <h3>Vì sao giá biến động?</h3>
        </div>
        <p>{explanation?.summary ?? "Đang phân tích biến động."}</p>
        <div className="driver-list">
          {explanation?.drivers.slice(0, 3).map((driver) => (
            <div className="driver-row" key={driver.name}>
              <strong>{driver.name}</strong>
              <span>{driver.direction}</span>
              <p>{driver.detail}</p>
            </div>
          ))}
        </div>
        <div className="recommendation">{explanation?.recommendation}</div>
      </article>

      <article className="brain-panel compare-panel">
        <div className="panel-heading">
          <GitCompareArrows size={18} />
          <h3>So sánh vùng cùng giống</h3>
        </div>
        <div className="compare-list">
          {comparison?.peers.slice(0, 6).map((peer) => (
            <div className="compare-row" key={peer.label}>
              <span>{peer.label}</span>
              <strong>{money(peer.avg_price_vnd, language)}</strong>
              <em className={peer.premium_pct >= 0 ? "positive" : "negative"}>
                {peer.premium_pct >= 0 ? "+" : ""}
                {peer.premium_pct}%
              </em>
            </div>
          ))}
        </div>
      </article>
    </section>
  );
}

export const MarketBrain = memo(MarketBrainComponent);
