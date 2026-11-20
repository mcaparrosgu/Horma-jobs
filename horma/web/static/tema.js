// Tema claro/oscuro (RF-6.1d). Se carga en <head>, sin defer, para aplicar el tema guardado antes de pintar.
// Si el navegador no deja guardar (modo privado, datos bloqueados), la página sigue el tema del sistema.
(function () {
  const CLAVE = "horma-tema";
  const raiz = document.documentElement;

  function leer() {
    try {
      const v = localStorage.getItem(CLAVE);
      return v === "dark" || v === "light" ? v : null;
    } catch (e) {
      return null;
    }
  }

  function guardar(valor) {
    try {
      localStorage.setItem(CLAVE, valor);
    } catch (e) {
      /* sin almacenamiento: el cambio vale solo para esta visita */
    }
  }

  function esOscuro() {
    const puesto = raiz.getAttribute("data-theme");
    if (puesto) return puesto === "dark";
    return !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
  }

  function pintarBotones() {
    for (const b of document.querySelectorAll("[data-tema-boton]")) b.setAttribute("aria-pressed", String(esOscuro()));
  }

  function alternarTema() {
    const nuevo = esOscuro() ? "light" : "dark";
    raiz.setAttribute("data-theme", nuevo);
    guardar(nuevo);
    pintarBotones();
  }

  // Une un botón al tema. El botón lleva siempre el mismo texto («Tema oscuro»); aria-pressed dice si está activo.
  function vincularTema(boton) {
    if (!boton || boton.hasAttribute("data-tema-boton")) return;
    boton.setAttribute("data-tema-boton", "");
    boton.addEventListener("click", alternarTema);
    boton.setAttribute("aria-pressed", String(esOscuro()));
  }

  const guardado = leer();
  if (guardado) raiz.setAttribute("data-theme", guardado);
  window.alternarTema = alternarTema;
  window.vincularTema = vincularTema;
  document.addEventListener("DOMContentLoaded", () => vincularTema(document.getElementById("tema")));
})();
