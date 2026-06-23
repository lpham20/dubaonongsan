import type { AppLanguage } from "../../contexts/LanguageContext";
import type { CropType } from "../../lib/api";
import { toNFC } from "../../lib/text";
import type { MainSection, NewsView } from "./types";

export const headerText = {
  vi: {
    brand: "DỰ BÁO NÔNG SẢN",
    account: "Tài khoản",
    openAccount: "Mở tài khoản",
    logout: "Đăng xuất",
    login: "Đăng nhập",
    register: "Đăng ký",
    createAccount: "Tạo tài khoản",
    fullName: "Họ tên",
    password: "Mật khẩu",
    priceForecast: "Dự báo giá nông sản",
    forecastPrice: "Dự báo giá",
    worldFertilizer: "Giá phân bón thế giới",
    forecastAlgorithm: "Thuật toán dự báo",
    closeMenu: "Đóng menu",
    openMenu: "Mở menu",
    mainNavigation: "Điều hướng chính",
    mobileDrawer: "Menu điều hướng",
    switchLanguage: "Đổi sang tiếng Anh",
    languageLabel: "VI",
    languageFlag: "🇻🇳"
  },
  en: {
    brand: "AGRI PRICE FORECAST",
    account: "Account",
    openAccount: "Open account",
    logout: "Sign out",
    login: "Log in",
    register: "Register",
    createAccount: "Create account",
    fullName: "Full name",
    password: "Password",
    priceForecast: "Agricultural price forecast",
    forecastPrice: "Price forecast",
    worldFertilizer: "World fertilizer prices",
    forecastAlgorithm: "Forecast method",
    closeMenu: "Close menu",
    openMenu: "Open menu",
    mainNavigation: "Primary navigation",
    mobileDrawer: "Navigation menu",
    switchLanguage: "Switch to Vietnamese",
    languageLabel: "EN",
    languageFlag: "🇬🇧"
  }
} as const;

const mainSectionLabels: Record<AppLanguage, Partial<Record<MainSection, string>>> = {
  vi: {
    home: "Trang chủ",
    news: "Tin tức",
    guides: "Hướng dẫn",
    fertilizer: "Khuyến nghị"
  },
  en: {
    home: "Home",
    news: "News",
    guides: "Guides",
    fertilizer: "Advisory"
  }
};

const newsLabels: Record<AppLanguage, Record<NewsView, string>> = {
  vi: {
    latest: "Tin tức mới nhất",
    sau_rieng: "Giá sầu riêng",
    ca_phe: "Giá cà phê",
    ho_tieu: "Giá hồ tiêu"
  },
  en: {
    latest: "Latest news",
    sau_rieng: "Durian prices",
    ca_phe: "Coffee prices",
    ho_tieu: "Pepper prices"
  }
};

const cropLabels: Record<AppLanguage, Record<CropType, string>> = {
  vi: {
    sau_rieng: "Sầu riêng",
    ca_phe: "Cà phê",
    ho_tieu: "Hồ tiêu",
    lua: "Lúa"
  },
  en: {
    sau_rieng: "Durian",
    ca_phe: "Coffee",
    ho_tieu: "Pepper",
    lua: "Rice"
  }
};

const fertilizerLabels: Record<AppLanguage, Partial<Record<MainSection, string>>> = {
  vi: {
    fertilizer: "Khuyến nghị bón phân",
    fertilizerMethodology: "Giải thích logic cách tính",
    yieldFeedback: "Báo cáo năng suất",
    roi: "Lợi nhuận nông vụ",
    sellingTime: "Thời điểm bán",
    arbitrage: "Chênh lệch vùng",
    crossCrop: "So sánh cây trồng"
  },
  en: {
    fertilizer: "Fertilizer recommendation",
    fertilizerMethodology: "Calculation logic",
    yieldFeedback: "Yield feedback",
    roi: "Farm profit",
    sellingTime: "Selling timing",
    arbitrage: "Regional spread",
    crossCrop: "Crop comparison"
  }
};

export function mainSectionLabel(language: AppLanguage, value: MainSection, fallback: string) {
  return toNFC(mainSectionLabels[language][value] ?? fallback);
}

export function newsItemLabel(language: AppLanguage, value: NewsView) {
  return toNFC(newsLabels[language][value]);
}

export function cropItemLabel(language: AppLanguage, value: CropType) {
  return toNFC(cropLabels[language][value]);
}

export function fertilizerItemLabel(language: AppLanguage, value: MainSection, fallback: string) {
  return toNFC(fertilizerLabels[language][value] ?? fallback);
}

export function fertilizerGroupLabel(language: AppLanguage, fallback?: string) {
  if (!fallback) return "";
  return toNFC(language === "en" ? "Decision tools" : fallback);
}
