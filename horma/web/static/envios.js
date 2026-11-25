// Medición de destinos. Todo lo que viene de la API se pinta con textContent: nunca como HTML.
const entero = (n) => Number(n).toLocaleString("es-ES");

function pintar(r) {
  const t = $("tabla");
  t.replaceChildren();
  const cabecera = nodo("tr");
  ["Portal", "Ofertas", "Exige cuenta"].forEach((c) => cabecera.append(nodo("th", c)));
  const encabezado = nodo("thead");
  encabezado.append(cabecera);
  const cuerpo = nodo("tbody");
  r.filas.forEach((f) => {
    const tr = nodo("tr");
    tr.append(nodo("td", f.portal), nodo("td", entero(f.ofertas)),
      nodo("td", f.automatico ? (f.exige_cuenta ? "Sí" : "No") : "—"));
    cuerpo.append(tr);
  });
  t.append(encabezado, cuerpo);
  $("resumen").textContent = `${entero(r.total)} ofertas: ${entero(r.automaticas)} con canal automático ` +
    `(${entero(r.exigen_cuenta)} exigen cuenta) y ${entero(r.no_automaticas)} no automáticas.`;
  const motivos = $("motivos");
  motivos.replaceChildren();
  (r.motivos || []).forEach((x) => motivos.append(nodo("li", `${x.motivo} ${entero(x.ofertas)}`)));
  $("motivos-bloque").hidden = !(r.motivos || []).length;
  $("resultado").hidden = false;
}

async function medir() {
  const boton = $("medir");
  boton.disabled = true;
  $("aviso").className = "";
  $("aviso").textContent = "Midiendo… puede tardar un minuto.";
  try {
    const r = await fetch("/api/admin/envios/medicion");
    if (!r.ok) {
      $("aviso").className = "error";
      $("aviso").textContent = r.status === 403 ? "Solo para administradoras." : `Error ${r.status}`;
      return;
    }
    $("aviso").textContent = "";
    pintar(await r.json());
  } catch {
    $("aviso").className = "error";
    $("aviso").textContent = "No se pudo medir. Prueba otra vez.";
  } finally {
    boton.disabled = false;
  }
}

(async () => {
  if (!(await arrancarAdmin())) return;
  $("medir").addEventListener("click", medir);
})();
