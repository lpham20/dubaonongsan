import type { ReactNode } from "react";
import type { LucideIcon } from "../icons";
import type { CropType } from "../../lib/api";

export type MainSection = "home" | "analytics" | "inputPrices" | "news" | "guides" | "fertilizer" | "fertilizerMethodology" | "yieldFeedback" | "methodology";
export type AuthMode = "login" | "register";
export type NewsView = "latest" | "sau_rieng" | "ca_phe" | "ho_tieu";

export type NavItem = {
  value: MainSection;
  label: string;
  Icon: LucideIcon;
};

export type CropNavItem = {
  value: CropType;
  label: string;
  Icon: LucideIcon;
};

export type AppHeaderProps = {
  section: MainSection;
  crop: CropType;
  newsView: NewsView;
  mainSections: NavItem[];
  cropTabs: CropNavItem[];
  priceMenuOpen: boolean;
  newsMenuOpen: boolean;
  fertilizerMenuOpen: boolean;
  authOpen: boolean;
  authMode: AuthMode;
  authName: string;
  authEmail: string;
  authPassword: string;
  onSectionChange: (section: MainSection) => void;
  onAnalyticsOpen: (crop: CropType) => void;
  onNewsOpen: (view: NewsView) => void;
  onPriceMenuOpenChange: (open: boolean) => void;
  onNewsMenuOpenChange: (open: boolean) => void;
  onFertilizerMenuOpenChange: (open: boolean) => void;
  onAuthOpenChange: (open: boolean) => void;
  onAuthModeChange: (mode: AuthMode) => void;
  onAuthNameChange: (value: string) => void;
  onAuthEmailChange: (value: string) => void;
  onAuthPasswordChange: (value: string) => void;
  onAuthSubmit: (mode: AuthMode) => void;
};

export type HeaderSurfaceProps = AppHeaderProps & {
  authContent: ReactNode;
  userLabel: string | null;
};
