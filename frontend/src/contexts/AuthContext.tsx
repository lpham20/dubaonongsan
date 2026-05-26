import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { login as apiLogin, logout as apiLogout, register as apiRegister, type AuthSession, type AuthUser } from "../lib/api";

type AuthContextValue = {
  token: string;
  user: AuthUser | null;
  signIn: (email: string, password: string, signal?: AbortSignal) => Promise<AuthSession>;
  signUp: (email: string, password: string, displayName: string, signal?: AbortSignal) => Promise<AuthSession>;
  signOut: () => Promise<void>;
};

const TOKEN_KEY = "agri_price.token";
const USER_KEY = "agri_price.user";

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState(() => sessionStorage.getItem(TOKEN_KEY) ?? "");
  const [user, setUser] = useState<AuthUser | null>(() => {
    try {
      const saved = sessionStorage.getItem(USER_KEY);
      return saved ? (JSON.parse(saved) as AuthUser) : null;
    } catch {
      return null;
    }
  });

  function persist(session: AuthSession) {
    setToken(session.access_token);
    setUser(session.user);
    sessionStorage.setItem(TOKEN_KEY, session.access_token);
    sessionStorage.setItem(USER_KEY, JSON.stringify(session.user));
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }

  async function signIn(email: string, password: string, signal?: AbortSignal) {
    const session = await apiLogin(email, password, signal);
    if (signal?.aborted) throw new DOMException("Authentication request was cancelled.", "AbortError");
    persist(session);
    return session;
  }

  async function signUp(email: string, password: string, displayName: string, signal?: AbortSignal) {
    const session = await apiRegister(email, password, displayName, signal);
    if (signal?.aborted) throw new DOMException("Authentication request was cancelled.", "AbortError");
    persist(session);
    return session;
  }

  async function signOut() {
    const currentToken = token;
    if (currentToken) {
      await apiLogout(currentToken).catch(() => undefined);
    }
    setToken("");
    setUser(null);
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(USER_KEY);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }

  const value = useMemo(() => ({ token, user, signIn, signUp, signOut }), [token, user]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
