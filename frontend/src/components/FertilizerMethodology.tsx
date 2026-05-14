import { BookOpenCheck, Calculator, ClipboardCheck, Leaf, ShieldCheck } from "./icons";
import { SeoHead } from "./SeoHead";

const steps = [
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
    text: "Sau khi có lượng hoạt chất N, P2O5 và K2O, hệ thống quy đổi sang Urê 46% N, DAP 18-46 và Kali KCl 60%. Với sầu riêng giai đoạn nuôi trái, kali được ưu tiên chuyển sang Kali sunphat K2SO4."
  }
];

export function FertilizerMethodology() {
  return (
    <section className="fertilizer-page fertilizer-method-page">
      <SeoHead
        title="Giải thích logic tính khuyến nghị bón phân"
        description="Cách Dubaonongsan tính khuyến nghị bón phân từ phân tích đất, năng suất mục tiêu, điều kiện vườn và quy đổi sang phân thương mại."
        canonical="/khuyen-nghi-bon-phan/logic"
      />
      <header className="fertilizer-hero fertilizer-method-hero">
        <div>
          <span className="fertilizer-eyebrow">Minh bạch công thức</span>
          <h1>Giải thích logic chi tiết cách tính khuyến nghị bón phân</h1>
          <p>Cách tính được thiết kế để người trồng có thể kiểm tra từng bước: từ chỉ tiêu đất, liều nền, hệ số hiệu chỉnh đến lượng phân thương mại cần bón theo từng đợt.</p>
          <a className="fertilizer-inline-link" href="/khuyen-nghi-bon-phan">Mở công cụ khuyến nghị</a>
        </div>
      </header>

      <div className="methodology-article fertilizer-methodology-article">
        <section>
          <span className="method-kicker"><Calculator size={18} /> Công thức tổng quát</span>
          <h2>Liều hoạt chất trước khi quy đổi</h2>
          <div className="formula-card">
            Liều cuối = Liều nền theo đất và năng suất x Hệ số pH x Hệ số nước x Hệ số kết cấu đất x Hệ số độ dốc x Hệ số tuổi vườn x Hệ số hữu cơ
          </div>
          <p>
            Liều cuối là lượng hoạt chất tính theo kg/ha/năm. Sau bước này, hệ thống mới quy đổi ra lượng phân thương mại để người dùng dễ áp dụng ngoài vườn.
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
          <span className="method-kicker"><ClipboardCheck size={18} /> Quy đổi phân thương mại</span>
          <h2>Cách đổi hoạt chất sang kg phân/ha</h2>
          <div className="formula-card">
            DAP = P2O5 / 0,46; Đạm từ DAP = DAP x 0,18; Urê = phần Đạm còn lại / 0,463; Kali KCl = K2O / 0,60
          </div>
          <p>
            Ví dụ nếu cần 100 kg P2O5/ha, hệ thống quy đổi khoảng 217 kg DAP/ha. Lượng đạm có sẵn trong DAP sẽ được trừ trước khi tính thêm Urê, để tránh bón thừa đạm.
          </p>
        </section>

        <section className="method-note-grid">
          <article>
            <ShieldCheck size={20} />
            <h3>Chặn ngưỡng an toàn</h3>
            <p>Liều N, P2O5 và K2O được kiểm tra lại bằng trần an toàn. Nếu vượt quá ngưỡng, hệ thống hạ về mức bảo thủ và hiển thị cảnh báo.</p>
          </article>
          <article>
            <Leaf size={20} />
            <h3>Không thay thế tư vấn tại vườn</h3>
            <p>Kết quả là khuyến nghị tham khảo. Với vườn có biểu hiện bệnh rễ, suy cây, pH quá thấp hoặc dữ liệu đất thiếu, người dùng nên đối chiếu thêm phân tích lá và kiểm tra thực địa.</p>
          </article>
        </section>
      </div>
    </section>
  );
}
