import { memo } from "react";
import { useLanguage } from "../contexts/LanguageContext";
import type { PricePoint } from "../lib/api";
import { displayProvince } from "../lib/displayLabels";

type Props = {
  points: PricePoint[];
};

type DataGridCopy = {
  title: string;
  description: string;
  date: string;
  region: string;
  variety: string;
  grade: string;
  source: string;
  low: string;
  high: string;
  tonnes: string;
  observed: string;
  adjusted: string;
  filled: string;
  cardsLabel: string;
};

function DataGridComponent({ points }: Props) {
  const { language } = useLanguage();
  const copy: DataGridCopy =
    language === "en"
      ? {
          title: "Historical prices by region",
          description: "Daily price data by growing region, variety, grade and data source.",
          date: "Date",
          region: "Region",
          variety: "Variety",
          grade: "Grade",
          source: "Source",
          low: "Low",
          high: "High",
          tonnes: "Tonnes",
          observed: "Observed",
          adjusted: "Adjusted",
          filled: "Filled",
          cardsLabel: "Historical price cards"
        }
      : {
          title: "Bảng giá lịch sử theo vùng",
          description: "Dữ liệu giá theo ngày, vùng trồng, giống, loại hàng và nguồn dữ liệu.",
          date: "Ngày",
          region: "Khu vực",
          variety: "Giống",
          grade: "Loại",
          source: "Nguồn",
          low: "Thấp nhất",
          high: "Cao nhất",
          tonnes: "Tấn",
          observed: "Quan sát",
          adjusted: "Hiệu chỉnh",
          filled: "Nội suy",
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
              <th>{copy.source}</th>
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
                <td>
                  <DataKindBadge row={row} copy={copy} />
                </td>
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
                <dt>{copy.source}</dt>
                <dd>
                  <DataKindBadge row={row} copy={copy} />
                </dd>
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

function DataKindBadge({ row, copy }: { row: PricePoint; copy: DataGridCopy }) {
  const rawKind = (row.data_kind ?? "").toLowerCase();
  const isAdjusted = rawKind.includes("hiệu") || rawKind.includes("adjust") || rawKind.includes("calibrat");
  const isFilled = row.is_synthetic || rawKind.includes("nội") || rawKind.includes("synthetic") || rawKind.includes("interpolat");
  const label = isFilled ? copy.filled : isAdjusted ? copy.adjusted : copy.observed;
  const className = isFilled ? "data-kind-badge filled" : isAdjusted ? "data-kind-badge adjusted" : "data-kind-badge observed";
  return <span className={className}>{label}</span>;
}

export const DataGrid = memo(DataGridComponent);
