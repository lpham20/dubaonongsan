import { BookOpenCheck, Calculator, Coffee, Leaf, Newspaper, Sprout } from "../icons";
import type { LucideIcon } from "../icons";
import type { MainSection, NewsView } from "./types";

export const newsMenuItems: { value: NewsView; label: string; Icon: LucideIcon }[] = [
  { value: "latest", label: "Tin tức mới nhất", Icon: Newspaper },
  { value: "sau_rieng", label: "Giá sầu riêng", Icon: Sprout },
  { value: "ca_phe", label: "Giá cà phê", Icon: Coffee },
  { value: "ho_tieu", label: "Giá hồ tiêu", Icon: Leaf }
];

export const fertilizerMenuItems: {
  value: Extract<MainSection, "fertilizer" | "fertilizerMethodology">;
  label: string;
  Icon: LucideIcon;
}[] = [
  { value: "fertilizer", label: "Khuyến nghị bón phân", Icon: Calculator },
  { value: "fertilizerMethodology", label: "Giải thích logic cách tính", Icon: BookOpenCheck }
];
