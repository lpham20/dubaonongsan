(function seoFallback() {
  function rootReady() {
    var root = document.getElementById("root");
    return !!(root && root.children.length);
  }

  function removeSeo() {
    var seo = document.getElementById("seo-prerender");
    if (seo) seo.remove();
  }

  function revealSeo() {
    if (rootReady()) {
      removeSeo();
      return;
    }
    var seo = document.getElementById("seo-prerender");
    if (!seo) return;
    seo.removeAttribute("hidden");
    seo.removeAttribute("aria-hidden");
    seo.style.cssText = "max-width:760px;margin:24px auto;padding:0 16px;font-family:system-ui,sans-serif;line-height:1.6;color:#1a1a1a";
  }

  var guard = window.setInterval(function checkRoot() {
    if (!rootReady()) return;
    window.clearInterval(guard);
    removeSeo();
  }, 250);

  window.setTimeout(function onTimeout() {
    window.clearInterval(guard);
    revealSeo();
  }, 5000);
})();
