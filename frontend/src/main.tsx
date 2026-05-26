import React from "react";
import ReactDOM from "react-dom/client";
import { registerSW } from "virtual:pwa-register";
import { App } from "./App";
import { ErrorBoundary, isRecoverableChunkError, reloadOnceForNewBundle } from "./components/ErrorBoundary";
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
import "./styles/mobile-bloomberg.css";
import "./styles/tablet-ipad.css";
import "./styles/input-prices.css";
import "./styles/advisory.css";
import "./styles/navigation-hierarchy.css";
import "./styles/live-ticker.css";

const SERVICE_WORKER_UPDATE_INTERVAL_MS = 60 * 60 * 1000;

if (typeof window !== "undefined") {
  window.addEventListener("error", (event) => {
    if (isRecoverableChunkError(event.error ?? event.message)) {
      reloadOnceForNewBundle();
    }
  });

  window.addEventListener("unhandledrejection", (event) => {
    if (isRecoverableChunkError(event.reason)) {
      reloadOnceForNewBundle();
    }
  });
}

if (import.meta.env.PROD) {
  let updateServiceWorker: ((reloadPage?: boolean) => Promise<void>) | undefined;
  updateServiceWorker = registerSW({
    immediate: true,
    onNeedRefresh() {
      void updateServiceWorker?.(true);
    },
    onRegisteredSW(_swUrl, registration) {
      void registration?.update();
      window.setInterval(() => {
        void registration?.update();
      }, SERVICE_WORKER_UPDATE_INTERVAL_MS);
    },
    onOfflineReady() {
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
