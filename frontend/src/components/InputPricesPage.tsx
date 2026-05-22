import { LineChart, PackageCheck } from "./icons";
import { SeoHead } from "./SeoHead";
import { WorldFertilizerForecastSection } from "./WorldFertilizerForecastSection";

export function InputPricesPage() {
  return (
    <section className="input-prices-page world-fertilizer-page">
      <SeoHead
        title="Dự báo giá phân bón thế giới"
        description="Theo dõi giá Urê, DAP và Kali MOP thế giới theo USD/tấn, kèm dự báo 30 ngày và mức tăng giảm mỗi ngày để tham chiếu giá phân bón địa phương."
        canonical="/du-bao-gia/phan-bon"
        schemaJsonLd={{
          "@context": "https://schema.org",
          "@type": "Dataset",
          name: "Dự báo giá phân bón thế giới",
          description: "Dữ liệu giá phân bón hàng hóa thế giới và dự báo 30 ngày cho Urê, DAP, Kali MOP theo USD/tấn.",
          url: "https://dubaonongsan.com/du-bao-gia/phan-bon",
          creator: { "@type": "Organization", name: "dubaonongsan.com" }
        }}
      />

      <header className="market-quote-header world-fertilizer-hero">
        <div className="quote-main">
          <div className="quote-title-row">
            <PackageCheck size={20} />
            <h1>
              <span className="quote-h1-line1">Giá phân bón thế giới</span>
              <span className="quote-h1-line2">Dự báo 30 ngày Urê, DAP, Kali</span>
            </h1>
          </div>
          <div className="quote-meta">
            <span>USD/tấn</span>
            <span>Hàng hóa thế giới</span>
            <span>Dự báo 30 ngày</span>
          </div>
          <p>
            Trang này chỉ hiển thị giá phân bón thế giới và dự báo xu hướng tăng giảm. Giá đại lý địa phương không còn được trộn vào chart để tránh nhiễu logic.
          </p>
        </div>

        <div className="quote-side">
          <div className="quote-range">
            <span>Phạm vi</span>
            <strong>Thế giới</strong>
          </div>
          <div className="quote-range">
            <span>Đơn vị</span>
            <strong>USD/tấn</strong>
          </div>
          <div className="quote-range">
            <span>Tín hiệu</span>
            <strong>%/ngày</strong>
          </div>
        </div>
      </header>

      <nav className="market-subnav" aria-label="Dữ liệu phân bón thế giới">
        <button type="button" className="active">
          <LineChart size={15} />
          Dự báo thế giới
        </button>
      </nav>

      <WorldFertilizerForecastSection />
    </section>
  );
}
