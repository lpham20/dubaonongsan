import React from "react";
import ReactDOM from "react-dom/client";
import * as Sentry from "@sentry/react";
import { registerSW } from "virtual:pwa-register";
import { App } from "./App";
import { ErrorBoundary, isRecoverableChunkError, reloadOnceForNewBundle } from "./components/ErrorBoundary";
import { AuthProvider } from "./contexts/AuthContext";
import { trackEvent } from "./lib/analytics";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/finance-terminal.css";
import "./styles/legacy-surfaces.css";
import "./styles/design-system.css";
import "./styles/navigation-hierarchy.css";
import "./styles/editorial.css";
import "./styles/site-header.css";
import "./styles/news.css";
import "./styles/tools-redesign.css";
import "./styles/fertilizer.css";
import "./styles/forecast.css";
import "./styles/production.css";
import "./styles/input-prices.css";
import "./styles/advisory.css";
import "./styles/analytics.css";
import "./styles/route-polish.css";
import "./styles/responsive.css";
import "./styles/tablet-ipad.css";
import "./styles/mobile-bloomberg.css";
import "./styles/live-ticker.css";
import "./styles/cookie-consent.css";
import "./styles/title-fixes.css";
import "./styles/header-panel-fixes.css";

const SERVICE_WORKER_UPDATE_INTERVAL_MS = 60 * 60 * 1000;
const sentryDsn = import.meta.env.VITE_SENTRY_DSN;

function swallowServiceWorkerError(error: unknown) {
  const message = error instanceof Error ? error.message : String(error ?? "");
  if (import.meta.env.DEV && message) {
    console.warn("Service worker update skipped:", message);
  }
}

async function unregisterUnavailableServiceWorker() {
  if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;
  const registrations = await navigator.serviceWorker.getRegistrations();
  await Promise.all(registrations.map((registration) => registration.unregister()));
}

async function canRegisterServiceWorker() {
  if (typeof window === "undefined" || !("serviceWorker" in navigator)) return false;
  try {
    const response = await fetch("/sw.js", { cache: "no-store" });
    if (!response.ok) {
      await unregisterUnavailableServiceWorker().catch(swallowServiceWorkerError);
      return false;
    }
    return true;
  } catch (error) {
    await unregisterUnavailableServiceWorker().catch(swallowServiceWorkerError);
    swallowServiceWorkerError(error);
    return false;
  }
}

function updateRegistrationSafely(registration?: ServiceWorkerRegistration) {
  if (!registration) return;
  void registration.update().catch(swallowServiceWorkerError);
}

if (sentryDsn) {
  Sentry.init({
    dsn: sentryDsn,
    environment: import.meta.env.MODE || "production",
    release: import.meta.env.VITE_MARKETAI_RELEASE || "unknown",
    tracesSampleRate: 0.1,
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: 1.0,
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration({
        maskAllText: true,
        blockAllMedia: true
      })
    ],
    beforeSend(event, hint) {
      const error = hint.originalException;
      const message = error instanceof Error ? error.message : String(error ?? "");
      if (/AbortError|Network request failed|ChunkLoadError|Loading chunk|Failed to fetch dynamically imported module/i.test(message)) {
        return null;
      }
      trackEvent("exception", {
        description: "frontend_error",
        fatal: event.level === "fatal"
      });
      return event;
    }
  });
}

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
  void canRegisterServiceWorker().then((available) => {
    if (!available) return;
    let updateServiceWorker: ((reloadPage?: boolean) => Promise<void>) | undefined;
    updateServiceWorker = registerSW({
      immediate: true,
      onNeedRefresh() {
        void updateServiceWorker?.(true).catch(swallowServiceWorkerError);
      },
      onRegisteredSW(_swUrl, registration) {
        updateRegistrationSafely(registration);
        window.setInterval(() => {
          updateRegistrationSafely(registration);
        }, SERVICE_WORKER_UPDATE_INTERVAL_MS);
      },
      onOfflineReady() {
      }
    });
  }).catch(swallowServiceWorkerError);
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
