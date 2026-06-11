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

  const headerTone = section === "analytics" ? "term" : "paper";

  return (
    <nav ref={headerRef} className={`site-head ${headerTone}`} aria-label={copy.mainNavigation}>
      <div className="sh-util">
        <span className="date num">{dateLabel}</span>
        <span className="spacer" />
        <span className="live">{language === "en" ? "Live data" : "Dữ liệu trực tiếp"}</span>
        <button type="button" className="sh-lang" onClick={onLanguageToggle} aria-label={copy.switchLanguage}>
          <span className={`language-flag language-flag-${language}`} aria-hidden="true" />
          <b>{copy.languageLabel}</b>
        </button>
        <div className="sh-auth">
          <button type="button" className="sh-link-button" onClick={toggleAccount}>
            <UserRound size={15} />
            {userLabel ?? copy.account}
          </button>
          {authOpen ? <div className="sh-popover">{authContent}</div> : null}
        </div>
      </div>

      <div className="sh-main">
        <button
          type="button"
          className="sh-logo"
          onClick={() => {
            onSectionChange("home");
            closeMenus();
          }}
        >
          <span className="mk" />
          <span className="wd">
            {language === "en" ? "Agri" : "Dự báo"}
            <span>{language === "en" ? "Forecast" : "NôngSản"}</span>
          </span>
        </button>

        <div className="sh-nav">
          {mainSections.map((item) => {
            const Icon = item.Icon;
            if (item.value === "news") {
              return (
                <div key={item.value} className={["sh-dropdown", section === "news" ? "active" : "", newsMenuOpen ? "open" : ""].filter(Boolean).join(" ")}>
                  <button type="button" aria-expanded={newsMenuOpen} onClick={() => toggleDesktopMenu("news")}>
                    <Icon size={16} />
                    {mainSectionLabel(language, item.value, item.label)}
                    <ChevronDown className="caret" size={14} />
                  </button>
                  <div className="sh-menu">
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
                  className={["sh-dropdown", fertilizerActive ? "active" : "", fertilizerMenuOpen ? "open" : ""].filter(Boolean).join(" ")}
                >
                  <button type="button" aria-expanded={fertilizerMenuOpen} onClick={() => toggleDesktopMenu("fertilizer")}>
                    <Icon size={16} />
                    {mainSectionLabel(language, item.value, item.label)}
                    <ChevronDown className="caret" size={14} />
                  </button>
                  <div className="sh-menu">
                    {fertilizerMenuItems.map((fertilizerItem) => {
                      const FertilizerIcon = fertilizerItem.Icon;
                      return (
                        <div key={fertilizerItem.value} className="sh-menu-row">
                          {fertilizerItem.groupLabel ? <span className="sh-menu-section">{fertilizerGroupLabel(language, fertilizerItem.groupLabel)}</span> : null}
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
                className={item.value === section ? "active" : ""}
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
              "sh-dropdown",
              section === "analytics" || section === "inputPrices" || section === "methodology" ? "active" : "",
              priceMenuOpen ? "open" : ""
            ]
              .filter(Boolean)
              .join(" ")}
          >
            <button type="button" aria-expanded={priceMenuOpen} onClick={() => toggleDesktopMenu("price")}>
              <Leaf size={16} />
              {copy.priceForecast}
              <ChevronDown className="caret" size={14} />
            </button>
            <div className="sh-menu">
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

        <span className="sh-spacer" />
        <div className="sh-tools">
          <button
            type="button"
            className="sh-search"
            onClick={() => {
              onNewsOpen("latest");
              closeMenus();
            }}
          >
            <Search size={14} />
            <span>{language === "en" ? "Search crops, prices, growing regions..." : "Tìm nông sản, giá, vùng trồng..."}</span>
          </button>
          <button
            type="button"
            className="sh-btn primary"
            onClick={() => {
              onAnalyticsOpen(crop);
              closeMenus();
            }}
          >
            {language === "en" ? "Open terminal" : "Mở terminal"}
          </button>
        </div>
      </div>
    </nav>
  );
}
