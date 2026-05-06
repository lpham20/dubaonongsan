import { BookOpenCheck, Calculator, ChevronDown, Coffee, Leaf, Newspaper, Sprout, UserRound, type LucideIcon } from "./icons";
import { useAuth } from "../contexts/AuthContext";
import type { CropType } from "../lib/api";

type MainSection = "home" | "analytics" | "news" | "guides" | "fertilizer" | "fertilizerMethodology" | "methodology";
type AuthMode = "login" | "register";
type NewsView = "latest" | "sau_rieng" | "ca_phe" | "ho_tieu";

type NavItem = {
  value: MainSection;
  label: string;
  Icon: LucideIcon;
};

type CropNavItem = {
  value: CropType;
  label: string;
  Icon: LucideIcon;
};

const newsMenuItems: { value: NewsView; label: string; Icon: LucideIcon }[] = [
  { value: "latest", label: "Tin tức mới nhất", Icon: Newspaper },
  { value: "sau_rieng", label: "Giá sầu riêng", Icon: Sprout },
  { value: "ca_phe", label: "Giá cà phê", Icon: Coffee },
  { value: "ho_tieu", label: "Giá hồ tiêu", Icon: Leaf }
];

const fertilizerMenuItems: { value: Extract<MainSection, "fertilizer" | "fertilizerMethodology">; label: string; Icon: LucideIcon }[] = [
  { value: "fertilizer", label: "Khuyến nghị bón phân", Icon: Calculator },
  { value: "fertilizerMethodology", label: "Giải thích logic cách tính", Icon: BookOpenCheck }
];

