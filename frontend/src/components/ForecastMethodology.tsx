import type { ReactNode } from "react";
import {
  Activity,
  BookOpenCheck,
  Brain,
  Calculator,
  ClipboardCheck,
  Database,
  LineChart,
  ShieldCheck,
  type LucideIcon
} from "./icons";
import { SeoHead } from "./SeoHead";
import { useLanguage } from "../contexts/LanguageContext";

const faqSchema = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: [
    {
      "@type": "Question",
      name: "Hệ thống dự báo giá nông sản theo cách nào?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Hệ thống tách dữ liệu theo cây trồng, vùng, giống và loại hàng; sau đó dùng cửa sổ giá gần nhất, xu hướng, biến động thời tiết và khoảng tin cậy để tạo dự báo 30 ngày."
      }
    },
    {
      "@type": "Question",
      name: "Dữ liệu đầu vào gồm những gì?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Dữ liệu gồm giá VND/kg, vùng trồng, giống, loại hàng, nhiệt độ, lượng mưa, độ chín và khối lượng giao dịch nếu nguồn thu thập có cung cấp."
      }
    },
    {
      "@type": "Question",
      name: "Khoảng tin cậy nên được hiểu ra sao?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Khoảng tin cậy là vùng giá thấp và cao quanh dự báo trung tâm, dùng để nhắc người dùng rằng dự báo là tín hiệu tham khảo chứ không phải cam kết giá mua bán."
      }
    },
    {
      "@type": "Question",
      name: "Vì sao cần kiểm định MAE và RMSE?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "MAE cho biết sai số trung bình, còn RMSE nhạy với các ngày biến động mạnh. Hai chỉ số này giúp đánh giá mô hình theo từng cây trồng và vùng."
      }
    }
  ]
};

