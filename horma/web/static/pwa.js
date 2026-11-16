// Registra el service worker (RF-4.6). Si el navegador no lo admite, la web funciona igual.
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  });
}
