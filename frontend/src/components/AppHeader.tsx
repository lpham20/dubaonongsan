import { useAuth } from "../contexts/AuthContext";
import { useLanguage } from "../contexts/LanguageContext";
import { useMediaQuery } from "../hooks/useMediaQuery";
import { AppHeaderDesktop } from "./header/AppHeaderDesktop";
import { MobileNavDrawer } from "./header/MobileNavDrawer";
import { headerText } from "./header/i18n";
import type { AppHeaderProps } from "./header/types";

export function AppHeader(props: AppHeaderProps) {
  const { user, signOut } = useAuth();
  const { language, toggleLanguage } = useLanguage();
  const isMobile = useMediaQuery("(max-width: 1180px)");
  const userLabel = user?.display_name ?? null;
  const copy = headerText[language];

  const authContent = user ? (
    <>
      <strong>{user.display_name}</strong>
      <span>{user.email}</span>
      <button type="button" onClick={() => void signOut()}>{copy.logout}</button>
    </>
  ) : (
    <>
      <div className="auth-mode-tabs" role="tablist" aria-label={`${copy.login} / ${copy.register}`}>
        <button type="button" className={props.authMode === "login" ? "active" : ""} onClick={() => props.onAuthModeChange("login")}>
          {copy.login}
        </button>
        <button type="button" className={props.authMode === "register" ? "active" : ""} onClick={() => props.onAuthModeChange("register")}>
          {copy.register}
        </button>
      </div>
      {props.authMode === "register" ? (
        <label>
          {copy.fullName}
          <input value={props.authName} onChange={(event) => props.onAuthNameChange(event.target.value)} autoComplete="name" />
        </label>
      ) : null}
      <label>
        Email
        <input
          value={props.authEmail}
          onChange={(event) => props.onAuthEmailChange(event.target.value)}
          type="email"
          inputMode="email"
          autoComplete="email"
          autoCapitalize="none"
          autoCorrect="off"
        />
      </label>
      <label>
        {copy.password}
        <input
          value={props.authPassword}
          onChange={(event) => props.onAuthPasswordChange(event.target.value)}
          type="password"
          autoComplete={props.authMode === "login" ? "current-password" : "new-password"}
        />
      </label>
      <div className={`auth-actions auth-actions-${props.authMode}`}>
        <button type="button" onClick={() => props.onAuthSubmit("login")}>{copy.login}</button>
        <button type="button" onClick={() => props.onAuthSubmit("register")}>{copy.createAccount}</button>
      </div>
    </>
  );

  const surfaceProps = { ...props, authContent, userLabel, language, onLanguageToggle: toggleLanguage };

  return isMobile ? <MobileNavDrawer {...surfaceProps} /> : <AppHeaderDesktop {...surfaceProps} />;
}
