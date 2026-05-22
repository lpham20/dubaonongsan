import { useEffect, useRef, useState } from "react";
import { Leaf, Menu, UserRound, X } from "../icons";
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
    } else if (section === "fertilizer" || section === "fertilizerMethodology" || section === "yieldFeedback") {
      setMobileGroup("fertilizer");
    } else if (section === "analytics" || section === "inputPrices" || section === "methodology") {
      setMobileGroup("price");
    } else {
      setMobileGroup(null);
    }
  }, [drawerOpen, section]);

  return (
    <nav ref={headerRef} className="menu-bar mobile-menu-bar" aria-label="Điều hướng chính">
      <button type="button" className="brand-title mobile-brand-button" onClick={() => navigateMobile(() => onSectionChange("home"))}>
        <Leaf size={20} />
        <span>DỰ BÁO NÔNG SẢN</span>
      </button>
      <button
        ref={menuButtonRef}
        type="button"
        className="mobile-menu-trigger"
        aria-label="Mở menu"
        aria-expanded={drawerOpen}
        aria-controls="mobile-nav-drawer"
        onClick={() => setDrawerOpen(true)}
      >
        <Menu size={24} />
      </button>
      <button
        type="button"
        className="mobile-header-account-trigger"
        aria-label={userLabel ? `Tài khoản ${userLabel}` : "Mở tài khoản"}
        onClick={() => {
          setDrawerOpen(false);
          onAuthOpenChange(true);
        }}
      >
        <UserRound size={24} />
        <span className="sr-only">{userLabel ?? "Tài khoản"}</span>
      </button>

      <div className={drawerOpen ? "mobile-drawer-backdrop open" : "mobile-drawer-backdrop"} onClick={closeDrawer} />
      <div
        id="mobile-nav-drawer"
        ref={drawerRef}
        className={drawerOpen ? "mobile-nav-drawer open" : "mobile-nav-drawer"}
        role="dialog"
        aria-modal="true"
        aria-label="Menu điều hướng"
      >
        <div className="mobile-drawer-head">
          <div className="brand-title">
            <Leaf size={20} />
            <span>DỰ BÁO NÔNG SẢN</span>
          </div>
          <button type="button" aria-label="Đóng menu" onClick={closeDrawer}>
            <X size={22} />
          </button>
        </div>
        <div className="mobile-drawer-list">
          <button type="button" className={section === "home" ? "active" : ""} onClick={() => navigateMobile(() => onSectionChange("home"))}>
            Trang chủ
          </button>
          <MobileAccordion
            title="Tin tức"
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
                {item.label}
              </button>
            ))}
          </MobileAccordion>
          <button type="button" className={section === "guides" ? "active" : ""} onClick={() => navigateMobile(() => onSectionChange("guides"))}>
            Hướng dẫn
          </button>
          <MobileAccordion
            title="Khuyến nghị bón phân"
            open={mobileGroup === "fertilizer"}
            active={section === "fertilizer" || section === "fertilizerMethodology" || section === "yieldFeedback"}
            onToggle={() => setMobileGroup(mobileGroup === "fertilizer" ? null : "fertilizer")}
          >
            {fertilizerMenuItems.map((item) => (
              <button
                key={item.value}
                type="button"
                className={section === item.value ? "active" : ""}
                onClick={() => navigateMobile(() => onSectionChange(item.value))}
              >
                {item.label}
              </button>
            ))}
          </MobileAccordion>
          <MobileAccordion
            title="Dự báo giá"
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
                {tab.label}
              </button>
            ))}
            <button
              type="button"
              className={section === "inputPrices" ? "active" : ""}
              onClick={() => navigateMobile(() => onSectionChange("inputPrices"))}
            >
              Giá phân bón đầu vào
            </button>
            <button
              type="button"
              className={section === "methodology" ? "active" : ""}
              onClick={() => navigateMobile(() => onSectionChange("methodology"))}
            >
              Thuật toán dự báo
            </button>
          </MobileAccordion>
          <button
            type="button"
            onClick={() => {
              setDrawerOpen(false);
              onAuthOpenChange(true);
            }}
          >
            {userLabel ?? "Tài khoản"}
          </button>
        </div>
      </div>
      {authOpen ? (
        <>
          <div className="mobile-auth-backdrop" onClick={() => onAuthOpenChange(false)} />
          <div className="account-popover mobile-auth-sheet">
            <button type="button" className="mobile-auth-close" aria-label="Đóng tài khoản" onClick={() => onAuthOpenChange(false)}>
              <X size={20} />
            </button>
            {authContent}
          </div>
        </>
      ) : null}
    </nav>
  );
}
