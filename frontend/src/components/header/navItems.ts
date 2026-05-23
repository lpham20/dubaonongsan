import { BarChart3, BookOpenCheck, Calculator, ClipboardCheck, Coffee, GitCompareArrows, Leaf, Newspaper, Sprout } from "../icons";
import type { LucideIcon } from "../icons";
import type { MainSection, NewsView } from "./types";

export const newsMenuItems: { value: NewsView; label: string; Icon: LucideIcon }[] = [
  { value: "latest", label: "Tin tức mới nhất", Icon: Newspaper },
  { value: "sau_rieng", label: "Giá sầu riêng", Icon: Sprout },
  { value: "ca_phe", label: "Giá cà phê", Icon: Coffee },
  { value: "ho_tieu", label: "Giá hồ tiêu", Icon: Leaf }
];

export const fertilizerMenuItems: {
  value: Extract<MainSection, "fertilizer" | "roi" | "sellingTime" | "arbitrage" | "crossCrop" | "fertilizerMethodology" | "yieldFeedback">;
  label: string;
  Icon: LucideIcon;
  hierarchy?: "child";
  groupLabel?: string;
}[] = [
  { value: "fertilizer", label: "Khuyến nghị bón phân", Icon: Calculator },
  { value: "fertilizerMethodology", label: "Giải thích logic cách tính", Icon: BookOpenCheck, hierarchy: "child" },
  { value: "yieldFeedback", label: "Báo cáo năng suất", Icon: ClipboardCheck, hierarchy: "child" },
  { value: "roi", label: "Lợi nhuận nông vụ", Icon: Calculator, groupLabel: "Công cụ quyết định" },
  { value: "sellingTime", label: "Thời điểm bán", Icon: BarChart3 },
  { value: "arbitrage", label: "Chênh lệch vùng", Icon: GitCompareArrows },
  { value: "crossCrop", label: "So sánh cây trồng", Icon: Sprout }
];
