// Barra de rango de la guía (RF-11.27): dos tiradores sobre una pista, con sus dos números a la vista.
// El mínimo nunca pasa del máximo: el tirador que se mueve se detiene en el otro.
function acotarRango(min, max, tirador) {
  const entero = (v, defecto) => {
    const x = Number(v);
    return Number.isFinite(x) ? Math.max(0, Math.min(100, Math.round(x))) : defecto;
  };
  let a = entero(min, 0);
  let b = entero(max, 100);
  if (a > b) {
    if (tirador === "min") a = b;
    else b = a;
  }
  return { min: a, max: b };
}

// Pinta los números y el tramo, y deja encima el tirador que se puede mover cuando coinciden
// (en el extremo derecho, el mínimo; en el resto, el máximo). Devuelve `pintar` para refrescar desde fuera.
function montarRango(caja, minEl, maxEl) {
  const tramo = caja.querySelector(".rango-tramo");
  const nMin = caja.querySelector("[data-rango='min']");
  const nMax = caja.querySelector("[data-rango='max']");
  function pintar(tirador) {
    const r = acotarRango(minEl.value, maxEl.value, tirador);
    minEl.value = r.min;
    maxEl.value = r.max;
    nMin.textContent = String(r.min);
    nMax.textContent = String(r.max);
    tramo.style.left = `${r.min}%`;       // por CSSOM: la CSP no permite style= en el HTML
    tramo.style.right = `${100 - r.max}%`;
    minEl.style.zIndex = r.min >= 50 ? "2" : "1";
    maxEl.style.zIndex = r.min >= 50 ? "1" : "2";
  }
  minEl.addEventListener("input", () => pintar("min"));
  maxEl.addEventListener("input", () => pintar("max"));
  pintar();
  return pintar;
}
