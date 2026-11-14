// Pantalla de preferencias: casillas con contador, sueldo mínimo y ordenación (RF-2.8, RF-2.8b).
let guardadas = null;

function pintar(opciones) {
  const cont = $("grupos");
  cont.replaceChildren(...GRUPOS.map(([clave, titulo]) =>
    grupoCasillas(clave, titulo, opciones.grupos[clave] || [], guardadas[clave] || [],
                  { origen: (guardadas.origen || {})[clave] })));
  $("solo-remoto").checked = guardadas.solo_remoto;
  $("solo-salario").checked = guardadas.solo_salario;
  $("sueldo-minimo").value = guardadas.sueldo_minimo === null ? "" : guardadas.sueldo_minimo;
  $("orden").value = guardadas.orden;
}

$("formulario").addEventListener("submit", async (e) => {
  e.preventDefault();
  const nuevas = { ...guardadas };
  for (const [clave] of GRUPOS) nuevas[clave] = marcadas(document.querySelector(`[data-grupo="${clave}"]`));
  nuevas.solo_remoto = $("solo-remoto").checked;
  nuevas.solo_salario = $("solo-salario").checked;
  const sueldo = $("sueldo-minimo").value.trim();
  nuevas.sueldo_minimo = sueldo === "" ? null : Number(sueldo);
  nuevas.orden = $("orden").value;
  const boton = e.target.querySelector("button[type=submit]");
  boton.disabled = true;
  const r = await api("/api/preferencias", { metodo: "PUT", cuerpo: nuevas });
  boton.disabled = false;
  if (!r.ok) return avisar(r.estado === 422 ? "Revisa el sueldo mínimo: debe ser un número positivo." : r.motivo, true);
  guardadas = r.datos;
  avisar("Preferencias guardadas.");
});

(async () => {
  if (!(await arrancar("/preferencias"))) return;
  const [p, o] = await Promise.all([api("/api/preferencias"), api("/api/preferencias/opciones")]);
  if (!p.ok || !o.ok) return avisar((p.motivo || o.motivo), true);
  guardadas = p.datos;
  pintar(o.datos);
})();
