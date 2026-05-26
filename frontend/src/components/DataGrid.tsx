import { memo } from "react";
import { useLanguage } from "../contexts/LanguageContext";
import type { PricePoint } from "../lib/api";
import { displayProvince } from "../lib/displayLabels";

type Props = {
  points: PricePoint[];
};

function DataGridComponent({ points }: Props) {
  const { language } = useLanguage();
  const copy = language === "en"
    ? {
        title: "Historical prices by region",
        description: "Daily price data by growing region, variety and grade.",
        date: "Date",
        region: "Region",
        variety: "Variety",
        grade: "Grade",
        low: "Low",
        high: "High",
        tonnes: "Tonnes",
        cardsLabel: "Historical price cards"
      }
    : {
        title: "Bảng giá lịch sử theo vùng",
        description: "Dữ liệu giá theo ngày, vùng trồng, giống và loại hàng.",
        date: "Ngày",
        region: "Khu vực",
        variety: "Giống",
        grade: "Loại",
        low: "Thấp nhất",
        high: "Cao nhất",
        tonnes: "Tấn",
        cardsLabel: "Bảng giá lịch sử dạng thẻ"
      };
  const locale = language === "en" ? "en-US" : "vi-VN";
  const rows = points.slice(-12).reverse();
  return (
    <section className="data-section">
      <div className="section-heading">
        <div>
          <h2>{copy.title}</h2>
          <p>{copy.description}</p>
        </div>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>{copy.date}</th>
              <th>{copy.region}</th>
              <th>{copy.variety}</th>
              <th>{copy.grade}</th>
              <th>{copy.low}</th>
              <th>{copy.high}</th>
              <th>{copy.tonnes}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.timestamp}-${row.quality_grade}-${row.variety}-${displayProvince(row.province, row.region)}`}>
                <td className="num">{new Date(row.timestamp).toLocaleDateString(locale)}</td>
                <td>{displayProvince(row.province, row.region)}</td>
                <td>{row.variety}</td>
                <td>{row.quality_grade}</td>
                <td className="num">{row.min_price_vnd?.toLocaleString(locale)}</td>
                <td className="num">{row.max_price_vnd?.toLocaleString(locale)}</td>
                <td className="num">{row.volume_traded_tons}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mobile-price-cards" aria-label={copy.cardsLabel}>
        {rows.map((row) => (
          <article key={`mobile-${row.timestamp}-${row.quality_grade}-${row.variety}-${displayProvince(row.province, row.region)}`}>
            <div>
              <strong>{row.variety}</strong>
              <span className="num">{new Date(row.timestamp).toLocaleDateString(locale)}</span>
            </div>
            <dl>
              <div>
                <dt>{copy.region}</dt>
                <dd>{displayProvince(row.province, row.region)}</dd>
              </div>
              <div>
                <dt>{copy.grade}</dt>
                <dd>{row.quality_grade}</dd>
              </div>
              <div>
                <dt>{copy.low}</dt>
                <dd className="num">{row.min_price_vnd?.toLocaleString(locale)}</dd>
              </div>
              <div>
                <dt>{copy.high}</dt>
                <dd className="num">{row.max_price_vnd?.toLocaleString(locale)}</dd>
              </div>
            </dl>
          </article>
        ))}
      </div>
    </section>
  );
}

export const DataGrid = memo(DataGridComponent);
