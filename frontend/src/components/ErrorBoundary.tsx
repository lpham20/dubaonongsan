import { Component, type ErrorInfo, type ReactNode } from "react";
import * as Sentry from "@sentry/react";

type Props = {
  children: ReactNode;
  fallback?: (error: Error, reset: () => void) => ReactNode;
  resetKey?: string;
};

type State = {
  error: Error | null;
};

const CHUNK_RELOAD_KEY = "marketai:chunk-reload-at";
const CHUNK_RELOAD_WINDOW_MS = 30_000;

export function isRecoverableChunkError(error: unknown): boolean {
  const message = error instanceof Error ? error.message : String(error ?? "");
  return /ChunkLoadError|Loading chunk|dynamically imported module|Failed to fetch dynamically imported module|Importing a module script failed|module script/i.test(
    message
  );
}

async function clearStaleAppCaches() {
  if (typeof window === "undefined") return;
  if ("serviceWorker" in navigator) {
    const registrations = await navigator.serviceWorker.getRegistrations();
    await Promise.all(registrations.map((registration) => registration.unregister()));
  }
  if ("caches" in window) {
    const keys = await window.caches.keys();
    await Promise.all(keys.map((key) => window.caches.delete(key)));
  }
}

function hardReloadForNewBundle() {
  void clearStaleAppCaches().finally(() => {
    window.location.reload();
  });
}

export function reloadOnceForNewBundle(): boolean {
  if (typeof window === "undefined") return false;
  const lastReload = Number(window.sessionStorage.getItem(CHUNK_RELOAD_KEY) ?? "0");
  const now = Date.now();
  if (now - lastReload < CHUNK_RELOAD_WINDOW_MS) return false;
  window.sessionStorage.setItem(CHUNK_RELOAD_KEY, String(now));
  hardReloadForNewBundle();
  return true;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, _info: ErrorInfo) {
    Sentry.captureException(error);
    if (isRecoverableChunkError(error)) {
      reloadOnceForNewBundle();
    }
  }

  componentDidUpdate(previousProps: Props) {
    if (this.state.error && previousProps.resetKey !== this.props.resetKey) {
      this.setState({ error: null });
    }
  }

  reset = () => {
    this.setState({ error: null });
  };

  render() {
    if (this.state.error) {
      return (
        this.props.fallback?.(this.state.error, this.reset) ?? (
          <div className="error-boundary" role="alert">
            <h3>Đã có lỗi xảy ra</h3>
            <p>Vui lòng tải lại trang. Nếu lỗi vẫn còn, hãy báo cho quản trị viên.</p>
            <button
              type="button"
              onClick={() => {
                if (this.state.error && isRecoverableChunkError(this.state.error)) {
                  window.sessionStorage.removeItem(CHUNK_RELOAD_KEY);
                  hardReloadForNewBundle();
                  return;
                }
                this.reset();
              }}
            >
              Tải lại
            </button>
          </div>
        )
      );
    }
    return this.props.children;
  }
}
