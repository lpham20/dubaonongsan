import { Component, type ErrorInfo, type ReactNode } from "react";

type Props = {
  children: ReactNode;
  fallback?: (error: Error) => ReactNode;
};

type State = {
  error: Error | null;
};

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        this.props.fallback?.(this.state.error) ?? (
          <div className="error-boundary" role="alert">
            <h3>Đã có lỗi xảy ra</h3>
            <p>Vui lòng tải lại trang. Nếu lỗi vẫn còn, hãy báo cho quản trị viên.</p>
            <button type="button" onClick={() => this.setState({ error: null })}>
              Thử lại
            </button>
          </div>
        )
      );
    }
    return this.props.children;
  }
}
