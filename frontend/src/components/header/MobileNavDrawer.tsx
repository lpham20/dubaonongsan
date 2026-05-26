import { useEffect, useRef, useState } from "react";
import { Leaf, Menu, UserRound, X } from "../icons";
import {
  cropItemLabel,
  fertilizerGroupLabel,
  fertilizerItemLabel,
  headerText,
  newsItemLabel
} from "./i18n";
import { fertilizerMenuItems, newsMenuItems } from "./navItems";
import { MobileAccordion } from "./MobileAccordion";
import type { HeaderSurfaceProps } from "./types";

export function MobileNavDrawer({
  section,
  crop,
  newsView,
  cropTabs,
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
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [mobileGroup, setMobileGroup] = useState<"news" | "fertilizer" | "price" | null>(null);
  const headerRef = useRef<HTMLElement | null>(null);
  const drawerRef = useRef<HTMLDivElement | null>(null);
  const menuButtonRef = useRef<HTMLButtonElement | null>(null);
  const fertilizerActive = fertilizerMenuItems.some((item) => item.value === section);
  const copy = headerText[language];

  const closeMenus = () => {
    onNewsMenuOpenChange(false);
    onFertilizerMenuOpenChange(false);
    onPriceMenuOpenChange(false);
  };

  const closeDrawer = () => {
    setDrawerOpen(false);
    menuButtonRef.current?.focus();
  };

  const navigateMobile = (callback: () => void) => {
    callback();
    closeMenus();
    setDrawerOpen(false);
  };

  useEffect(() => {
    document.body.classList.toggle("mobile-drawer-locked", drawerOpen || authOpen);
    return () => document.body.classList.remove("mobile-drawer-locked");
  }, [authOpen, drawerOpen]);

  useEffect(() => {
    if (!drawerOpen || !headerRef.current?.parentElement) return;
    const parent = headerRef.current.parentElement;
    const hiddenSiblings: Array<{ element: HTMLElement; previous: string | null }> = [];
    Array.from(parent.children).forEach((child) => {
      if (child === headerRef.current || !(child instanceof HTMLElement)) return;
      hiddenSiblings.push({ element: child, previous: child.getAttribute("aria-hidden") });
      child.setAttribute("aria-hidden", "true");
    });
    return () => {
      hiddenSiblings.forEach(({ element, previous }) => {
        if (previous === null) {
          element.removeAttribute("aria-hidden");
        } else {
          element.setAttribute("aria-hidden", previous);
        }
      });
    };
  }, [drawerOpen]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        closeMenus();
        setDrawerOpen(false);
        onAuthOpenChange(false);
      }
      if (!drawerOpen || event.key !== "Tab" || !drawerRef.current) return;
      const focusable = drawerRef.current.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [drawerOpen, onAuthOpenChange]);

  useEffect(() => {
    if (!drawerOpen || !drawerRef.current) return;
    drawerRef.current.querySelector<HTMLElement>("button")?.focus();
  }, [drawerOpen]);

  useEffect(() => {
    if (!drawerOpen) return;
    if (section === "news") {
      setMobileGroup("news");
    } else if (fertilizerActive) {
      setMobileGroup("fertilizer");
    } else if (section === "analytics" || section === "inputPrices" || section === "methodology") {
      setMobileGroup("price");
    } else {
      setMobileGroup(null);
    }
  }, [drawerOpen, section]);

  return (
    <nav ref={headerRef} className="menu-bar mobile-menu-bar" aria-label={copy.mainNavigation}>
      <button type="button" className="brand-title mobile-brand-button" onClick={() => navigateMobile(() => onSectionChange("home"))}>
        <Leaf size={20} />
        <span>{copy.brand}</span>
      </button>
      <button type="button" className="mobile-language-toggle" onClick={onLanguageToggle} aria-label={copy.switchLanguage}>
        <span className={`language-flag language-flag-${language}`} aria-hidden="true" />
        <span>{copy.languageLabel}</span>
      </button>
      <button
        ref={menuButtonRef}
        type="button"
        className="mobile-menu-trigger"
        aria-label={copy.openMenu}
        aria-expanded={drawerOpen}
        aria-controls="mobile-nav-drawer"
        onClick={() => setDrawerOpen(true)}
      >
        <Menu size={24} />
      </button>
      <button
        type="button"
        className="mobile-header-account-trigger"
        aria-label={userLabel ? `${copy.account} ${userLabel}` : copy.openAccount}
        onClick={() => {
          setDrawerOpen(false);
          onAuthOpenChange(true);
        }}
      >
        <UserRound size={24} />
        <span className="sr-only">{userLabel ?? copy.account}</span>
      </button>

      <div className={drawerOpen ? "mobile-drawer-backdrop open" : "mobile-drawer-backdrop"} onClick={closeDrawer} />
      <div
        id="mobile-nav-drawer"
        ref={drawerRef}
        className={drawerOpen ? "mobile-nav-drawer open" : "mobile-nav-drawer"}
        role="dialog"
        aria-modal="true"
        aria-label={copy.mobileDrawer}
      >
        <div className="mobile-drawer-head">
          <div className="brand-title">
            <Leaf size={20} />
            <span>{copy.brand}</span>
          </div>
          <button type="button" aria-label={copy.closeMenu} onClick={closeDrawer}>
            <X size={22} />
          </button>
        </div>
        <div className="mobile-drawer-list">
          <button type="button" className={section === "home" ? "active" : ""} onClick={() => navigateMobile(() => onSectionChange("home"))}>
            {language === "en" ? "Home" : "Trang chủ"}
          </button>
          <MobileAccordion
            title={language === "en" ? "News" : "Tin tức"}
            open={mobileGroup === "news"}
            active={section === "news"}
            onToggle={() => setMobileGroup(mobileGroup === "news" ? null : "news")}
          >
            {newsMenuItems.map((item) => (
              <button
                key={item.value}
                type="button"
                className={section === "news" && newsView === item.value ? "active" : ""}
                onClick={() => navigateMobile(() => onNewsOpen(item.value))}
              >
                {newsItemLabel(language, item.value)}
              </button>
            ))}
          </MobileAccordion>
          <button type="button" className={section === "guides" ? "active" : ""} onClick={() => navigateMobile(() => onSectionChange("guides"))}>
            {language === "en" ? "Guides" : "Hướng dẫn"}
          </button>
          <MobileAccordion
            title={language === "en" ? "Advisory" : "Khuyến nghị"}
            open={mobileGroup === "fertilizer"}
            active={fertilizerActive}
            onToggle={() => setMobileGroup(mobileGroup === "fertilizer" ? null : "fertilizer")}
          >
            {fertilizerMenuItems.map((item) => (
              <div key={item.value} className="mobile-accordion-row">
                {item.groupLabel ? <span className="mobile-section-label">{fertilizerGroupLabel(language, item.groupLabel)}</span> : null}
                <button
                  type="button"
                  className={[
                    section === item.value ? "active" : "",
                    item.hierarchy === "child" ? "mobile-child-item" : ""
                  ].filter(Boolean).join(" ")}
                  onClick={() => navigateMobile(() => onSectionChange(item.value))}
                >
                  {fertilizerItemLabel(language, item.value, item.label)}
                </button>
              </div>
            ))}
          </MobileAccordion>
          <MobileAccordion
            title={copy.forecastPrice}
            open={mobileGroup === "price"}
            active={section === "analytics" || section === "inputPrices" || section === "methodology"}
            onToggle={() => setMobileGroup(mobileGroup === "price" ? null : "price")}
          >
            {cropTabs.map((tab) => (
              <button
                key={tab.value}
                type="button"
                className={section === "analytics" && crop === tab.value ? "active" : ""}
                onClick={() => navigateMobile(() => onAnalyticsOpen(tab.value))}
              >
                {cropItemLabel(language, tab.value)}
              </button>
            ))}
            <button
              type="button"
              className={section === "inputPrices" ? "active" : ""}
              onClick={() => navigateMobile(() => onSectionChange("inputPrices"))}
            >
              {copy.worldFertilizer}
            </button>
            <button
              type="button"
              className={section === "methodology" ? "active" : ""}
              onClick={() => navigateMobile(() => onSectionChange("methodology"))}
            >
              {copy.forecastAlgorithm}
            </button>
          </MobileAccordion>
          <button
            type="button"
            onClick={() => {
              setDrawerOpen(false);
              onAuthOpenChange(true);
            }}
          >
            {userLabel ?? copy.account}
          </button>
        </div>
      </div>
      {authOpen ? (
        <>
          <div className="mobile-auth-backdrop" onClick={() => onAuthOpenChange(false)} />
          <div className="account-popover mobile-auth-sheet">
            <button type="button" className="mobile-auth-close" aria-label={copy.closeMenu} onClick={() => onAuthOpenChange(false)}>
              <X size={20} />
            </button>
            {authContent}
          </div>
        </>
      ) : null}
    </nav>
  );
}
