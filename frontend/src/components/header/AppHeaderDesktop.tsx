import { useEffect, useRef } from "react";
import { BookOpenCheck, PackageCheck, Search, UserRound } from "../icons";
import {
  cropItemLabel,
  headerText,
} from "./i18n";
import type { HeaderSurfaceProps } from "./types";

export function AppHeaderDesktop({
  section,
  crop,
  cropTabs,
  priceMenuOpen,
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
  onAuthOpenChange
}: HeaderSurfaceProps) {
  const headerRef = useRef<HTMLElement | null>(null);
  const copy = headerText[language];
  const dateParts = new Intl.DateTimeFormat(language === "en" ? "en-US" : "vi-VN", {
    weekday: "long",
    day: "2-digit",
    month: "2-digit",
    year: "numeric"
  }).formatToParts(new Date());
  const part = (type: Intl.DateTimeFormatPartTypes) => dateParts.find((item) => item.type === type)?.value ?? "";
  const dateLabel = `${part("weekday")} · ${part("day")}/${part("month")}/${part("year")} · GMT+7`;
  const isTerminal = section === "analytics";
  const isPriceActive = section === "inputPrices" || section === "methodology";
  const otherLanguage = language === "en" ? "VI" : "EN";

  const closeMenus = () => {
    onNewsMenuOpenChange(false);
    onFertilizerMenuOpenChange(false);
    onPriceMenuOpenChange(false);
  };

  const togglePriceMenu = () => {
    onPriceMenuOpenChange(!priceMenuOpen);
    onNewsMenuOpenChange(false);
    onFertilizerMenuOpenChange(false);
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
    <nav ref={headerRef} className={`site-head ${isTerminal ? "term" : "paper"}`} aria-label={copy.mainNavigation}>
      {!isTerminal ? (
        <div className="sh-util">
          <span className="date num">{dateLabel}</span>
          <span className="spacer" />
          <span className="live">{language === "en" ? "Live data" : "Dữ liệu trực tiếp"}</span>
          <button type="button" className="sh-lang" onClick={onLanguageToggle} aria-label={copy.switchLanguage}>
            {language === "en" ? "Language" : "Ngôn ngữ"}: <b>{copy.languageLabel}</b> · {otherLanguage}
          </button>
          <div className="sh-auth">
            <button type="button" className="sh-link-button" onClick={() => onAuthOpenChange(!authOpen)}>
              {userLabel ?? copy.login}
            </button>
            {authOpen ? <div className="account-popover sh-popover">{authContent}</div> : null}
          </div>
        </div>
      ) : null}

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
          <span className="wd">{language === "en" ? <>Agri<span>Forecast</span></> : <>Dự báo<span>NôngSản</span></>}</span>
          {isTerminal ? <span className="mode">Terminal</span> : null}
        </button>

        <nav className="sh-nav" aria-label={copy.mainNavigation}>
          <button type="button" className={section === "home" ? "active" : ""} onClick={() => { onSectionChange("home"); closeMenus(); }}>
            {language === "en" ? "Home" : "Trang chủ"}
          </button>
          <div className={`sh-dropdown ${isPriceActive ? "active" : ""} ${priceMenuOpen ? "open" : ""}`}>
            <button type="button" className={isPriceActive ? "active" : ""} aria-expanded={priceMenuOpen} onClick={togglePriceMenu}>
              {language === "en" ? "Commodities" : "Nông sản"} <span className="caret">▾</span>
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
                    <Icon size={15} />
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
                <PackageCheck size={15} />
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
                <BookOpenCheck size={15} />
                {copy.forecastAlgorithm}
              </button>
            </div>
          </div>
          <button type="button" className={section === "analytics" ? "active" : ""} onClick={() => { onAnalyticsOpen(crop); closeMenus(); }}>
            {language === "en" ? "Analysis" : "Phân tích"}
          </button>
          <button type="button" className={section === "news" ? "active" : ""} onClick={() => { onNewsOpen("latest"); closeMenus(); }}>
            {language === "en" ? "News" : "Tin tức"}
          </button>
          <button type="button" className={section === "guides" ? "active" : ""} onClick={() => { onSectionChange("guides"); closeMenus(); }}>
            {language === "en" ? "Guides" : "Hướng dẫn"}
          </button>
          <button type="button" className={section === "roi" ? "active" : ""} onClick={() => { onSectionChange("roi"); closeMenus(); }}>
            {language === "en" ? "ROI" : "ROI"}
          </button>
        </nav>

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
            <Search size={13} />
            <span>{language === "en" ? "Search crops, prices, regions..." : "Tìm sầu riêng, cà phê, vùng trồng..."}</span>
          </button>
          {isTerminal ? (
            <div className="sh-auth">
              <button type="button" className="sh-btn" onClick={() => onAuthOpenChange(!authOpen)}>
                <UserRound size={14} />
                {userLabel ?? copy.login}
              </button>
              {authOpen ? <div className="account-popover sh-popover">{authContent}</div> : null}
            </div>
          ) : (
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
          )}
        </div>
      </div>
    </nav>
  );
}
