import { memo } from "react";
import type { PricePoint } from "../lib/api";

type Props = {
  points: PricePoint[];
};

function DataGridComponent({ points }: Props) {
  const rows = points.slice(-12).reverse();
  return (
    <section className="data-section">
      <div className="section-heading">
        <div>
          <h2>Bảng giá lịch sử theo vùng</h2>
          <p>Dữ liệu giá theo ngày, vùng trồng, giống và loại hàng.</p>
        </div>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Ngày</th>
              <th>Khu vực</th>
              <th>Giống</th>
              <th>Loại</th>
              <th>Thấp nhất</th>
              <th>Cao nhất</th>
              <th>Tấn</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.timestamp}-${row.quality_grade}-${row.variety}-${row.province ?? row.region}`}>
                <td className="num">{new Date(row.timestamp).toLocaleDateString("vi-VN")}</td>
                <td>{row.province ?? row.region}</td>
                <td>{row.variety}</td>
                <td>{row.quality_grade}</td>
                <td className="num">{row.min_price_vnd?.toLocaleString("vi-VN")}</td>
                <td className="num">{row.max_price_vnd?.toLocaleString("vi-VN")}</td>
                <td className="num">{row.volume_traded_tons}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mobile-price-cards" aria-label="Bảng giá lịch sử dạng thẻ">
        {rows.map((row) => (
          <article key={`mobile-${row.timestamp}-${row.quality_grade}-${row.variety}-${row.province ?? row.region}`}>
            <div>
              <strong>{row.variety}</strong>
              <span className="num">{new Date(row.timestamp).toLocaleDateString("vi-VN")}</span>
            </div>
            <dl>
              <div>
                <dt>Khu vực</dt>
                <dd>{row.province ?? row.region}</dd>
              </div>
              <div>
                <dt>Loại</dt>
                <dd>{row.quality_grade}</dd>
              </div>
              <div>
                <dt>Thấp nhất</dt>
                <dd className="num">{row.min_price_vnd?.toLocaleString("vi-VN")}</dd>
              </div>
              <div>
                <dt>Cao nhất</dt>
                <dd className="num">{row.max_price_vnd?.toLocaleString("vi-VN")}</dd>
              </div>
            </dl>
          </article>
        ))}
      </div>
    </section>
  );
}

export const DataGrid = memo(DataGridComponent);
