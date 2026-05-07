import { useEffect, useRef } from "react";
import { BookOpenCheck, ChevronDown, Leaf, UserRound } from "../icons";
import { fertilizerMenuItems, newsMenuItems } from "./navItems";
import type { HeaderSurfaceProps } from "./types";

export function AppHeaderDesktop({
  section,
  crop,
  newsView,
  mainSections,
  cropTabs,
  priceMenuOpen,
  newsMenuOpen,
  fertilizerMenuOpen,
  authOpen,
  authContent,
  userLabel,
  onSectionChange,
  onAnalyticsOpen,
  onNewsOpen,
  onPriceMenuOpenChange,
  onNewsMenuOpenChange,
  onFertilizerMenuOpenChange,
  onAuthOpenChange
}: HeaderSurfaceProps) {
  const headerRef = useRef<HTMLElement | null>(null);

  const closeMenus = () => {
    onNewsMenuOpenChange(false);
    onFertilizerMenuOpenChange(false);
    onPriceMenuOpenChange(false);
  };

  const toggleDesktopMenu = (menu: "news" | "fertilizer" | "price") => {
    if (menu === "news") {
      onNewsMenuOpenChange(!newsMenuOpen);
      onFertilizerMenuOpenChange(false);
      onPriceMenuOpenChange(false);
    } else if (menu === "fertilizer") {
      onFertilizerMenuOpenChange(!fertilizerMenuOpen);
      onNewsMenuOpenChange(false);
      onPriceMenuOpenChange(false);
    } else {
      onPriceMenuOpenChange(!priceMenuOpen);
      onNewsMenuOpenChange(false);
      onFertilizerMenuOpenChange(false);
    }
  };

  useEffect(() => {
    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Node;
      if (headerRef.current?.contains(target)) return;
      closeMenus();
      onAuthOpenChange(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [onAuthOpenChange]);

  return (
    <nav ref={headerRef} className="menu-bar" aria-label="Điều hướng chính">
      <div className="brand-title">
        <Leaf size={21} />
        <span>DỰ BÁO NÔNG SẢN</span>
      </div>
      <div className="main-nav">
        {mainSections.map((item) => {
          const Icon = item.Icon;
          if (item.value === "news") {
            return (
              <div key={item.value} className={["nav-dropdown", section === "news" ? "active" : "", newsMenuOpen ? "open" : ""].filter(Boolean).join(" ")}>
                <button type="button" className="tab-button" aria-expanded={newsMenuOpen} onClick={() => toggleDesktopMenu("news")}>
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
                        onClick={() => {
                          onNewsOpen(newsItem.value);
                          closeMenus();
                        }}
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
              >
                <button type="button" className="tab-button" aria-expanded={fertilizerMenuOpen} onClick={() => toggleDesktopMenu("fertilizer")}>
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
                          closeMenus();
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
              onClick={() => {
                onSectionChange(item.value);
                closeMenus();
              }}
              type="button"
            >
              <Icon size={16} />
              {item.label}
            </button>
          );
        })}

        <div className={["nav-dropdown", section === "analytics" || section === "methodology" ? "active" : "", priceMenuOpen ? "open" : ""].filter(Boolean).join(" ")}>
          <button type="button" className="tab-button" aria-expanded={priceMenuOpen} onClick={() => toggleDesktopMenu("price")}>
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
                  onClick={() => {
                    onAnalyticsOpen(tab.value);
                    closeMenus();
                  }}
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
                closeMenus();
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
          {userLabel ?? "Tài khoản"}
        </button>
        {authOpen ? <div className="account-popover">{authContent}</div> : null}
      </div>
    </nav>
  );
}
