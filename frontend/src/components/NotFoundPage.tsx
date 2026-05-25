import { Link } from "react-router-dom";
import { Home, Newspaper, Sprout } from "./icons";
import { Breadcrumb } from "./Breadcrumb";
import { SeoHead } from "./SeoHead";
import { useLanguage } from "../contexts/LanguageContext";
import { withLanguagePrefix } from "../lib/localizedRoutes";

export function NotFoundPage() {
  const { language } = useLanguage();
  const isEnglish = language === "en";
  return (
    <section className="content-page detail-page not-found-page">
      <SeoHead
        title={isEnglish ? "Page not found" : "Không tìm thấy trang"}
        description={isEnglish ? "The page you are looking for does not exist. Return to Agri Price Forecast for market news, farming guides and crop price forecasts." : "Trang bạn tìm không tồn tại. Quay về Dự báo nông sản để xem tin thị trường, hướng dẫn kỹ thuật và dự báo giá nông sản."}
        canonical="/404"
      />
      <Breadcrumb items={[{ label: isEnglish ? "Home" : "Trang chủ", href: "/" }, { label: isEnglish ? "Not found" : "Không tìm thấy" }]} />
      <div className="not-found-card">
        <span>404</span>
        <h1>{isEnglish ? "Page not found" : "Không tìm thấy trang"}</h1>
        <p>{isEnglish ? "This URL does not exist, or the content has moved to another address." : "Đường dẫn này không tồn tại hoặc nội dung đã được chuyển sang địa chỉ khác."}</p>
        <nav>
          <Link to={withLanguagePrefix("/", language)}>
            <Home size={16} />
            {isEnglish ? "Home" : "Trang chủ"}
          </Link>
          <Link to={withLanguagePrefix("/tin-tuc", language)}>
            <Newspaper size={16} />
            {isEnglish ? "Market news" : "Tin tức thị trường"}
          </Link>
          <Link to={withLanguagePrefix("/du-bao-gia/sau_rieng", language)}>
            <Sprout size={16} />
            {isEnglish ? "Crop price forecast" : "Dự báo giá nông sản"}
          </Link>
        </nav>
      </div>
    </section>
  );
}