export function ForecastMethodology() {
  const { language } = useLanguage();
  if (language === "en") return <EnglishForecastMethodology />;

  return (
    <section className="method-page">
      <SeoHead
        title="Thuật toán dự báo giá nông sản"
        description="Giải thích dữ liệu đầu vào, công thức dự báo, LSTM, MAE, RMSE và cách đọc khoảng tin cậy trong hệ thống dự báo giá nông sản."
        canonical="/thuat-toan-du-bao"
        schemaJsonLd={faqSchema}
      />
      <header className="method-hero">
        <span>
          <Brain size={18} />
          Thuật toán dự báo
        </span>
        <h1>Cách hệ thống dự báo giá nông sản</h1>
        <p>
          Trang này giải thích rõ cách hệ thống biến dữ liệu giá, vùng trồng, giống, thời tiết và độ chín thành dự báo
          30 ngày. Nội dung được viết theo đúng quy trình đang chạy ở lớp xử lý dữ liệu hiện tại, đồng thời chỉ ra phần nào
          là mô hình thống kê ổn định và phần nào có thể nâng cấp thành mô hình LSTM vận hành chính thức khi có đủ dữ
          liệu lịch sử sạch.
        </p>
      </header>

      <div className="method-layout">
        <article className="method-article">
          <section>
            <h2>1. Bài toán dự báo được định nghĩa như thế nào?</h2>
            <p>
              Giá nông sản không chỉ là một chuỗi số theo thời gian. Một mức giá của sầu riêng hoặc cà phê luôn gắn với
              mặt hàng, vùng trồng, giống, loại hàng, thời điểm thu hoạch, điều kiện mưa nắng và độ sẵn hàng ngoài thị
              trường. Vì vậy hệ thống không dự báo một giá chung cho cả nước, mà tách bài toán theo từng tổ hợp:
            </p>
            <FormulaBlock label="Đơn vị dự báo">
              ŷ<sub>c,r,v</sub>(t + h), &nbsp; h = 1, 2, ..., 30
            </FormulaBlock>
            <p>
              Trong đó <code>c</code> là cây trồng, <code>r</code> là vùng hoặc tỉnh, <code>v</code> là giống, còn
              <code>h</code> là số ngày cần dự báo. Cách tách này giúp dự báo thực tế hơn: cùng là sầu riêng Ri6, giá ở
              Đắk Lắk không nên bị trộn cứng với Tiền Giang; cùng là cà phê, Robusta và Arabica cũng cần được xem như
              hai chuỗi khác nhau.
            </p>
          </section>

          <section>
            <h2>2. Dữ liệu đầu vào và cách làm sạch</h2>
            <p>
              Mỗi lần dự báo, hệ thống lấy cửa sổ 60 ngày gần nhất. Hệ thống ưu tiên giá <code>Loại A</code> để giữ mặt
              bằng chất lượng tương đối ổn định. Nếu vùng đang chọn thiếu dữ liệu loại A, hệ thống mới fallback sang
              dữ liệu loại khác để tránh trả về trang trống.
            </p>
            <FormulaBlock label="Cửa sổ dữ liệu">
              W<sub>t</sub> = {"{"}x<sub>i</sub>{"}"}<sub>i=t-59</sub><sup>t</sup>, &nbsp;
              x<sub>i</sub> = [p<sub>i</sub>, T<sub>i</sub>, R<sub>i</sub>, M<sub>i</sub>, V<sub>i</sub>]
            </FormulaBlock>
            <p>
              <code>p</code> là giá cao nhất VND/kg, <code>T</code> là nhiệt độ tối đa, <code>R</code> là lượng mưa,
              <code>M</code> là chỉ số độ chín và <code>V</code> là khối lượng giao dịch. Với các điểm thiếu ngắn hạn,
              hệ thống dùng phương pháp điền tiếp giá trị gần nhất trước đó. Nếu đầu chuỗi vẫn thiếu, lớp xử lý dữ liệu dùng
              giá trị hợp lệ đầu tiên trong chuỗi. Cách này thận trọng hơn việc tự bịa số trung bình toàn quốc, vì nó
              giữ đặc tính riêng của vùng đang phân tích.
            </p>
          </section>

          <section>
            <h2>3. Tách xu hướng ngắn hạn khỏi mặt bằng giá</h2>
            <p>
              Lõi dự báo hiện tại dùng mô hình thống kê xác định. Mục tiêu của lớp này là chạy ổn định, dễ kiểm toán và
              không phụ thuộc phần cứng đồ họa. Trước tiên, hệ thống so sánh mặt bằng 7 ngày gần nhất với mặt bằng dài hơn trong tối
              đa 30 ngày.
            </p>
            <FormulaBlock label="Xu hướng">
              S<sub>t</sub> = 1/7 · Σ<sub>i=t-6</sub><sup>t</sup> p<sub>i</sub>
              <br />
              L<sub>t</sub> = 1/m · Σ<sub>i=t-m+1</sub><sup>t</sup> p<sub>i</sub>, &nbsp; m = min(30, n)
              <br />
              b<sub>t</sub> = (S<sub>t</sub> - L<sub>t</sub>) / min(30, n)
            </FormulaBlock>
            <p>
              Nếu <code>S_t</code> cao hơn <code>L_t</code>, chuỗi đang có lực tăng gần đây; nếu thấp hơn, thị trường
              đang yếu đi so với mặt bằng tháng. Điểm quan trọng là hệ thống không kết luận “giá chắc chắn tăng” chỉ vì
              vài ngày cuối nhích lên. Độ dốc <code>b_t</code> được chia cho độ dài cửa sổ để giảm phản ứng quá mạnh
              với nhiễu ngắn hạn.
            </p>
          </section>

          <section>
            <h2>4. Đưa biên độ mùa vụ và thời tiết vào dự báo</h2>
            <p>
              Giá nông sản thường rung lắc theo nhịp thu hoạch, vận chuyển, mưa nắng và lịch giao hàng. Vì vậy sau phần
              xu hướng, hệ thống thêm một thành phần dao động ngắn hạn dựa trên độ lệch chuẩn của giá gần đây.
            </p>
            <FormulaBlock label="Biên độ dao động">
              σ<sub>t</sub> = √{"{"}1/m · Σ<sub>i=t-m+1</sub><sup>t</sup>(p<sub>i</sub> - p̄)<sup>2</sup>{"}"}
              <br />
              season<sub>h</sub> = 0.09 · σ<sub>t</sub> · sin(h / 4.8)
            </FormulaBlock>
            <p>
              Thành phần <code>season_h</code> không phải “mùa vụ dài hạn” theo năm, mà là nhịp dao động nhỏ trong cửa
              sổ 30 ngày. Nó giúp đường dự báo bớt cứng, nhưng vẫn bị giới hạn bởi biến động thật của chuỗi.
            </p>
            <FormulaBlock label="Tác động nông học">
              w<sub>t</sub> = 18(T̄ - 31.5) - 12 · max(0, R̄ - 20) + 22 · max(0, M̄ - 7)
            </FormulaBlock>
            <p>
              Công thức trên là phần quy tắc nông nghiệp đang chạy trong lớp xử lý dữ liệu. Nhiệt độ cao hơn nền có thể làm áp lực
              thu hoạch xuất hiện sớm hơn; mưa lớn thường làm tăng rủi ro chất lượng, vận chuyển và hao hụt; chỉ số độ
              chín cao cho thấy nguồn hàng sắp ra thị trường rõ hơn. Các hệ số hiện tại là hệ số kinh nghiệm để mô hình
              chạy ổn định trong bản thử nghiệm, và sẽ được thay bằng hệ số học được từ dữ liệu khi huấn luyện lại ở môi trường vận hành chính thức.
            </p>
          </section>

          <section>
            <h2>5. Công thức dự báo cuối cùng</h2>
            <p>
              Giá dự báo cho ngày thứ <code>h</code> được cộng từ giá mới nhất, độ dốc xu hướng, dao động ngắn hạn và
              phần hiệu chỉnh theo thời tiết/độ chín. Hệ thống cũng đặt một ngưỡng sàn để loại bỏ kết quả phi thực tế khi
              chuỗi quá ngắn hoặc dữ liệu đầu vào nhiễu.
            </p>
            <FormulaBlock label="Dự báo 30 ngày">
              ŷ(t+h) = max(25.000, p<sub>t</sub> + b<sub>t</sub>h + season<sub>h</sub> + w<sub>t</sub>h)
            </FormulaBlock>
            <p>
              Đây là dự báo điểm. Trên giao diện, đường dự báo nên được đọc như một kịch bản trung tâm, không phải cam
              kết giá mua bán. Khi dữ liệu một vùng ít hơn hoặc biến động bất thường, phần khoảng tin cậy bên dưới mới
              là thứ cần nhìn kỹ.
            </p>
          </section>

          <section>
            <h2>6. Khoảng tin cậy và cách hiểu sai số</h2>
            <p>
              Với mỗi điểm dự báo, hệ thống tạo dải thấp/cao bằng sai số quy đổi sang VND/kg. Cấu hình hiện tại dùng
              <code>0.45 USD/kg</code> và tỷ giá quy đổi <code>24.500 VND/USD</code>.
            </p>
            <FormulaBlock label="Dải dự báo">
              band = 0.45 × 24.500 = 11.025 VND/kg
              <br />
              lower<sub>h</sub> = ŷ(t+h) - band
              <br />
              upper<sub>h</sub> = ŷ(t+h) + band
            </FormulaBlock>
            <p>
              Sai số được tính bằng kiểm định trượt theo thời gian. Hệ thống lấy 60 ngày làm dữ liệu đầu vào, dự báo 30
              ngày sau, rồi so với giá đã xảy ra. Cách này mô phỏng đúng tình huống vận hành: tại thời điểm dự báo,
              model không được nhìn trước dữ liệu tương lai.
            </p>
            <FormulaBlock label="Đo sai số">
              e<sub>i</sub> = ŷ<sub>i</sub> - y<sub>i</sub>
              <br />
              MAE = 1/N · Σ<sub>i=1</sub><sup>N</sup> |e<sub>i</sub>|
              <br />
              RMSE = √{"{"}1/N · Σ<sub>i=1</sub><sup>N</sup> e<sub>i</sub><sup>2</sup>{"}"}
            </FormulaBlock>
            <p>
              MAE trả lời câu hỏi “trung bình lệch bao nhiêu VND/kg”. RMSE phạt nặng các lần lệch lớn, nên hữu ích khi
              phát hiện vùng hoặc giống có cú sốc nguồn cung, thời tiết hoặc giá thu mua. Nếu RMSE cao hơn MAE nhiều,
              điều đó thường cho thấy chuỗi có một vài ngày biến động mạnh mà mô hình chưa bắt kịp.
            </p>
          </section>

          <section>
            <h2>7. LSTM vận hành chính thức sẽ nâng cấp phần nào?</h2>
            <p>
              Lớp <code>LSTMForecaster</code> hiện được thiết kế như một lớp bọc kỹ thuật: bản thử nghiệm dùng công thức kiểm toán
              được, còn bản vận hành chính thức có thể nạp tệp mô hình TensorFlow/Keras. Khi dữ liệu lịch sử đủ dài và được kiểm soát
              chất lượng, LSTM sẽ học quan hệ phi tuyến giữa giá, thời tiết, độ chín, vùng trồng và độ trễ nhiều ngày.
            </p>
            <FormulaBlock label="Ô nhớ LSTM">
              f<sub>t</sub> = σ(W<sub>f</sub>[h<sub>t-1</sub>, x<sub>t</sub>] + b<sub>f</sub>)
              <br />
              i<sub>t</sub> = σ(W<sub>i</sub>[h<sub>t-1</sub>, x<sub>t</sub>] + b<sub>i</sub>)
              <br />
              C̃<sub>t</sub> = tanh(W<sub>C</sub>[h<sub>t-1</sub>, x<sub>t</sub>] + b<sub>C</sub>)
              <br />
              C<sub>t</sub> = f<sub>t</sub> ⊙ C<sub>t-1</sub> + i<sub>t</sub> ⊙ C̃<sub>t</sub>
              <br />
              o<sub>t</sub> = σ(W<sub>o</sub>[h<sub>t-1</sub>, x<sub>t</sub>] + b<sub>o</sub>)
              <br />
              h<sub>t</sub> = o<sub>t</sub> ⊙ tanh(C<sub>t</sub>)
            </FormulaBlock>
            <p>
              LSTM không tự động “thông minh hơn” nếu dữ liệu ít hoặc nhiễu. Vì vậy hướng vận hành hợp lý là dùng mô
              hình thống kê hiện tại làm mốc so sánh, sau đó chỉ thay bằng LSTM khi kiểm định trượt theo thời gian chứng minh được MAE/RMSE giảm
              ổn định theo từng cây trồng, vùng và giống. Đây là cách triển khai đáng tin hơn việc đưa học sâu
              lên giao diện chỉ để nghe có vẻ hiện đại.
            </p>
          </section>

          <section>
            <h2>8. Những trường hợp hệ thống phải cảnh báo</h2>
            <p>
              Một dự báo tốt không chỉ đưa ra con số, mà còn phải biết khi nào con số đó yếu. Hệ thống nên hạ độ tin
              cậy nếu một trong các điều kiện sau xảy ra: chuỗi có quá ít ngày liên tục, nhiều điểm bị forward-fill,
              giá nhảy bất thường do nguồn tin đơn lẻ, vùng đang vào mùa mưa mạnh, hoặc giống được chọn có thanh khoản
              giao dịch thấp.
            </p>
            <FormulaBlock label="Điểm tin cậy đề xuất">
              confidence = 100 - gapPenalty - volatilityPenalty - sourcePenalty - freshnessPenalty
            </FormulaBlock>
            <p>
              Công thức tin cậy này chưa cần phức tạp, nhưng rất quan trọng cho trải nghiệm vận hành chính thức: người dùng phải
              biết lúc nào nên xem dự báo như tín hiệu chính, lúc nào chỉ nên xem như tham khảo và cần kiểm tra thêm
              nguồn giá thực địa.
            </p>
          </section>
        </article>

        <aside className="method-sidebar">
          <MethodCard icon={Database} title="Cửa sổ dữ liệu" value="60 ngày" detail="Tách theo cây trồng, vùng và giống" />
          <MethodCard icon={LineChart} title="Chân trời dự báo" value="30 ngày" detail="Sinh dự báo từng ngày, không nhìn trước tương lai" />
          <MethodCard icon={Calculator} title="Đo sai số" value="MAE / RMSE" detail="Kiểm định trượt theo thời gian" />
          <MethodCard icon={Activity} title="Biến nông học" value="Mưa / nhiệt / độ chín" detail="Không chỉ dựa vào giá quá khứ" />
          <MethodCard icon={ClipboardCheck} title="Kiểm toán" value="Mốc so sánh trước" detail="LSTM chỉ thay thế khi kiểm định tốt hơn" />
          <MethodCard icon={ShieldCheck} title="Minh bạch" value="Công thức mở" detail="Có thể đọc, kiểm tra và nâng cấp" />
        </aside>
      </div>

      <section className="method-sources">
        <div>
          <BookOpenCheck size={18} />
          <h2>Nguồn tham khảo</h2>
        </div>
        <ul>
          <li>
            Hochreiter, S. & Schmidhuber, J. (1997), <a href="https://direct.mit.edu/neco/article/9/8/1735/6109/Long-Short-Term-Memory" target="_blank" rel="noreferrer">Long Short-Term Memory</a>, Neural Computation.
          </li>
          <li>
            Hyndman, R. & Athanasopoulos, G. (2021), <a href="https://otexts.com/fpp3/" target="_blank" rel="noreferrer">Forecasting: Principles and Practice</a>, OTexts.
          </li>
          <li>
            Hyndman & Athanasopoulos, <a href="https://otexts.com/fpp3/tscv.html" target="_blank" rel="noreferrer">Time series cross-validation</a>, về rolling forecast origin.
          </li>
          <li>
            Choudhary et al. (2025), <a href="https://www.nature.com/articles/s41598-025-94173-0" target="_blank" rel="noreferrer">VMD-LSTM for agricultural price forecasting</a>, Scientific Reports.
          </li>
          <li>
            Yang et al. (2022), <a href="https://www.mdpi.com/2077-0472/12/2/256" target="_blank" rel="noreferrer">Dual Input Attention LSTM for agricultural commodity prices</a>, Agriculture.
          </li>
          <li>
            Scientific Reports (2025), <a href="https://www.nature.com/articles/s41598-025-97724-7" target="_blank" rel="noreferrer">RNN/GNN agricultural price prediction with weather variables</a>.
          </li>
        </ul>
      </section>
    </section>
  );
}

