import { ArrowRight, BarChart3, BookOpenCheck, Newspaper } from "./icons";
import type { CropType } from "../lib/api";
import { categoryPath, forecastPath } from "../lib/seo";

const topicToCrop: Array<{ match: string[]; crop: CropType; label: string }> = [
  { match: ["cà phê", "ca phe", "robusta", "arabica"], crop: "ca_phe", label: "cà phê" },
  { match: ["sầu riêng", "sau rieng", "durian"], crop: "sau_rieng", label: "sầu riêng" },
  { match: ["hồ tiêu", "ho tieu", "tiêu", "pepper"], crop: "ho_tieu", label: "hồ tiêu" },
  { match: ["lúa", "lua", "gạo", "gao", "rice"], crop: "lua", label: "lúa" }
];

export function RelatedForecastWidget({ text }: { text: string }) {
  const normalized = normalize(text);
  const matched = topicToCrop.find((item) => item.match.some((term) => normalized.includes(normalize(term))));
  if (!matched) return null;

  return (
    <aside className="related-forecast">
      <h3>Xem thêm</h3>
      <a href={forecastPath(matched.crop)}>
        <BarChart3 size={16} />
        Giá {matched.label} hôm nay và dự báo 30 ngày
        <ArrowRight size={15} />
      </a>
      <a href={`/huong-dan?cay=${matched.crop}`}>
        <BookOpenCheck size={16} />
        Hướng dẫn kỹ thuật trồng {matched.label}
        <ArrowRight size={15} />
      </a>
      <a href={categoryPath(matched.label)}>
        <Newspaper size={16} />
        Tin tức {matched.label} mới nhất
        <ArrowRight size={15} />
      </a>
    </aside>
  );
}

function normalize(value: string) {
  return value
    .toLocaleLowerCase("vi-VN")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d");
}
