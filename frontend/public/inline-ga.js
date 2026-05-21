window.dataLayer = window.dataLayer || [];
window.gtag = window.gtag || function gtag() {
  window.dataLayer.push(arguments);
};

(function loadAnalytics() {
  var id = window.DUBAONONGSAN_GA_ID;
  if (!id) return;
  var script = document.createElement("script");
  script.async = true;
  script.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(id);
  document.head.appendChild(script);
  window.gtag("js", new Date());
  window.gtag("config", id);
})();
