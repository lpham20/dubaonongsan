import { Component, type ErrorInfo, type ReactNode } from "react";

type Props = {
  children: ReactNode;
  fallback?: (error: Error) => ReactNode;
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

export function reloadOnceForNewBundle(): boolean {
  if (typeof window === "undefined") return false;
  const lastReload = Number(window.sessionStorage.getItem(CHUNK_RELOAD_KEY) ?? "0");
  const now = Date.now();
  if (now - lastReload < CHUNK_RELOAD_WINDOW_MS) return false;
  window.sessionStorage.setItem(CHUNK_RELOAD_KEY, String(now));
  window.location.reload();
  return true;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info);
    if (isRecoverableChunkError(error)) {
      reloadOnceForNewBundle();
    }
  }

  render() {
    if (this.state.error) {
      return (
        this.props.fallback?.(this.state.error) ?? (
          <div className="error-boundary" role="alert">
            <h3>Đã có lỗi xảy ra</h3>
            <p>Vui lòng tải lại trang. Nếu lỗi vẫn còn, hãy báo cho quản trị viên.</p>
            <button
              type="button"
              onClick={() => {
                if (this.state.error && isRecoverableChunkError(this.state.error)) {
                  window.sessionStorage.removeItem(CHUNK_RELOAD_KEY);
                  window.location.reload();
                  return;
                }
                this.setState({ error: null });
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
