import { Brain, LineChart, Sparkles } from "./icons";
import { useLanguage } from "../contexts/LanguageContext";
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

export function AnalysisBrief({ cropLabel, regionLabel, varietyLabel, historical, forecast, explanation }: Props) {
  const { language } = useLanguage();
  const locale = language === "en" ? "en-US" : "vi-VN";
  const money = (value: number) => `${Math.round(value).toLocaleString(locale)} VND/kg`;
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
  const toneText = toneCopy(tone, cropLabel, regionLabel, language);
  const drivers = language === "en" ? [] : (explanation?.drivers.slice(0, 6) ?? []);

  return (
    <section className="analysis-brief">
      <article className="analysis-narrative">
        <span>
          <Brain size={17} />
          {language === "en" ? "Market read" : "Nhận định thị trường"}
        </span>
        <h2>{toneText.title}</h2>
        {language === "vi" && explanation?.summary ? <p className="analysis-summary">{explanation.summary}</p> : null}
        {language === "en" ? (
          <>
            <p>
              For {varietyLabel}, the latest price is {money(latest)}. Across the selected data window, the price is
              {changePct >= 0 ? " up " : " down "}
              {Math.abs(changePct).toFixed(2)}%, while the latest session {dayPct >= 0 ? "edged up" : "moved lower"} by {Math.abs(dayPct).toFixed(2)}%.
              It is now {latest >= sma7 ? "above" : "below"} the 7-day average and {latest >= sma30 ? "above" : "below"} the 30-day average,
              which suggests {toneText.marketRead}.
            </p>
            <p>
              Looking ahead, the final forecast point is around {money(forecastEnd)}, or
              {outlookPct >= 0 ? " above " : " below "}today's price by {Math.abs(outlookPct).toFixed(2)}%.
              {toneText.forwardRead} With 30-day volatility near {volatility.toFixed(2)}%, users should still watch harvest pace,
              grade quality, regional price gaps and forward-buying signals before deciding whether to sell quickly or hold part of the crop.
            </p>
          </>
        ) : (
          <>
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
          </>
        )}
        {language === "vi" && explanation?.recommendation ? (
          <div className="analysis-callout">
            <Sparkles size={16} />
            <strong>{explanation.recommendation}</strong>
          </div>
        ) : null}
      </article>

      <aside className="analysis-driver-card">
        <span>
          <LineChart size={17} />
          {language === "en" ? "Main drivers" : "Tác nhân chính"}
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
            fallbackDrivers(tone, language).map((driver) => (
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

function toneCopy(tone: MarketTone, cropLabel: string, regionLabel: string, language: "vi" | "en") {
  if (language === "en") {
    const byTone = {
      breakout: {
        title: `${cropLabel} in ${regionLabel} is rising faster than its recent baseline`,
        marketRead: "buyers are paying up to secure enough export-grade supply",
        forwardRead: "If qualified supply does not expand quickly, the current price level may hold."
      },
      uptrend: {
        title: `${cropLabel} in ${regionLabel} is moving higher, but the market is not overheated`,
        marketRead: "steady demand is supporting prices, while orchard supply is still enough to keep the market from tightening too sharply",
        forwardRead: "Prices still have room to stay firm, but watch how traders react as new supply reaches the market."
      },
      sideways: {
        title: `${cropLabel} in ${regionLabel} is trading sideways in a narrow range`,
        marketRead: "sellers and buyers are fairly balanced, with no clear advantage on either side",
        forwardRead: "The base case is a stable range unless fresh information changes the supply, weather or demand picture."
      },
      pullback: {
        title: `${cropLabel} in ${regionLabel} is cooling after the previous move`,
        marketRead: "near-term supply or selling pressure is slightly stronger than buying demand",
        forwardRead: "Watch buyer response at lower prices; if orders return, prices may stabilize instead of extending the decline."
      },
      downtrend: {
        title: `${cropLabel} in ${regionLabel} is under clearer downside pressure`,
        marketRead: "prices are below several recent averages, which suggests buyers are becoming more cautious",
        forwardRead: "Downside risk remains if demand does not improve or fresh supply keeps building."
      }
    };
    return byTone[tone];
  }
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

function fallbackDrivers(tone: MarketTone, language: "vi" | "en") {
  if (language === "en") {
    if (tone === "downtrend" || tone === "pullback") {
      return [
        { name: "Near-term supply", direction: "Adds pressure", detail: "When more produce reaches the market, buyers have more choice and often push harder on lower-grade lots." },
        { name: "Wait-and-see demand", direction: "Slows trading", detail: "Buyers tend to wait for confirmation that prices have bottomed, so rebounds can be fragile without fresh support." },
        { name: "Regional price gaps", direction: "Creates divergence", detail: "Regions with better quality and logistics usually hold prices better than the broader market." }
      ];
    }
    return [
      { name: "Qualified supply", direction: "Supports prices", detail: "When export-grade supply is not abundant, buyers need to pay better prices to secure volume." },
      { name: "Market demand", direction: "Watch closely", detail: "Stronger export or processing orders help prices hold; weaker demand leaves the market vulnerable to sideways trading." },
      { name: "Weather and harvest timing", direction: "Adds noise", detail: "Rain, heat or uneven harvest timing can move short-term prices even when the broader trend is stable." }
    ];
  }
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