type Props = {
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

export function AppHeader({
  section,
  crop,
  newsView,
  mainSections,
  cropTabs,
  priceMenuOpen,
  newsMenuOpen,
  fertilizerMenuOpen,
  authOpen,
  authMode,
  authName,
  authEmail,
  authPassword,
  onSectionChange,
  onAnalyticsOpen,
  onNewsOpen,
  onPriceMenuOpenChange,
  onNewsMenuOpenChange,
  onFertilizerMenuOpenChange,
  onAuthOpenChange,
  onAuthModeChange,
  onAuthNameChange,
  onAuthEmailChange,
  onAuthPasswordChange,
  onAuthSubmit
}: Props) {
  const { user, signOut } = useAuth();

  return (
    <nav className="menu-bar" aria-label="Điều hướng chính">
      <div className="brand-title">
        <Leaf size={21} />
        <span>DỰ BÁO NÔNG SẢN</span>
      </div>
      <div className="main-nav">
        {mainSections.map((item) => {
          const Icon = item.Icon;
          if (item.value === "news") {
            return (
              <div
                key={item.value}
                className={["nav-dropdown", section === "news" ? "active" : "", newsMenuOpen ? "open" : ""].filter(Boolean).join(" ")}
                onMouseEnter={() => onNewsMenuOpenChange(true)}
                onMouseLeave={() => onNewsMenuOpenChange(false)}
                onFocus={() => onNewsMenuOpenChange(true)}
              >
                <button type="button" className="tab-button" onClick={() => onNewsMenuOpenChange(!newsMenuOpen)}>
                  <Icon size={16} />
                  {item.label}
                  <ChevronDown size={14} />
                </button>
                <div className="dropdown-menu">
                  {newsMenuItems.map((newsItem) => {
                    const NewsIcon = newsItem.Icon;
                    return (
                      <button
                        key={newsItem.value}
                        type="button"
                        className={section === "news" && newsView === newsItem.value ? "active" : ""}
                        onClick={() => onNewsOpen(newsItem.value)}
                      >
                        <NewsIcon size={16} />
                        {newsItem.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          }
          if (item.value === "fertilizer") {
            return (
              <div
                key={item.value}
                className={[
                  "nav-dropdown",
                  section === "fertilizer" || section === "fertilizerMethodology" ? "active" : "",
                  fertilizerMenuOpen ? "open" : ""
                ].filter(Boolean).join(" ")}
                onMouseEnter={() => onFertilizerMenuOpenChange(true)}
                onMouseLeave={() => onFertilizerMenuOpenChange(false)}
                onFocus={() => onFertilizerMenuOpenChange(true)}
              >
                <button type="button" className="tab-button" onClick={() => onFertilizerMenuOpenChange(!fertilizerMenuOpen)}>
                  <Icon size={16} />
                  {item.label}
                  <ChevronDown size={14} />
                </button>
                <div className="dropdown-menu">
                  {fertilizerMenuItems.map((fertilizerItem) => {
                    const FertilizerIcon = fertilizerItem.Icon;
                    return (
                      <button
                        key={fertilizerItem.value}
                        type="button"
                        className={section === fertilizerItem.value ? "active" : ""}
                        onClick={() => {
                          onSectionChange(fertilizerItem.value);
                          onFertilizerMenuOpenChange(false);
                        }}
                      >
                        <FertilizerIcon size={16} />
                        {fertilizerItem.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          }
          return (
            <button
              key={item.value}
              className={item.value === section ? "tab-button active" : "tab-button"}
              onClick={() => onSectionChange(item.value)}
              type="button"
            >
              <Icon size={16} />
              {item.label}
            </button>
          );
        })}
        <div
          className={["nav-dropdown", section === "analytics" || section === "methodology" ? "active" : "", priceMenuOpen ? "open" : ""].filter(Boolean).join(" ")}
          onMouseEnter={() => onPriceMenuOpenChange(true)}
          onMouseLeave={() => onPriceMenuOpenChange(false)}
          onFocus={() => onPriceMenuOpenChange(true)}
        >
          <button type="button" className="tab-button" onClick={() => onPriceMenuOpenChange(!priceMenuOpen)}>
            <Leaf size={16} />
            Dự báo giá nông sản
            <ChevronDown size={14} />
          </button>
          <div className="dropdown-menu">
            {cropTabs.map((tab) => {
              const Icon = tab.Icon;
              return (
                <button
                  key={tab.value}
                  type="button"
                  className={tab.value === crop && section === "analytics" ? "active" : ""}
                  onClick={() => onAnalyticsOpen(tab.value)}
                >
                  <Icon size={16} />
                  {tab.label}
                </button>
              );
            })}
            <button
              type="button"
              className={section === "methodology" ? "active" : ""}
              onClick={() => {
                onSectionChange("methodology");
                onPriceMenuOpenChange(false);
              }}
            >
              <BookOpenCheck size={16} />
              Thuật toán dự báo
            </button>
          </div>
        </div>
      </div>
      <div className="account-menu">
        <button type="button" className="account-trigger" onClick={() => onAuthOpenChange(!authOpen)}>
          <UserRound size={16} />
          {user ? user.display_name : "Tài khoản"}
        </button>
        {authOpen ? (
          <div className="account-popover">
            {user ? (
              <>
                <strong>{user.display_name}</strong>
                <span>{user.email}</span>
                <button type="button" onClick={signOut}>Đăng xuất</button>
              </>
            ) : (
              <>
                <div className="auth-mode-tabs" role="tablist" aria-label="Chọn đăng nhập hoặc đăng ký">
                  <button type="button" className={authMode === "login" ? "active" : ""} onClick={() => onAuthModeChange("login")}>
                    Đăng nhập
                  </button>
                  <button type="button" className={authMode === "register" ? "active" : ""} onClick={() => onAuthModeChange("register")}>
                    Đăng ký
                  </button>
                </div>
                {authMode === "register" ? (
                  <label>
                    Họ tên
                    <input value={authName} onChange={(event) => onAuthNameChange(event.target.value)} autoComplete="name" />
                  </label>
                ) : null}
                <label>
                  Email
                  <input value={authEmail} onChange={(event) => onAuthEmailChange(event.target.value)} type="email" autoComplete="email" />
                </label>
                <label>
                  Mật khẩu
                  <input
                    value={authPassword}
                    onChange={(event) => onAuthPasswordChange(event.target.value)}
                    type="password"
                    autoComplete={authMode === "login" ? "current-password" : "new-password"}
                  />
                </label>
                <div className={`auth-actions auth-actions-${authMode}`}>
                  <button type="button" onClick={() => onAuthSubmit("login")}>Đăng nhập</button>
                  <button type="button" onClick={() => onAuthSubmit("register")}>Tạo tài khoản</button>
                </div>
              </>
            )}
          </div>
        ) : null}
      </div>
    </nav>
  );
}
