import type { AppLanguage } from "../contexts/LanguageContext";

export const languagePrefixes: Record<AppLanguage, "vn" | "en"> = {
  vi: "vn",
  en: "en"
};

export function languageFromPrefix(value: string | undefined): AppLanguage | null {
  if (value === "en") return "en";
  if (value === "vn" || value === "vi") return "vi";
  return null;
}

export function splitLanguagePath(pathnameInput: string) {
  const pathname = pathnameInput || "/";
  const parts = pathname.split("/").filter(Boolean);
  const language = languageFromPrefix(parts[0]);
  if (!language) {
    return { language: null, pathname };
  }
  const rest = parts.slice(1).join("/");
  return {
    language,
    pathname: rest ? `/${rest}` : "/"
  };
}

export function withLanguagePrefix(pathInput: string, language: AppLanguage) {
  if (!pathInput || pathInput === "#") return pathInput;
  if (/^(https?:|mailto:|tel:)/i.test(pathInput)) return pathInput;
  const [rawPathAndSearch, hash = ""] = pathInput.split("#", 2);
  const [rawPath, search = ""] = rawPathAndSearch.split("?", 2);
  const normalizedPath = rawPath.startsWith("/") ? rawPath : `/${rawPath}`;
  const stripped = splitLanguagePath(normalizedPath).pathname;
  if (language === "vi") {
    return `${stripped}${search ? `?${search}` : ""}${hash ? `#${hash}` : ""}`;
  }
  const prefix = `/${languagePrefixes[language]}`;
  const path = stripped === "/" ? prefix : `${prefix}${stripped}`;
  return `${path}${search ? `?${search}` : ""}${hash ? `#${hash}` : ""}`;
}

export function pathWithoutLanguagePrefix(pathname: string) {
  return splitLanguagePath(pathname).pathname;
}
