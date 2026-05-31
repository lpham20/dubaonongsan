window.dataLayer = window.dataLayer || [];
window.gtag = window.gtag || function gtag() {
  window.dataLayer.push(arguments);
};

window.DUBAONONGSAN_LOAD_ANALYTICS = function loadAnalytics() {
  var id = window.DUBAONONGSAN_GA_ID;
  if (!id || typeof id !== "string" || !id.startsWith("G-") || window.DUBAONONGSAN_GA_LOADED) return;
  window.DUBAONONGSAN_GA_LOADED = true;
  var script = document.createElement("script");
  script.async = true;
  script.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(id);
  document.head.appendChild(script);
  window.gtag("js", new Date());
  window.gtag("config", id, { send_page_view: false });
};

(function loadAnalyticsAfterStoredConsent() {
  try {
    var consent = JSON.parse(window.localStorage.getItem("marketai.consent.v1") || "{}");
    if (consent.decided !== true || consent.analytics !== true) return;
    window.gtag("consent", "update", {
      analytics_storage: "granted",
      ad_storage: "denied",
      ad_user_data: "denied",
      ad_personalization: "denied"
    });
    window.DUBAONONGSAN_LOAD_ANALYTICS();
  } catch {
    // Invalid or unavailable storage keeps analytics disabled.
  }
})();
