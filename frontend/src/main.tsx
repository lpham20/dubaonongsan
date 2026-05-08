import React from "react";
import ReactDOM from "react-dom/client";
import { registerSW } from "virtual:pwa-register";
import { App } from "./App";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { AuthProvider } from "./contexts/AuthContext";
import "./styles/tokens.css";
import "./styles/fertilizer.css";
import "./styles/base.css";
import "./styles/legacy-surfaces.css";
import "./styles/design-system.css";
import "./styles/analytics.css";
import "./styles/route-polish.css";
import "./styles/home.css";
import "./styles/news.css";
import "./styles/guides.css";
import "./styles/forecast.css";
import "./styles/header.css";
import "./styles/production.css";
import "./styles/responsive.css";
import "./styles/finance-terminal.css";

if (import.meta.env.PROD) {
  registerSW({
    immediate: true,
    onNeedRefresh() {
      console.info("Có phiên bản mới, hãy tải lại trang để cập nhật.");
    },
    onOfflineReady() {
      console.info("Dự báo nông sản đã sẵn sàng dùng ở chế độ offline.");
    }
  });
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <AuthProvider>
        <App />
      </AuthProvider>
    </ErrorBoundary>
  </React.StrictMode>
);
