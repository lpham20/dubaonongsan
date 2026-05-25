import { BookOpenCheck, Calculator, ClipboardCheck, Leaf, ShieldCheck } from "./icons";
import { SeoHead } from "./SeoHead";
import { useLanguage } from "../contexts/LanguageContext";

const stepsVi = [
  {
    title: "1. Phân loại đất theo ngưỡng dinh dưỡng",
    text: "Hệ thống đọc pH KCl, đạm tổng số, lân dễ tiêu, kali trao đổi, chất hữu cơ và loại đất. Mỗi chỉ tiêu được xếp vào nhóm thấp, trung bình hoặc cao theo ngưỡng nghiên cứu cho từng cây."
  },
  {
    title: "2. Chọn liều nền theo cây trồng và năng suất mục tiêu",
    text: "Vườn kinh doanh dùng ma trận liều nền theo cây trồng, loại đất và mức dinh dưỡng. Nếu năng suất mục tiêu cao hơn mức chuẩn, hệ thống cộng thêm phần dinh dưỡng cần bù cho sản lượng tăng thêm."
  },
  {
    title: "3. Hiệu chỉnh theo điều kiện thực tế của vườn",
    text: "Liều nền được nhân với các hệ số về pH, lượng mưa, nước tưới, độ dốc, tuổi vườn, kết cấu đất và chất hữu cơ. Hệ số tổng được chặn trong khoảng an toàn để tránh khuyến nghị quá cực đoan."
  },
  {
    title: "4. Quy đổi sang phân thương mại",
    text: "Sau khi có lượng hoạt chất N, P2O5 và K2O, hệ thống quy đổi sang Urê 46% N, DAP 18-46 và nguồn kali phù hợp. Với sầu riêng giai đoạn nuôi trái, nếu chọn KCl hệ thống tự đổi sang K2SO4."
  }
];

const stepsEn = [
  {
    title: "1. Classify soil fertility indicators",
    text: "The system reads pH KCl, total nitrogen, available phosphorus, exchangeable potassium, organic matter and soil type. Each indicator is grouped as low, medium or high using crop-specific reference thresholds."
  },
  {
    title: "2. Select a base rate by crop and target yield",
    text: "Bearing orchards use a base-rate matrix by crop, soil type and fertility level. If the target yield is higher than the reference yield, the system adds nutrients needed for the extra production."
  },
  {
    title: "3. Adjust for real orchard conditions",
    text: "The base rate is adjusted for pH, rainfall, irrigation, slope, orchard age, soil texture and organic matter. The combined factor is capped within a safe range to avoid extreme recommendations."
  },
  {
    title: "4. Convert active nutrients to commercial fertilizer",
    text: "After calculating active N, P2O5 and K2O, the system converts them to Urea 46% N, DAP 18-46 and the selected potassium source. For durian during fruit filling, KCl is replaced by K2SO4 when needed."
  }
];

