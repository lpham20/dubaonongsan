import { Brain, LineChart, Sparkles } from "./icons";
import type { ChangeExplanation, ForecastPoint, PricePoint } from "../lib/api";

type Props = {
  cropLabel: string;
  regionLabel: string;
  varietyLabel: string;
  historical: PricePoint[];
  forecast: ForecastPoint[];
  explanation: ChangeExplanation | null;
};

type MarketTone = "breakout" | "uptrend" | "sideways" | "pullback" | "downtrend";

const money = (value: number) => `${Math.round(value).toLocaleString("vi-VN")} VND/kg`;

export function AnalysisBrief({ cropLabel, regionLabel, varietyLabel, historical, forecast, explanation }: Props) {
  const prices = historical
    .filter((point) => typeof point.max_price_vnd === "number")
    .map((point) => Number(point.max_price_vnd));
  const latest = prices.at(-1) ?? 0;
  const first = prices[0] ?? latest;
  const previous = prices.at(-2) ?? first;
  const sma7 = average(prices.slice(-7));
  const sma30 = average(prices.slice(-30));
  const changePct = first ? ((latest - first) / first) * 100 : 0;
  const dayPct = previous ? ((latest - previous) / previous) * 100 : 0;
  const forecastEnd = forecast.at(-1)?.forecast_price_vnd ?? latest;
  const outlookPct = latest ? ((forecastEnd - latest) / latest) * 100 : 0;
  const volatility = volatilityPct(prices.slice(-30));
  const tone = classifyTone(changePct, dayPct, latest, sma7, sma30, volatility, outlookPct);
  const toneText = toneCopy(tone, cropLabel, regionLabel);
  const drivers = explanation?.drivers.slice(0, 6) ?? [];

  return (
    <section className="analysis-brief">
      <article className="analysis-narrative">
        <span>
          <Brain size={17} />
          Nhận định thị trường
        </span>
        <h2>{toneText.title}</h2>
        {explanation?.summary ? <p className="analysis-summary">{explanation.summary}</p> : null}
        <p>
          Với giống {varietyLabel}, giá hiện ở mức {money(latest)}. Trong khung dữ liệu đang xem, giá
          {changePct >= 0 ? " tăng " : " giảm "}
          {Math.abs(changePct).toFixed(2)}%, phiên gần nhất {dayPct >= 0 ? "nhích lên" : "lùi lại"} {Math.abs(dayPct).toFixed(2)}%.
          Giá hiện {latest >= sma7 ? "cao hơn mặt bằng 7 ngày gần đây" : "thấp hơn mặt bằng 7 ngày gần đây"} và
          {latest >= sma30 ? " cao hơn" : " thấp hơn"} mặt bằng 30 ngày, cho thấy {toneText.marketRead}.
        </p>
        <p>
          Nhìn về phía trước, mức dự báo cuối kỳ ở quanh {money(forecastEnd)}, tương đương
          {outlookPct >= 0 ? " cao hơn " : " thấp hơn "}giá hiện tại {Math.abs(outlookPct).toFixed(2)}%.
          {toneText.forwardRead} Với mức dao động 30 ngày khoảng {volatility.toFixed(2)}%, nên theo dõi sát
          tốc độ thu hoạch, chất lượng hàng đưa ra thị trường, chênh lệch giá giữa các vùng và tín hiệu đặt mua trước khi quyết định bán nhanh hay giữ lại một phần sản lượng.
        </p>
        {explanation?.recommendation ? (
          <div className="analysis-callout">
            <Sparkles size={16} />
            <strong>{explanation.recommendation}</strong>
          </div>
        ) : null}
      </article>

      <aside className="analysis-driver-card">
        <span>
          <LineChart size={17} />
          Tác nhân chính
        </span>
        <div className="analysis-driver-list">
          {drivers.length ? (
            drivers.map((driver) => (
              <div key={driver.name}>
                <strong>{driver.name}</strong>
                <em>{driver.direction}</em>
                <p>{driver.detail}</p>
              </div>
            ))
          ) : (
            fallbackDrivers(tone).map((driver) => (
              <div key={driver.name}>
                <strong>{driver.name}</strong>
                <em>{driver.direction}</em>
                <p>{driver.detail}</p>
              </div>
            ))
          )}
        </div>
      </aside>
    </section>
  );
}

function classifyTone(
  changePct: number,
  dayPct: number,
  latest: number,
  sma7: number,
  sma30: number,
  volatility: number,
  outlookPct: number
): MarketTone {
  if (changePct > 8 && latest >= sma7 && sma7 >= sma30 && outlookPct >= 0) return "breakout";
  if (changePct > 2 && latest >= sma7 && latest >= sma30) return "uptrend";
  if (changePct < -8 && latest < sma7 && sma7 <= sma30) return "downtrend";
  if (changePct < -2 || dayPct < -1.5 || latest < sma7) return "pullback";
  if (volatility < 3 && Math.abs(changePct) < 2) return "sideways";
  return "sideways";
}

