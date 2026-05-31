import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { splitLanguagePath } from "../lib/localizedRoutes";
import { trackEvent } from "../lib/analytics";

export type AppLanguage = "vi" | "en";

type LanguageContextValue = {
  language: AppLanguage;
  setLanguage: (language: AppLanguage) => void;
  toggleLanguage: () => void;
};

const LanguageContext = createContext<LanguageContextValue | null>(null);

function readInitialLanguage(): AppLanguage {
  if (typeof window === "undefined") return "vi";
  const pathLanguage = splitLanguagePath(window.location.pathname).language;
  if (pathLanguage) return pathLanguage;
  let stored: string | null = null;
  try {
    stored = window.localStorage.getItem("marketai.language");
  } catch {
    stored = null;
  }
  return stored === "en" ? "en" : "vi";
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<AppLanguage>(readInitialLanguage);

  const setLanguage = useCallback((nextLanguage: AppLanguage) => {
    setLanguageState((currentLanguage) => {
      if (currentLanguage !== nextLanguage) {
        trackEvent("language_changed", { from: currentLanguage, to: nextLanguage });
      }
      return nextLanguage;
    });
  }, []);

  const toggleLanguage = useCallback(() => {
    setLanguageState((currentLanguage) => {
      const nextLanguage = currentLanguage === "vi" ? "en" : "vi";
      trackEvent("language_changed", { from: currentLanguage, to: nextLanguage });
      return nextLanguage;
    });
  }, []);

  useEffect(() => {
    document.documentElement.lang = language === "en" ? "en" : "vi";
    try {
      window.localStorage.setItem("marketai.language", language);
    } catch {
      // Private browsing modes can reject localStorage writes; URL language still drives rendering.
    }
  }, [language]);

  const value = useMemo<LanguageContextValue>(
    () => ({
      language,
      setLanguage,
      toggleLanguage
    }),
    [language, setLanguage, toggleLanguage]
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used inside LanguageProvider");
  }
  return context;
}