export function FertilizerMethodology() {
  const { language } = useLanguage();
  const isEnglish = language === "en";
  const steps = isEnglish ? stepsEn : stepsVi;

  return (
    <section className="fertilizer-page fertilizer-method-page">
      <SeoHead
        title={isEnglish ? "How fertilizer recommendations are calculated" : "Giải thích logic tính khuyến nghị bón phân"}
        description={isEnglish ? "How Dubaonongsan turns soil-test data, target yield and orchard conditions into commercial fertilizer recommendations." : "Cách Dubaonongsan tính khuyến nghị bón phân từ phân tích đất, năng suất mục tiêu, điều kiện vườn và quy đổi sang phân thương mại."}
        canonical="/khuyen-nghi-bon-phan/logic"
      />
      <header className="fertilizer-hero fertilizer-method-hero">
        <div>
          <h1>{isEnglish ? "How the fertilizer recommendation is calculated" : "Giải thích logic chi tiết cách tính khuyến nghị bón phân"}</h1>
          <p>{isEnglish ? "The calculation is designed so growers can audit each step: soil indicators, base rates, adjustment factors and the final commercial fertilizer split." : "Cách tính được thiết kế để người trồng có thể kiểm tra từng bước: từ chỉ tiêu đất, liều nền, hệ số hiệu chỉnh đến lượng phân thương mại cần bón theo từng đợt."}</p>
        </div>
      </header>

      <div className="methodology-article fertilizer-methodology-article">
        <section>
          <span className="method-kicker"><Calculator size={18} /> {isEnglish ? "General formula" : "Công thức tổng quát"}</span>
          <h2>{isEnglish ? "Active nutrient rate before conversion" : "Liều hoạt chất trước khi quy đổi"}</h2>
          <div className="formula-card">
            {isEnglish ? "Final rate = Base rate by soil and yield x pH factor x water factor x soil-texture factor x slope factor x orchard-age factor x organic-matter factor" : "Liều cuối = Liều nền theo đất và năng suất x Hệ số pH x Hệ số nước x Hệ số kết cấu đất x Hệ số độ dốc x Hệ số tuổi vườn x Hệ số hữu cơ"}
          </div>
          <p>
            {isEnglish ? "The final rate is the active nutrient amount in kg/ha/year. Only after this step does the system convert it to commercial fertilizer rates that are easier to apply in the orchard." : "Liều cuối là lượng hoạt chất tính theo kg/ha/năm. Sau bước này, hệ thống mới quy đổi ra lượng phân thương mại để người dùng dễ áp dụng ngoài vườn."}
          </p>
        </section>

        <section className="method-step-grid">
          {steps.map((step) => (
            <article key={step.title}>
              <BookOpenCheck size={18} />
              <h3>{step.title}</h3>
              <p>{step.text}</p>
            </article>
          ))}
        </section>

        <section>
          <span className="method-kicker"><ClipboardCheck size={18} /> {isEnglish ? "Commercial fertilizer conversion" : "Quy đổi phân thương mại"}</span>
          <h2>{isEnglish ? "Converting active nutrients to kg fertilizer/ha" : "Cách đổi hoạt chất sang kg phân/ha"}</h2>
          <div className="formula-card">
            {isEnglish ? "DAP = P2O5 / 0.46; Nitrogen from DAP = DAP x 0.18; Urea = remaining Nitrogen / 0.463; KCl Potash = K2O / 0.60 or K2SO4 = K2O / 0.50" : "DAP = P2O5 / 0,46; Đạm từ DAP = DAP x 0,18; Urê = phần Đạm còn lại / 0,463; Kali KCl = K2O / 0,60 hoặc K2SO4 = K2O / 0,50"}
          </div>
          <p>
            {isEnglish ? "For example, 100 kg P2O5/ha converts to about 217 kg DAP/ha. Nitrogen supplied by DAP is subtracted before additional Urea is calculated, which helps avoid excess nitrogen." : "Ví dụ nếu cần 100 kg P2O5/ha, hệ thống quy đổi khoảng 217 kg DAP/ha. Lượng đạm có sẵn trong DAP sẽ được trừ trước khi tính thêm Urê, để tránh bón thừa đạm."}
          </p>
        </section>

        <section className="method-note-grid">
          <article>
            <ShieldCheck size={20} />
            <h3>{isEnglish ? "Safety caps" : "Chặn ngưỡng an toàn"}</h3>
            <p>{isEnglish ? "Bearing durian is capped at 300 kg N/ha/year, 200 kg P2O5/ha/year and 250 kg K2O/ha/year. For black pepper, P2O5 is paused when soil phosphorus is already above the safety threshold." : "Sầu riêng kinh doanh được chặn ở N tối đa 300 kg/ha/năm, P2O5 tối đa 200 kg/ha/năm và K2O tối đa 250 kg/ha/năm. Hồ tiêu nếu P đất vượt 96 mg P/kg sẽ tạm ngưng P2O5."}</p>
          </article>
          <article>
            <Leaf size={20} />
            <h3>{isEnglish ? "Not a substitute for field advice" : "Không thay thế tư vấn tại vườn"}</h3>
            <p>{isEnglish ? "The result is a reference recommendation. If the orchard shows root disease, weak growth, very low pH or missing soil data, compare it with leaf analysis and a field inspection." : "Kết quả là khuyến nghị tham khảo. Với vườn có biểu hiện bệnh rễ, suy cây, pH quá thấp hoặc dữ liệu đất thiếu, người dùng nên đối chiếu thêm phân tích lá và kiểm tra thực địa."}</p>
          </article>
        </section>

        <section>
          <span className="method-kicker"><ClipboardCheck size={18} /> {isEnglish ? "Main split schedule" : "Lịch chia đợt chính"}</span>
          <h2>{isEnglish ? "Robusta coffee needs a phosphorus base after harvest" : "Cà phê Robusta sau thu hoạch cần có lân nền"}</h2>
          <p>
            {isEnglish ? "For bearing Robusta coffee, the post-harvest split in January-February uses 15% N, 50% P2O5 and 15% K2O to support recovery and root development before the rainy season. The remaining splits are early, mid and late rainy season; together they always total 100% of each nutrient." : "Với cà phê kinh doanh, đợt sau thu hoạch tháng 1-2 dùng 15% N, 50% P2O5 và 15% K2O để phục hồi cây và tạo nền rễ trước mùa mưa. Ba đợt còn lại là đầu mùa mưa, giữa mùa mưa và cuối mùa mưa; tổng các đợt luôn bằng 100% từng chất."}
          </p>
        </section>

        <section className="method-note-grid">
          <article>
            <ShieldCheck size={20} />
            <h3>{isEnglish ? "Confidence badge" : "Huy hiệu độ tin cậy"}</h3>
            <p>{isEnglish ? "Coffee: calibrated. Black pepper: partly calibrated. Durian: international-reference basis. This badge reflects the strength of the crop threshold set, not a yield guarantee." : "Cà phê: Đã hiệu chuẩn. Hồ tiêu: Hiệu chuẩn một phần. Sầu riêng: Tham chiếu quốc tế. Huy hiệu này phản ánh mức chắc của bộ ngưỡng cây trồng, không phải cam kết năng suất."}</p>
          </article>
          <article>
            <Leaf size={20} />
            <h3>{isEnglish ? "Durian reference basis" : "Cơ sở sầu riêng"}</h3>
            <p>{isEnglish ? "Durian uses a 1.0-1.8 kg N/tree/year range for bearing orchards, equal to about 150-270 kg N/ha at 150 trees/ha, referenced from Poovarodom & Tawinteung, DRIS 2024 and Thai DOA/Mekong Delta materials." : "Sầu riêng dùng khung 1,0-1,8 kg N/cây/năm cho vườn kinh doanh, tương đương khoảng 150-270 kg N/ha tại mật độ 150 cây/ha, tham chiếu từ Poovarodom & Tawinteung, DRIS 2024 và tài liệu Thai DOA/ĐBSCL."}</p>
          </article>
        </section>
      </div>
    </section>
  );
}