function EnglishForecastMethodology() {
  const schema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: [
      {
        "@type": "Question",
        name: "How does the agricultural price forecast work?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "The system separates data by crop, province or region, variety and grade, then combines recent prices, trend, weather signals and confidence ranges to produce a 30-day forecast."
        }
      },
      {
        "@type": "Question",
        name: "What data goes into the model?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "Inputs include VND/kg prices, production area, variety, grade, temperature, rainfall, maturity signals and transaction volume when the source provides it."
        }
      }
    ]
  };

  return (
    <section className="method-page">
      <SeoHead
        title="Agricultural price forecast methodology"
        description="A practical explanation of the data, 30-day forecast logic, LSTM upgrade path, MAE/RMSE backtesting and confidence ranges used in the agricultural price forecast."
        canonical="/thuat-toan-du-bao"
        schemaJsonLd={schema}
      />
      <header className="method-hero">
        <span>
          <Brain size={18} />
          Forecast method
        </span>
        <h1>How the agricultural price forecast works</h1>
        <p>
          This page explains how price, region, variety, weather and maturity data become a 30-day forecast. The current production layer is intentionally auditable, while the LSTM layer can replace it once backtests prove it is more stable.
        </p>
      </header>

      <div className="method-layout">
        <article className="method-article">
          <section>
            <h2>1. Forecast unit</h2>
            <p>
              Agricultural prices are not one national time series. A realistic forecast is calculated by crop, province or region, variety and grade, so Robusta coffee in Gia Lai is not mixed with durian in the Mekong Delta.
            </p>
            <FormulaBlock label="Forecast unit">
              y&#770;<sub>c,r,v</sub>(t + h), &nbsp; h = 1, 2, ..., 30
            </FormulaBlock>
          </section>

          <section>
            <h2>2. Data window and cleaning</h2>
            <p>
              Each run uses the latest available price window, prioritizes comparable quality grades and fills only short gaps with the nearest valid value. That keeps the forecast stable without inventing a national average when a local series is thin.
            </p>
            <FormulaBlock label="Input window">
              W<sub>t</sub> = {"{"}x<sub>i</sub>{"}"}<sub>i=t-59</sub><sup>t</sup>, &nbsp;
              x<sub>i</sub> = [p<sub>i</sub>, T<sub>i</sub>, R<sub>i</sub>, M<sub>i</sub>, V<sub>i</sub>]
            </FormulaBlock>
          </section>

          <section>
            <h2>3. Trend, short-term movement and weather signal</h2>
            <p>
              The model compares the recent seven-day level with the longer local baseline, then adds a bounded short-term movement term. Weather and maturity signals are used as cautious nudges, not as a promise that price must move in one direction.
            </p>
            <FormulaBlock label="Trend">
              b<sub>t</sub> = (S<sub>t</sub> - L<sub>t</sub>) / min(30, n)
            </FormulaBlock>
          </section>

          <section>
            <h2>4. Final 30-day forecast</h2>
            <p>
              The daily forecast starts from the latest local price and adds trend, seasonal movement and agronomic adjustment. On the chart, this is the base scenario, so it should be read together with the confidence range.
            </p>
            <FormulaBlock label="30-day forecast">
              y&#770;(t+h) = max(25,000, p<sub>t</sub> + b<sub>t</sub>h + season<sub>h</sub> + w<sub>t</sub>h)
            </FormulaBlock>
          </section>

          <section>
            <h2>5. Backtesting and confidence range</h2>
            <p>
              MAE shows the average miss in VND/kg. RMSE penalizes large misses more heavily, which is useful when a crop, province or variety has sudden supply or weather shocks. The confidence band reminds users that the forecast is a reference signal, not a guaranteed trading price.
            </p>
            <FormulaBlock label="Error metrics">
              MAE = average(|forecast - actual|)
              <br />
              RMSE = sqrt(average((forecast - actual)<sup>2</sup>))
            </FormulaBlock>
          </section>

          <section>
            <h2>6. Where LSTM fits</h2>
            <p>
              LSTM is useful only when the historical data is long, clean and consistently backtested. The safe path is to keep the current auditable model as the baseline, train LSTM offline, then deploy it only after rolling backtests show lower error for each crop and region group.
            </p>
          </section>
        </article>

        <aside className="method-sidebar">
          <MethodCard icon={Database} title="Data window" value="60 days" detail="Separated by crop, region and variety" />
          <MethodCard icon={LineChart} title="Forecast horizon" value="30 days" detail="Daily forecast without looking into future data" />
          <MethodCard icon={Calculator} title="Error metrics" value="MAE / RMSE" detail="Rolling time-series validation" />
          <MethodCard icon={Activity} title="Agronomic signals" value="Rain / heat / maturity" detail="The model does not rely on price alone" />
          <MethodCard icon={ClipboardCheck} title="Auditability" value="Baseline first" detail="LSTM replaces it only after better backtests" />
          <MethodCard icon={ShieldCheck} title="Transparency" value="Open logic" detail="Readable, testable and upgradeable" />
        </aside>
      </div>

      <section className="method-sources">
        <div>
          <BookOpenCheck size={18} />
          <h2>References</h2>
        </div>
        <ul>
          <li>
            Hochreiter, S. & Schmidhuber, J. (1997), <a href="https://direct.mit.edu/neco/article/9/8/1735/6109/Long-Short-Term-Memory" target="_blank" rel="noreferrer">Long Short-Term Memory</a>, Neural Computation.
          </li>
          <li>
            Hyndman, R. & Athanasopoulos, G. (2021), <a href="https://otexts.com/fpp3/" target="_blank" rel="noreferrer">Forecasting: Principles and Practice</a>, OTexts.
          </li>
          <li>
            Yang et al. (2022), <a href="https://www.mdpi.com/2077-0472/12/2/256" target="_blank" rel="noreferrer">Dual Input Attention LSTM for agricultural commodity prices</a>, Agriculture.
          </li>
        </ul>
      </section>
    </section>
  );
}

function FormulaBlock({ children, label }: { children: ReactNode; label: string }) {
  return (
    <div className="formula-block">
      <span>{label}</span>
      <div className="formula-expression">{children}</div>
    </div>
  );
}

function MethodCard({
  icon: Icon,
  title,
  value,
  detail
}: {
  icon: LucideIcon;
  title: string;
  value: string;
  detail: string;
}) {
  return (
    <article>
      <Icon size={18} />
      <span>{title}</span>
      <strong>{value}</strong>
      <p>{detail}</p>
    </article>
  );
}
