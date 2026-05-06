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
                <td>{new Date(row.timestamp).toLocaleDateString("vi-VN")}</td>
                <td>{row.province ?? row.region}</td>
                <td>{row.variety}</td>
                <td>{row.quality_grade}</td>
                <td>{row.min_price_vnd?.toLocaleString("vi-VN")}</td>
                <td>{row.max_price_vnd?.toLocaleString("vi-VN")}</td>
                <td>{row.volume_traded_tons}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export const DataGrid = memo(DataGridComponent);
