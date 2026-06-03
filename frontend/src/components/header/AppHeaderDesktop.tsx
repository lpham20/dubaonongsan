import { useEffect, useRef } from "react";
import { BookOpenCheck, ChevronDown, Leaf, PackageCheck, Search, UserRound } from "../icons";
import {
  cropItemLabel,
  fertilizerGroupLabel,
  fertilizerItemLabel,
  headerText,
  mainSectionLabel,
  newsItemLabel
} from "./i18n";
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
  language,
  onLanguageToggle,
  onSectionChange,
  onAnalyticsOpen,
  onNewsOpen,
  onPriceMenuOpenChange,
  onNewsMenuOpenChange,
  onFertilizerMenuOpenChange,
  onAuthOpenChange,
  onAuthModeChange
}: HeaderSurfaceProps) {
  const headerRef = useRef<HTMLElement | null>(null);
  const fertilizerActive = fertilizerMenuItems.some((item) => item.value === section);
  const copy = headerText[language];
  const dateLabel = new Intl.DateTimeFormat(language === "en" ? "en-US" : "vi-VN", {
    weekday: "long",
    day: "2-digit",
    month: "2-digit",
    year: "numeric"
  }).format(new Date());

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

  const toggleAccount = () => {
    if (!authOpen && !userLabel) {
      onAuthModeChange("login");
    }
    onAuthOpenChange(!authOpen);
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
    <nav ref={headerRef} className="menu-bar paper-mast" aria-label={copy.mainNavigation}>
      <div className="paper-mast-util">
        <span className="paper-mast-date num">{dateLabel}</span>
        <span className="paper-mast-spacer" />
        <div className="account-menu">
          <button type="button" className="language-toggle" onClick={onLanguageToggle} aria-label={copy.switchLanguage}>
            <span className={`language-flag language-flag-${language}`} aria-hidden="true" />
            <span>{copy.languageLabel}</span>
          </button>
          <button type="button" className="account-trigger" onClick={toggleAccount}>
            <UserRound size={16} />
            {userLabel ?? copy.account}
          </button>
          {authOpen ? <div className="account-popover">{authContent}</div> : null}
        </div>
      </div>

      <div className="paper-mast-brandrow">
        <button
          type="button"
          className="brand-title"
          onClick={() => {
            onSectionChange("home");
            closeMenus();
          }}
        >
          <Leaf size={21} />
          <span>{copy.brand}</span>
        </button>
        <span className="paper-mast-tag">
          {language === "en"
            ? "Vietnam agricultural price intelligence, field guides and 30-day ML forecasts."
            : "Nền tảng dự báo giá nông sản Việt Nam, hướng dẫn kỹ thuật và dự báo 30 ngày bằng ML."}
        </span>
        <span className="paper-mast-spacer" />
        <button
          type="button"
          className="paper-mast-search"
          onClick={() => {
            onNewsOpen("latest");
            closeMenus();
          }}
        >
          <Search size={14} />
          <span>{language === "en" ? "Search crops, prices, growing regions..." : "Tìm sầu riêng, cà phê, vùng trồng..."}</span>
        </button>
        <button
          type="button"
          className="paper-mast-terminal"
          onClick={() => {
            onAnalyticsOpen(crop);
            closeMenus();
          }}
        >
          {language === "en" ? "Open terminal" : "Mở terminal"}
        </button>
      </div>

      <div className="paper-mast-navrow">
        <div className="main-nav">
          {mainSections.map((item) => {
            const Icon = item.Icon;
            if (item.value === "news") {
              return (
                <div key={item.value} className={["nav-dropdown", section === "news" ? "active" : "", newsMenuOpen ? "open" : ""].filter(Boolean).join(" ")}>
                  <button type="button" className="tab-button" aria-expanded={newsMenuOpen} onClick={() => toggleDesktopMenu("news")}>
                    <Icon size={16} />
                    {mainSectionLabel(language, item.value, item.label)}
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
                          {newsItemLabel(language, newsItem.value)}
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
                  className={["nav-dropdown", fertilizerActive ? "active" : "", fertilizerMenuOpen ? "open" : ""].filter(Boolean).join(" ")}
                >
                  <button type="button" className="tab-button" aria-expanded={fertilizerMenuOpen} onClick={() => toggleDesktopMenu("fertilizer")}>
                    <Icon size={16} />
                    {mainSectionLabel(language, item.value, item.label)}
                    <ChevronDown size={14} />
                  </button>
                  <div className="dropdown-menu">
                    {fertilizerMenuItems.map((fertilizerItem) => {
                      const FertilizerIcon = fertilizerItem.Icon;
                      return (
                        <div key={fertilizerItem.value} className="dropdown-menu-row">
                          {fertilizerItem.groupLabel ? <span className="dropdown-section-label">{fertilizerGroupLabel(language, fertilizerItem.groupLabel)}</span> : null}
                          <button
                            type="button"
                            className={[section === fertilizerItem.value ? "active" : "", fertilizerItem.hierarchy === "child" ? "dropdown-child-item" : ""]
                              .filter(Boolean)
                              .join(" ")}
                            onClick={() => {
                              onSectionChange(fertilizerItem.value);
                              closeMenus();
                            }}
                          >
                            <FertilizerIcon size={16} />
                            {fertilizerItemLabel(language, fertilizerItem.value, fertilizerItem.label)}
                          </button>
                        </div>
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
                {mainSectionLabel(language, item.value, item.label)}
              </button>
            );
          })}

          <div
            className={[
              "nav-dropdown",
              section === "analytics" || section === "inputPrices" || section === "methodology" ? "active" : "",
              priceMenuOpen ? "open" : ""
            ]
              .filter(Boolean)
              .join(" ")}
          >
            <button type="button" className="tab-button" aria-expanded={priceMenuOpen} onClick={() => toggleDesktopMenu("price")}>
              <Leaf size={16} />
              {copy.priceForecast}
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
                    {cropItemLabel(language, tab.value)}
                  </button>
                );
              })}
              <button
                type="button"
                className={section === "inputPrices" ? "active" : ""}
                onClick={() => {
                  onSectionChange("inputPrices");
                  closeMenus();
                }}
              >
                <PackageCheck size={16} />
                {copy.worldFertilizer}
              </button>
              <button
                type="button"
                className={section === "methodology" ? "active" : ""}
                onClick={() => {
                  onSectionChange("methodology");
                  closeMenus();
                }}
              >
                <BookOpenCheck size={16} />
                {copy.forecastAlgorithm}
              </button>
            </div>
          </div>
        </div>
        <div className="paper-mast-live">{language === "en" ? "Live data" : "Dữ liệu trực tiếp"}</div>
      </div>
    </nav>
  );
}
