import { Link } from "react-router-dom";
import { Home, Newspaper, Sprout } from "./icons";
import { Breadcrumb } from "./Breadcrumb";
import { SeoHead } from "./SeoHead";

export function NotFoundPage() {
  return (
    <section className="content-page detail-page not-found-page">
      <SeoHead
        title="Không tìm thấy trang"
        description="Trang bạn tìm không tồn tại. Quay về Dự báo nông sản để xem tin thị trường, hướng dẫn kỹ thuật và dự báo giá nông sản."
        canonical="/404"
      />
      <Breadcrumb items={[{ label: "Trang chủ", href: "/" }, { label: "Không tìm thấy" }]} />
      <div className="not-found-card">
        <span>404</span>
        <h1>Không tìm thấy trang</h1>
        <p>Đường dẫn này không tồn tại hoặc nội dung đã được chuyển sang địa chỉ khác.</p>
        <nav>
          <Link to="/">
            <Home size={16} />
            Trang chủ
          </Link>
          <Link to="/tin-tuc">
            <Newspaper size={16} />
            Tin tức thị trường
          </Link>
          <Link to="/du-bao-gia/sau_rieng">
            <Sprout size={16} />
            Dự báo giá nông sản
          </Link>
        </nav>
      </div>
    </section>
  );
}
