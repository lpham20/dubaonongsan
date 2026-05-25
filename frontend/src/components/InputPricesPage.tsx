import { LineChart, PackageCheck } from "./icons";
import { LivePriceTicker } from "./LivePriceTicker";
import { SeoHead } from "./SeoHead";
import { WorldFertilizerForecastSection } from "./WorldFertilizerForecastSection";
import { useLanguage } from "../contexts/LanguageContext";

export function InputPricesPage() {
  const { language } = useLanguage();
  const isEnglish = language === "en";

  return (
    <section className="input-prices-page world-fertilizer-page">
      <SeoHead
        title={isEnglish ? "World fertilizer price forecast" : "Dự báo giá phân bón thế giới"}
        description={
          isEnglish
            ? "Track global Urea, DAP and MOP fertilizer prices in USD/tonne with a 30-day forecast and daily percentage changes."
            : "Theo dõi giá Urê, DAP và Kali MOP thế giới theo USD/tấn, kèm dự báo 30 ngày và mức tăng giảm mỗi ngày để tham chiếu giá phân bón địa phương."
        }
        canonical="/du-bao-gia/phan-bon"
        schemaJsonLd={{
          "@context": "https://schema.org",
          "@type": "Dataset",
          name: isEnglish ? "World fertilizer price forecast" : "Dự báo giá phân bón thế giới",
          description: isEnglish
            ? "Global fertilizer commodity price data and 30-day forecasts for Urea, DAP and MOP in USD/tonne."
            : "Dữ liệu giá phân bón hàng hóa thế giới và dự báo 30 ngày cho Urê, DAP, Kali MOP theo USD/tấn.",
          url: "https://dubaonongsan.com/du-bao-gia/phan-bon",
          creator: { "@type": "Organization", name: "dubaonongsan.com" }
        }}
      />
      <LivePriceTicker />

      <header className="market-quote-header world-fertilizer-hero">
        <div className="quote-main">
          <div className="quote-title-row">
            <PackageCheck size={20} />
            <h1>
              <span className="quote-h1-line1">{isEnglish ? "World fertilizer prices" : "Giá phân bón thế giới"}</span>
            </h1>
          </div>
          <p>
            {isEnglish
              ? "Track global fertilizer commodity trends and forecasts."
              : "Theo dõi biến động và dự báo giá hàng hóa phân bón thế giới."}
          </p>
        </div>
      </header>

      <nav className="market-subnav" aria-label={isEnglish ? "World fertilizer data" : "Dữ liệu phân bón thế giới"}>
        <button type="button" className="active">
          <LineChart size={15} />
          {isEnglish ? "World forecast" : "Dự báo thế giới"}
        </button>
      </nav>

      <WorldFertilizerForecastSection />
    </section>
  );
}
