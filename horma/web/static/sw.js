// Service worker de Horma (RF-4.6): guarda solo archivos estáticos; nunca respuestas de la API.
const VERSION = "horma-v1";
const BASICOS = ["/static/offline.html", "/static/estilo.css", "/static/iconos/icono-192.png"];

self.addEventListener("install", (evento) => {
  evento.waitUntil(caches.open(VERSION).then((c) => c.addAll(BASICOS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(
    caches.keys()
      .then((claves) => Promise.all(claves.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (evento) => {
  const peticion = evento.request;
  if (peticion.method !== "GET") return;
  const url = new URL(peticion.url);
  if (url.origin !== self.location.origin) return;
  // La API, el login y las páginas con datos van siempre a la red y nunca se guardan.
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/auth/")) return;

  if (url.pathname.startsWith("/static/")) {
    // Primero la red (así un JS nuevo nunca convive con otro viejo); sin red, lo guardado.
    evento.respondWith(
      fetch(peticion)
        .then((respuesta) => {
          if (respuesta.ok) {
            const copia = respuesta.clone();
            caches.open(VERSION).then((c) => c.put(peticion, copia));
          }
          return respuesta;
        })
        .catch(() => caches.match(peticion))
    );
    return;
  }

  if (peticion.mode === "navigate") {
    // Las páginas no se guardan: sin red, solo la página «Sin conexión».
    evento.respondWith(fetch(peticion).catch(() => caches.match("/static/offline.html")));
  }
});