function toneCopy(tone: MarketTone, cropLabel: string, regionLabel: string) {
  const byTone = {
    breakout: {
      title: `Giá ${cropLabel} tại ${regionLabel} đang lên nhanh so với mặt bằng gần đây`,
      marketRead: "bên thu mua đang chấp nhận trả cao hơn để gom đủ hàng đạt chuẩn",
      forwardRead: "Nếu lượng hàng đạt chuẩn không tăng nhanh, mặt bằng giá hiện tại có thể còn được giữ."
    },
    uptrend: {
      title: `Giá ${cropLabel} tại ${regionLabel} đang nhích lên nhưng chưa quá nóng`,
      marketRead: "giá được đỡ bởi nhu cầu mua đều, nhưng lượng hàng ra vườn vẫn đủ để thị trường không bị căng",
      forwardRead: "Giá còn cơ hội giữ tốt, nhưng cần theo dõi phản ứng của thương lái khi lượng hàng mới ra nhiều hơn."
    },
    sideways: {
      title: `Giá ${cropLabel} tại ${regionLabel} đang đi ngang trong biên hẹp`,
      marketRead: "người bán và bên thu mua đang khá cân bằng, chưa bên nào tạo được ưu thế rõ",
      forwardRead: "Kịch bản cơ sở là giá giữ quanh vùng hiện tại, chỉ thay đổi mạnh khi có tin mới về sản lượng, thời tiết hoặc đầu ra."
    },
    pullback: {
      title: `Giá ${cropLabel} tại ${regionLabel} đang hạ nhiệt sau nhịp trước đó`,
      marketRead: "nguồn hàng ngắn hạn hoặc tâm lý bán ra đang nhỉnh hơn nhu cầu mua",
      forwardRead: "Cần quan sát phản ứng của thương lái ở vùng giá thấp hơn; nếu đơn mua quay lại, giá có thể ổn định thay vì giảm sâu."
    },
    downtrend: {
      title: `Giá ${cropLabel} tại ${regionLabel} đang chịu sức ép giảm rõ hơn`,
      marketRead: "giá thấp hơn mặt bằng nhiều ngày gần đây, cho thấy bên mua đang thận trọng hơn",
      forwardRead: "Rủi ro giảm còn hiện hữu nếu nhu cầu mua không cải thiện hoặc lượng hàng ra thị trường tiếp tục dày lên."
    }
  };
  return byTone[tone];
}

function fallbackDrivers(tone: MarketTone) {
  if (tone === "downtrend" || tone === "pullback") {
    return [
      { name: "Nguồn cung ngắn hạn", direction: "Tạo áp lực", detail: "Khi hàng ra đều hơn, bên mua có thêm lựa chọn và thường ép giá ở nhóm chất lượng thấp." },
      { name: "Tâm lý chờ giá", direction: "Làm giao dịch chậm", detail: "Người mua có xu hướng chờ xác nhận đáy, khiến nhịp hồi chưa bền nếu thiếu tin hỗ trợ." },
      { name: "Chênh lệch vùng", direction: "Phân hóa", detail: "Vùng có chất lượng và logistics tốt thường giữ giá tốt hơn mặt bằng còn lại." }
    ];
  }
  return [
    { name: "Nguồn hàng đạt chuẩn", direction: "Hỗ trợ giá", detail: "Khi tỷ lệ hàng đạt chuẩn không quá dồi dào, bên mua phải trả giá tốt hơn để gom đủ lượng." },
    { name: "Nhu cầu thị trường", direction: "Theo dõi", detail: "Đơn hàng xuất khẩu/chế biến cải thiện sẽ giúp giá giữ nền, ngược lại giá dễ đi ngang." },
    { name: "Thời tiết và thu hoạch", direction: "Tạo nhiễu", detail: "Mưa, nắng nóng hoặc thu hoạch lệch nhịp có thể làm giá biến động ngắn hạn." }
  ];
}

function average(values: number[]) {
  return values.length ? values.reduce((total, value) => total + value, 0) / values.length : 0;
}

function volatilityPct(values: number[]) {
  if (values.length < 2) return 0;
  const mean = average(values);
  if (!mean) return 0;
  const variance = values.reduce((total, value) => total + (value - mean) ** 2, 0) / values.length;
  return (Math.sqrt(variance) / mean) * 100;
}
