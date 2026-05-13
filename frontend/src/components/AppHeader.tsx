import { useAuth } from "../contexts/AuthContext";
import { useMediaQuery } from "../hooks/useMediaQuery";
import { AppHeaderDesktop } from "./header/AppHeaderDesktop";
import { MobileNavDrawer } from "./header/MobileNavDrawer";
import type { AppHeaderProps } from "./header/types";

export function AppHeader(props: AppHeaderProps) {
  const { user, signOut } = useAuth();
  const isMobile = useMediaQuery("(max-width: 1023px)");
  const userLabel = user?.display_name ?? null;

  const authContent = user ? (
    <>
      <strong>{user.display_name}</strong>
      <span>{user.email}</span>
      <button type="button" onClick={signOut}>Đăng xuất</button>
    </>
  ) : (
    <>
      <div className="auth-mode-tabs" role="tablist" aria-label="Chọn đăng nhập hoặc đăng ký">
        <button type="button" className={props.authMode === "login" ? "active" : ""} onClick={() => props.onAuthModeChange("login")}>
          Đăng nhập
        </button>
        <button type="button" className={props.authMode === "register" ? "active" : ""} onClick={() => props.onAuthModeChange("register")}>
          Đăng ký
        </button>
      </div>
      {props.authMode === "register" ? (
        <label>
          Họ tên
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
        Mật khẩu
        <input
          value={props.authPassword}
          onChange={(event) => props.onAuthPasswordChange(event.target.value)}
          type="password"
          autoComplete={props.authMode === "login" ? "current-password" : "new-password"}
        />
      </label>
      <div className={`auth-actions auth-actions-${props.authMode}`}>
        <button type="button" onClick={() => props.onAuthSubmit("login")}>Đăng nhập</button>
        <button type="button" onClick={() => props.onAuthSubmit("register")}>Tạo tài khoản</button>
      </div>
    </>
  );

  const surfaceProps = { ...props, authContent, userLabel };

  return isMobile ? <MobileNavDrawer {...surfaceProps} /> : <AppHeaderDesktop {...surfaceProps} />;
}
