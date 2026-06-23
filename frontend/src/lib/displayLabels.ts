import type { AppLanguage } from "../contexts/LanguageContext";
import type { CropType, FertilizerCrop, FertilizerStage, SoilTexture } from "./api";
import { toNFC } from "./text";

export function cropLabel(value: CropType | "", language: AppLanguage) {
  const labels: Record<AppLanguage, Record<CropType | "", string>> = {
    vi: {
      "": "Tất cả",
      sau_rieng: "Sầu riêng",
      ca_phe: "Cà phê",
      ho_tieu: "Hồ tiêu",
      lua: "Lúa"
    },
    en: {
      "": "All crops",
      sau_rieng: "Durian",
      ca_phe: "Coffee",
      ho_tieu: "Black pepper",
      lua: "Rice"
    }
  };
  return toNFC(labels[language][value] ?? value);
}

export function fertilizerCropLabel(value: FertilizerCrop, language: AppLanguage) {
  const labels: Record<AppLanguage, Record<FertilizerCrop, string>> = {
    vi: {
      robusta_coffee: "Cà phê Robusta",
      black_pepper: "Hồ tiêu",
      durian: "Sầu riêng"
    },
    en: {
      robusta_coffee: "Robusta coffee",
      black_pepper: "Black pepper",
      durian: "Durian"
    }
  };
  return toNFC(labels[language][value]);
}

export function fertilizerStageLabel(value: FertilizerStage, language: AppLanguage) {
  const labels: Record<AppLanguage, Record<FertilizerStage, string>> = {
    vi: {
      mature_kinh_doanh: "Vườn kinh doanh",
      establishment_y1: "Kiến thiết năm 1",
      establishment_y2: "Kiến thiết năm 2",
      establishment_y3: "Kiến thiết năm 3",
      establishment_y4: "Kiến thiết năm 4",
      establishment_y5: "Kiến thiết năm 5",
      fruit_set: "Sầu riêng đậu trái",
      fruit_fill: "Sầu riêng nuôi trái"
    },
    en: {
      mature_kinh_doanh: "Bearing orchard",
      establishment_y1: "Establishment year 1",
      establishment_y2: "Establishment year 2",
      establishment_y3: "Establishment year 3",
      establishment_y4: "Establishment year 4",
      establishment_y5: "Establishment year 5",
      fruit_set: "Durian fruit set",
      fruit_fill: "Durian fruit filling"
    }
  };
  return toNFC(labels[language][value]);
}

export function soilTextureLabel(value: SoilTexture, language: AppLanguage) {
  const labels: Record<AppLanguage, Record<SoilTexture, string>> = {
    vi: {
      basaltic_red: "Đất bazan đỏ",
      grey_granite: "Đất xám granite",
      gneiss: "Đất gneiss",
      acrisol: "Đất Acrisol",
      alluvial: "Đất phù sa"
    },
    en: {
      basaltic_red: "Red basalt soil",
      grey_granite: "Grey granite soil",
      gneiss: "Gneiss-derived soil",
      acrisol: "Acrisol soil",
      alluvial: "Alluvial soil"
    }
  };
  return toNFC(labels[language][value]);
}

export function provinceLabel(value: string | null | undefined) {
  return toNFC(value || "");
}

export function displayProvince(province: string | null | undefined, region?: string | null) {
  return toNFC(province || region || "");
}

export function translateFertilizerProduct(value: string, language: AppLanguage) {
  if (language === "vi") return value;
  return value
    .replace(/Urê/gi, "Urea")
    .replace(/Đạm/gi, "Nitrogen")
    .replace(/Lân/gi, "Phosphate")
    .replace(/Kali/gi, "Potassium")
    .replace(/Vôi/gi, "Lime")
    .replace(/hữu cơ/gi, "organic matter")
    .replace(/bao/gi, "bags");
}

export function translateFertilizerSplit(value: string, language: AppLanguage) {
  if (language === "vi") return value;
  const normalized = value.toLowerCase();
  if (normalized.includes("sau thu hoạch")) return "Post-harvest recovery";
  if (normalized.includes("đầu mùa mưa")) return "Early rainy season";
  if (normalized.includes("giữa mùa mưa")) return "Mid rainy season";
  if (normalized.includes("cuối mùa mưa")) return "Late rainy season";
  if (normalized.includes("ra hoa")) return "Flowering";
  if (normalized.includes("đậu trái")) return "Fruit set";
  if (normalized.includes("nuôi trái")) return "Fruit filling";
  return value;
}

export function confidenceLabel(value: string | undefined, language: AppLanguage) {
  if (language === "vi") {
    if (value === "high") return "Cao";
    if (value === "medium") return "Trung bình";
    return "Thấp";
  }
  if (value === "high") return "High";
  if (value === "medium") return "Medium";
  return "Low";
}
