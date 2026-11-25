"""Consola `horma`: sin lógica propia y sin credenciales de la base de datos. Lo que hay que guardar
se pide a la API con una clave (RF-1.2)."""
import copy
import json
import sys
from pathlib import Path

import typer

from horma.agents.registry import AGENTES, APARCADOS
from horma.config import ajustes
from horma.flows.base import ErrorDePaso
from horma.flows.registry import APARCADOS as FLUJOS_APARCADOS
from horma.flows.registry import FLUJOS, IMPLEMENTACIONES, RESULTADO, crear_flujo
from horma.llm import SalidaInvalida
from horma.llm.simulado import ProveedorSimulado

app = typer.Typer(help="Consola de Horma: agentes, flujos, ingesta, fuentes y evals.",
                  no_args_is_help=True)
agente = typer.Typer(help="Ejecutar agentes uno a uno.", no_args_is_help=True)
flujo = typer.Typer(help="Ejecutar flujos, también paso a paso.", no_args_is_help=True)
evals = typer.Typer(help="Correr sets de evals.", no_args_is_help=True)
fuente = typer.Typer(help="Calificar fuentes de ofertas.", no_args_is_help=True)
envios = typer.Typer(help="Envío de candidaturas (solo mide, no envía).", no_args_is_help=True)


@app.callback()
def _utf8() -> None:
    """En Windows la consola usa cp1252 y falla con «→» o «·»: se fuerza UTF-8 en la salida."""
    for flujo_ in (sys.stdout, sys.stderr):
        if hasattr(flujo_, "reconfigure"):
            flujo_.reconfigure(encoding="utf-8", errors="replace")


app.add_typer(agente, name="agente")
app.add_typer(flujo, name="flujo")
app.add_typer(evals, name="eval")
app.add_typer(fuente, name="fuente")
app.add_typer(envios, name="envios")


def _sin_clave_de_anthropic() -> None:
    if not ajustes().anthropic_api_key:
        typer.echo("Falta ANTHROPIC_API_KEY en .env (o usa --simulado).", err=True)
        raise typer.Exit(2)


# --- agente ------------------------------------------------------------------------------------
@agente.command("listar")
def listar() -> None:
    """Lista los agentes con su modelo y sus esquemas."""
    for a in AGENTES.values():
        typer.echo(f"{a.nombre}  modelo={a.modelo}  entrada={a.entrada.__name__}  "
                   f"salida={a.salida.__name__}")
    if APARCADOS:
        typer.echo(f"Aparcados (no activos, código conservado): {', '.join(APARCADOS)}")


QUITADOS = {  # agentes retirados en el bloque H de la fase 3 (16-nov-2026)
    "juez-cv": "lo sustituye juez-candidatura, que juzga CV y carta de una vez.",
    "juez-carta": "lo sustituye juez-candidatura, que juzga CV y carta de una vez.",
    "selector-cv-base": "el CV base lo elige la herramienta elegir_cv_base, sin modelo.",
}


@agente.command("correr")
def correr(
    nombre: str,
    entrada: Path = typer.Option(..., help="Archivo de entrada (.md = texto; .json = esquema)."),
    salida: Path | None = typer.Option(None, help="Archivo donde guardar la salida."),
    simulado: bool = typer.Option(False, help="No llama al modelo: usa --respuesta."),
    respuesta: Path | None = typer.Option(None, help="JSON con la respuesta simulada."),
) -> None:
    """Ejecuta un agente con una entrada en archivo y valida su salida."""
    if nombre in QUITADOS:
        typer.echo(f"El agente {nombre} ya no existe: {QUITADOS[nombre]}", err=True)
        raise typer.Exit(2)
    if nombre in APARCADOS:
        typer.echo(f"El agente {nombre} está aparcado (RF-10.11d): código conservado, sin uso.", err=True)
        raise typer.Exit(2)
    if nombre not in AGENTES:
        typer.echo(f"Agente desconocido: {nombre}", err=True)
        raise typer.Exit(2)
    clase = AGENTES[nombre]
    texto = entrada.read_text(encoding="utf-8")
    if entrada.suffix == ".json":
        datos = clase.entrada.model_validate_json(texto)
    elif "texto" in clase.entrada.model_fields:
        datos = clase.entrada(texto=texto)
    else:
        typer.echo(f"{nombre} necesita una entrada .json ({clase.entrada.__name__}).", err=True)
        raise typer.Exit(2)
    proveedor = None
    if simulado:
        if respuesta is None:
            typer.echo("--simulado necesita --respuesta <archivo.json>", err=True)
            raise typer.Exit(2)
        proveedor = ProveedorSimulado([json.loads(respuesta.read_text(encoding="utf-8"))])
    try:
        resultado = clase.run(datos, proveedor=proveedor)
    except RuntimeError as e:  # p. ej. falta ANTHROPIC_API_KEY
        typer.echo(str(e), err=True)
        raise typer.Exit(2) from e
    except SalidaInvalida as e:
        typer.echo(f"El modelo no devolvió una salida válida: {e}", err=True)
        raise typer.Exit(1) from e
    salida_json = resultado.model_dump_json(indent=2)
    if salida:
        salida.write_text(salida_json, encoding="utf-8")
    typer.echo(salida_json)


# --- flujo -------------------------------------------------------------------------------------
@flujo.command("listar")
def flujo_listar() -> None:
    """Lista los flujos y sus pasos en orden."""
    for nombre, fabrica in FLUJOS.items():
        typer.echo(f"{nombre}: {' → '.join(fabrica(proveedor=ProveedorSimulado([])).pasos())}")


def _serializar(valor):
    """Los bytes (PDF) no caben en JSON: se dejan como su tamaño."""
    if isinstance(valor, bytes):
        return f"<{len(valor)} bytes>"
    raise TypeError(f"no se puede serializar {type(valor).__name__}")


def _resumen(valor) -> str:
    texto = json.dumps(valor, ensure_ascii=False, default=_serializar)
    return texto if len(texto) <= 240 else texto[:237] + "…"


def _estado_inicial(nombre: str, entrada: Path, usuaria: str | None) -> dict:
    """`.json` = el estado tal cual; `.md` = {texto}. `perfilar` también admite `.pdf` y `.docx`:
    el CV se convierte a texto con `convertir_cv` y entra como el único CV de la usuaria."""
    if nombre == "perfilar" and entrada.suffix != ".json":
        from horma.tools.convertir_cv import ArchivoNoValido, convertir_cv

        tipo = entrada.suffix.lstrip(".").lower()
        try:
            texto = convertir_cv(entrada.read_bytes(), tipo)
        except ArchivoNoValido as e:
            typer.echo(f"No se puede leer el CV: {e}", err=True)
            raise typer.Exit(2) from e
        return {"cvs": [{"cv_id": 1, "nombre": f"CV de {usuaria}" if usuaria else entrada.name,
                         "texto": texto}]}
    texto = entrada.read_text(encoding="utf-8")
    return json.loads(texto) if entrada.suffix == ".json" else {"texto": texto}


def _estado_candidatura(usuaria: str | None, oferta_id: str | None, ofertas: Path | None) -> dict:
    """Estado inicial de `candidatura` sin base de datos: usuaria de prueba + oferta del catálogo."""
    from horma.evals import cargar_usuaria

    if not usuaria or not oferta_id:
        typer.echo("`candidatura` necesita --entrada, o bien --usuaria y --oferta.", err=True)
        raise typer.Exit(2)
    carpeta = Path("evals") / "cv" / "usuarias" / usuaria
    if not (carpeta / "usuaria.json").exists():
        typer.echo(f"No existe la usuaria de prueba {carpeta}.", err=True)
        raise typer.Exit(2)
    if ofertas:
        candidatas = json.loads(ofertas.read_text(encoding="utf-8"))["ofertas"]
    else:
        from horma.ingesta import ErrorApi

        try:
            candidatas = _cliente_api().catalogo()["ofertas"]
        except ErrorApi as e:
            typer.echo(f"La API respondió con un error: {e}", err=True)
            raise typer.Exit(1) from e
    elegida = next((c for c in candidatas if str(c["oferta_id"]) == oferta_id), None)
    if elegida is None:
        typer.echo(f"La oferta {oferta_id} no está en el catálogo.", err=True)
        raise typer.Exit(2)
    return {**cargar_usuaria(carpeta), "oferta": elegida["oferta"]}


@flujo.command("correr")
def flujo_correr(
    nombre: str,
    entrada: Path | None = typer.Option(None, help="Estado inicial: .md = {texto}; .json = estado; "
                                                   "en `perfilar`, también el CV en .pdf o .docx. "
                                                   "En `candidatura` sobra con --usuaria y --oferta."),
    usuaria: str | None = typer.Option(None, help="`perfilar`: solo nombra el CV en la traza. "
                                                  "`candidatura`: usuaria de prueba de "
                                                  "evals/cv/usuarias/. No guarda nada."),
    oferta: str | None = typer.Option(None, help="`candidatura`: id de la oferta del catálogo."),
    ofertas: Path | None = typer.Option(None, help='`candidatura`: catálogo en JSON ({"ofertas": '
                                                   "[...]}) para no usar la API."),
    paso_a_paso: bool = typer.Option(False, "--paso-a-paso", help="Pausa tras cada paso."),
    traza: Path | None = typer.Option(None, help="Carpeta donde guardar cada paso como JSON."),
    aprobar: bool = typer.Option(False, "--aprobar", help="Flujos con pausa (`candidatura`): sigue con "
                                                          "`entregar` y, con --traza, guarda los dos PDF."),
    salida: Path | None = typer.Option(None, help="Archivo donde guardar el resultado."),
    simulado: bool = typer.Option(False, help="No llama al modelo ni a la red: usa --respuestas."),
    respuestas: Path | None = typer.Option(None, help="JSON con la lista de respuestas simuladas."),
) -> None:
    """Ejecuta un flujo mostrando la entrada y la salida de cada paso (RT-05)."""
    if nombre in FLUJOS_APARCADOS:
        typer.echo(f"El flujo {nombre} está aparcado (RF-10.11d): código conservado, sin uso.", err=True)
        raise typer.Exit(2)
    if nombre not in FLUJOS:
        typer.echo(f"Flujo desconocido: {nombre}", err=True)
        raise typer.Exit(2)
    if nombre == "candidatura" and entrada is None:
        estado = _estado_candidatura(usuaria, oferta, ofertas)
    elif entrada is None:
        typer.echo("Falta --entrada.", err=True)
        raise typer.Exit(2)
    else:
        estado = _estado_inicial(nombre, entrada, usuaria)
    deps: dict = {}
    if simulado:
        if respuestas is None:
            typer.echo("--simulado necesita --respuestas <archivo.json>", err=True)
            raise typer.Exit(2)
        deps["proveedor"] = ProveedorSimulado(json.loads(respuestas.read_text(encoding="utf-8")))
        if nombre == "procesar_oferta":
            deps["resolver"] = None  # sin red
    else:
        _sin_clave_de_anthropic()
    try:
        f = crear_flujo(nombre, **deps)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(2) from e
    if aprobar and not f.pausas:
        typer.echo(f"--aprobar solo vale en flujos con pausa; «{nombre}» no tiene ninguna.", err=True)
        raise typer.Exit(2)
    orden = f.pasos()
    if traza:
        traza.mkdir(parents=True, exist_ok=True)
    from horma.llm.metricas import capturar

    try:
        with capturar() as llamadas:
            estado = _correr_pasos(f, orden, estado, paso_a_paso, traza, aprobar)
    except ErrorDePaso as e:
        typer.echo(f"Falló el {e}", err=True)
        raise typer.Exit(1) from e
    typer.echo(f"{len(llamadas)} llamadas al modelo · {sum(ll.coste for ll in llamadas):.4f} USD", err=True)
    resultado = json.dumps(estado.get(RESULTADO[nombre]), ensure_ascii=False, indent=2)
    if salida:
        salida.write_text(resultado, encoding="utf-8")
    typer.echo(resultado)


def _correr_pasos(f, orden, estado, paso_a_paso, traza, aprobar=False):
    paso, n = f.inicio, 0
    while paso is not None:
        if paso in f.pausas and not aprobar:
            typer.echo(f"En pausa: falta la aprobación (antes de «{paso}»). Con --aprobar sigue.")
            break
        n += 1
        antes = copy.deepcopy(estado)
        estado = f.run_step(paso, estado)
        cambios = {k: v for k, v in estado.items() if k not in antes or antes[k] != v}
        typer.echo(f"[{orden.index(paso) + 1}/{len(orden)}] {paso}")
        if paso_a_paso:
            typer.echo(f"  entrada: {', '.join(antes) or '—'}")
            for k, v in cambios.items():
                typer.echo(f"  {k}: {_resumen(v)}")
        if traza:
            (traza / f"{n:02d}-{paso}.json").write_text(json.dumps(
                {"paso": paso, "entrada": antes, "salida": estado}, ensure_ascii=False,
                indent=2, default=_serializar), encoding="utf-8")
        paso = f.siguiente(paso, estado)
        if paso_a_paso and paso is not None:
            typer.prompt("  Enter para seguir", default="", show_default=False,
                         prompt_suffix="")
    if aprobar:
        _guardar_pdfs(estado, traza)
    return estado


def _guardar_pdfs(estado: dict, traza: Path | None) -> None:
    """Tras `entregar`: los dos PDF van a la carpeta de la traza (datos de prueba, no de usuarias)."""
    if not (estado.get("cv_pdf") and estado.get("carta_pdf")):
        return
    if traza is None:
        typer.echo("Aprobada, pero sin --traza no hay dónde guardar los PDF.", err=True)
        return
    (traza / "cv.pdf").write_bytes(estado["cv_pdf"])
    (traza / "carta.pdf").write_bytes(estado["carta_pdf"])
    typer.echo(f"PDF guardados en {traza} (cv.pdf y carta.pdf).")


# --- ingesta y fuentes (por la API: la consola no tiene credenciales de la BD) -----------------
def _cliente_api():
    from horma.ingesta import ClienteApi

    a = ajustes()
    try:
        return ClienteApi(a.horma_api_url, a.horma_clave_ingesta)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(2) from e


def _esperar(segundos: float) -> None:
    import time

    time.sleep(segundos)


@app.command("ingestar")
def ingestar(
    fuente_nombre: str | None = typer.Argument(None, metavar="FUENTE"),
    limite: int = typer.Option(20, min=1, max=500, help="Máximo de ofertas a entregar."),
    en_seco: bool = typer.Option(False, "--en-seco", help="Lee la fuente de config/endpoints.json "
                                 "y enseña las ofertas normalizadas sin entregarlas."),
    escuchar: bool = typer.Option(False, "--escuchar", help="Atiende las ejecuciones del dashboard."),
) -> None:
    """Llama al endpoint de una fuente y entrega sus ofertas por POST /ofertas (RF-1.2)."""
    import httpx

    from horma import ingesta

    if escuchar:
        ingesta.escuchar(_cliente_api(), httpx.Client())
        return
    if not fuente_nombre:
        typer.echo("Indica la fuente (o usa --escuchar).", err=True)
        raise typer.Exit(2)
    if en_seco:
        from horma.tools.semilla import fuentes_semilla

        f = next((x for x in fuentes_semilla() if x.nombre == fuente_nombre), None)
        if not f:
            typer.echo(f"{fuente_nombre} no está en config/endpoints.json", err=True)
            raise typer.Exit(2)
        for o in ingesta.leer_fuente(f, httpx.Client(), limite):
            typer.echo(f"--- {o.id_externo}\n{o.texto[:600]}\n")
        return
    try:
        r = ingesta.ingestar_fuente(_cliente_api(), fuente_nombre, limite, httpx.Client())
    except (ingesta.ErrorApi, httpx.HTTPError) as e:
        typer.echo(f"No se pudo ingestar: {e}", err=True)
        raise typer.Exit(1) from e
    typer.echo(f"Ejecución {r['id']} · {r['estado']} · recibidas {r['recibidas']} · nuevas "
               f"{r['nuevas']} · repetidas {r['repetidas']} · errores {r['errores']}")
    if r["motivo_error"]:
        typer.echo(r["motivo_error"], err=True)
        raise typer.Exit(1)


def _mostrar_calificacion(c: dict) -> None:
    typer.echo(f"{c['url']}: {'APTA' if c['apta'] else 'NO APTA'}")
    for m in c.get("motivos") or []:
        typer.echo(f"  - {m}")
    if c.get("instrucciones_embebidas"):
        typer.echo(f"  Instrucciones detectadas y no ejecutadas: {len(c['instrucciones_embebidas'])}")


@fuente.command("calificar")
def calificar(
    url: str,
    condiciones: str | None = typer.Option(None, help="URL de las condiciones de uso, si no se "
                                                      "encuentran solas."),
    local: bool = typer.Option(False, "--local", help="Corre el flujo aquí y solo lo enseña: no "
                                                      "guarda la calificación."),
    espera_max: int = typer.Option(180, help="Segundos máximos esperando al worker."),
) -> None:
    """Califica una fuente (condiciones de uso y robots.txt) con auditor-fuentes (RF-1.7)."""
    if not url.startswith("https://"):
        typer.echo("La URL tiene que empezar por https://", err=True)
        raise typer.Exit(2)
    if local:
        estado = {"url": url, **({"condiciones_url": condiciones} if condiciones else {})}
        try:
            c = FLUJOS["calificar_fuente"]().run(estado)["calificacion"]
        except ErrorDePaso as e:
            typer.echo(f"Falló el {e}", err=True)
            raise typer.Exit(1) from e
        _mostrar_calificacion(c)
        return
    if condiciones:
        typer.echo("--condiciones solo funciona con --local por ahora.", err=True)
        raise typer.Exit(2)
    from horma.ingesta import ErrorApi

    api = _cliente_api()
    try:
        pedida = api.pedir_calificacion(url)
        for _ in range(espera_max):
            c = api.calificacion(pedida["id"])
            if c["estado"] != "pendiente":
                break
            _esperar(1)
    except ErrorApi as e:
        typer.echo(f"La API respondió con un error: {e}", err=True)
        raise typer.Exit(1) from e
    if c["estado"] == "pendiente":
        typer.echo(f"El worker no ha terminado todavía (calificación {pedida['id']}).", err=True)
        raise typer.Exit(1)
    if c["estado"] == "error":
        typer.echo(f"La calificación falló: {c['motivo_error']}", err=True)
        raise typer.Exit(1)
    _mostrar_calificacion(c)


@fuente.command("greenhouse")
def greenhouse_anadir(
    tokens: list[str] = typer.Argument(..., help="«Board tokens» (boards.greenhouse.io/<token>)."),
    pausa: float = typer.Option(1.0, help="Segundos entre peticiones."),
) -> None:
    """Comprueba cada token y añade las empresas que responden a config/greenhouse.json (T32)."""
    import httpx

    from horma.tools import greenhouse

    validas, rechazadas = [], []
    with httpx.Client() as http:
        for i, token in enumerate(dict.fromkeys(t.strip().lower() for t in tokens)):
            if i:
                _esperar(pausa)
            nombre = greenhouse.validar_token(token, http)
            if nombre:
                validas.append({"token": token, "nombre": nombre})
            else:
                rechazadas.append(token)
    nuevas = greenhouse.anadir(greenhouse.RUTA, validas)
    typer.echo(f"{len(validas)} responden ({nuevas} nuevas en config/greenhouse.json); "
               f"sin respuesta: {', '.join(rechazadas) or 'ninguna'}.")
    typer.echo("Quedan inactivas: se siembran con una migración y se activan con una calificación apta.")


# --- eval --------------------------------------------------------------------------------------
def _mostrar_medicion(m: dict) -> None:
    typer.echo(f"{'Portal':<24}{'Ofertas':>8}  Exige cuenta")
    for f in m["filas"]:
        cuenta = ("Sí" if f["exige_cuenta"] else "No") if f["automatico"] else "—"
        typer.echo(f"{f['portal']:<24}{f['ofertas']:>8}  {cuenta}")
    typer.echo(f"{m['total']} ofertas: {m['automaticas']} con canal automático "
               f"({m['exigen_cuenta']} exigen cuenta) y {m['no_automaticas']} no automáticas.")


@envios.command("medir")
def envios_medir() -> None:
    """Cuenta, sin enviar nada, a qué portal lleva cada oferta del catálogo (RF-11.1). Por la API."""
    import httpx

    from horma.ingesta import ErrorApi

    try:
        _mostrar_medicion(_cliente_api().medicion_destinos())
    except (ErrorApi, httpx.HTTPError) as e:
        typer.echo(f"No se pudo medir: {e}", err=True)
        raise typer.Exit(1) from e


@evals.command("correr")
def correr_eval(
    conjunto: str = typer.Argument(..., metavar="SET"),
    solo: str | None = typer.Option(None, help="Correr un solo caso."),
    simulado: bool = typer.Option(False, help="Cada caso responde con su esperado: solo prueba el "
                                              "harness, NO mide el modelo."),
    tope_coste: float = typer.Option(1.0, help="Tope de coste por ejecución, en USD: al superarlo "
                                               "el eval se detiene (RF-2.17)."),
    raiz: Path = typer.Option(Path("evals"), help="Carpeta de evals."),
    flujo_impl: str | None = typer.Option(None, "--flujo", help="Implementación del flujo `candidatura` "
                                          "(plain o langgraph); por defecto, HORMA_FLOW_IMPL."),
) -> None:
    """Corre un set de evals y deja la ejecución en evals/resultados/."""
    from horma.evals import SETS, correr_set

    if flujo_impl is not None and flujo_impl not in IMPLEMENTACIONES:
        typer.echo(f"--flujo desconocido: «{flujo_impl}». Valores válidos: {', '.join(IMPLEMENTACIONES)}.",
                   err=True)
        raise typer.Exit(2)

    if conjunto not in SETS:
        typer.echo(f"Set desconocido: {conjunto}", err=True)
        raise typer.Exit(2)
    if not simulado:
        _sin_clave_de_anthropic()
    res = correr_set(conjunto, raiz=raiz, solo=solo, simulado=simulado,
                     tope_coste=tope_coste, flujo=flujo_impl)
    for campo, valor in res["campos"].items():
        typer.echo(f"{campo:<30}{valor:.2f}")
    typer.echo(f"{'adversarias':<30}{res['adversarias']:.2f}")
    typer.echo(f"\n{res['casos_ejecutados']} de {res['casos']} casos · coste {res['coste']:.4f} USD "
               f"(tope {tope_coste:g}) · {'APROBADO' if res['aprobado'] else 'NO APROBADO'}")
    if res["detenido_por_coste"]:
        typer.echo("El eval se detuvo al superar el tope de coste: el resultado no es completo.")
    raise typer.Exit(0 if res["aprobado"] else 1)


def _slug(texto: str) -> str:
    import re
    import unicodedata

    plano = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", plano).strip("-")[:40] or "oferta"


@evals.command("importar-correccion")
def importar_correccion(
    archivo: Path = typer.Option(..., help="Caso exportado desde la pantalla (GET /api/matches/…/exportar)."),
    raiz: Path = typer.Option(Path("evals"), help="Carpeta de evals."),
) -> None:
    """Enseña una corrección de la usuaria y, solo si lo confirmas, la copia a evals/recomendacion/."""
    caso = json.loads(archivo.read_text(encoding="utf-8"))
    entrada, esperado = caso.get("entrada"), caso.get("esperado")
    if (not isinstance(entrada, dict) or not isinstance(esperado, dict)
            or not {"perfil", "preferencias", "oferta"} <= entrada.keys()
            or not isinstance(entrada["oferta"], dict) or "nota" not in esperado):
        typer.echo("El archivo no es un caso exportado (faltan «entrada» o «esperado»).", err=True)
        raise typer.Exit(2)
    casos = raiz / "recomendacion" / "casos"
    for previo in casos.glob("*/entrada.json"):
        otro = previo.parent / "esperado.json"
        if (otro.exists() and json.loads(previo.read_text(encoding="utf-8")) == entrada
                and json.loads(otro.read_text(encoding="utf-8")) == esperado):
            typer.echo(f"Este caso ya está importado ({previo.parent.name}).", err=True)
            raise typer.Exit(1)
    modelo = caso.get("modelo") or {}
    titulo = entrada["oferta"].get("titulo") or ""
    typer.echo(f"Oferta: {titulo or '(sin título)'}")
    typer.echo(f"Nota del modelo: {modelo.get('nota', '—')} · nota corregida: {esperado['nota']}")
    typer.echo(f"Motivo de la usuaria: {esperado.get('motivo', '—')}")
    respuesta = typer.prompt(f"¿Copiarlo a {casos}? [s/N]", default="n", show_default=False)
    if respuesta.strip().lower() not in {"s", "si", "sí", "y", "yes"}:
        typer.echo("No se ha copiado nada.")
        raise typer.Exit(1)
    numeros = [int(p.name[:2]) for p in casos.glob("*") if p.name[:2].isdigit()]
    destino = casos / f"{max(numeros, default=0) + 1:02d}-correccion-{_slug(titulo)}"
    destino.mkdir(parents=True)
    for nombre, datos in (("entrada.json", entrada), ("esperado.json", esperado)):
        (destino / nombre).write_text(json.dumps(datos, ensure_ascii=False, indent=2),
                                      encoding="utf-8")
    typer.echo(f"Copiado en {destino}. Revisa el cambio y haz commit tú.")


# --- recomendar (en local, sin guardar nada) ---------------------------------------------------
def _rango(texto: str) -> tuple[int, int]:
    try:
        minimo, maximo = (int(x) for x in texto.split("-"))
    except ValueError as e:
        raise typer.BadParameter("usa el formato 40-100") from e
    if not 0 <= minimo <= maximo <= 100:
        raise typer.BadParameter("va de 0 a 100 y el mínimo no puede superar al máximo")
    return minimo, maximo


@app.command("recomendar")
def recomendar_cmd(
    usuaria: str = typer.Argument(..., help="Nombre del perfil de prueba."),
    rango: str = typer.Option("40-100", help="Rango de compatibilidad, p. ej. 40-100 (RF-2.13)."),
    perfil: Path | None = typer.Option(None, help="Perfil en JSON. Por defecto "
                                       "evals/perfil/perfiles/<usuaria>.json."),
    ofertas: Path | None = typer.Option(None, help='Catálogo en JSON ({"ofertas": [...]}) para '
                                        "no usar la API."),
    simulado: bool = typer.Option(False, help="No llama al modelo: usa --respuestas."),
    respuestas: Path | None = typer.Option(None, help="JSON con la lista de respuestas simuladas."),
) -> None:
    """Puntúa un catálogo de ofertas para un perfil de prueba y enseña la lista. No guarda nada."""
    from horma.flows import recomendar as flujo_recomendar
    from horma.schemas.perfil import Perfil
    from horma.schemas.preferencias import Preferencias

    minimo, maximo = _rango(rango)
    ruta = perfil or Path("evals") / "perfil" / "perfiles" / f"{usuaria}.json"
    if not ruta.exists():
        typer.echo(f"No existe el perfil {ruta}.", err=True)
        raise typer.Exit(2)
    datos_perfil = Perfil.model_validate_json(ruta.read_text(encoding="utf-8"))
    if ofertas:
        candidatas = json.loads(ofertas.read_text(encoding="utf-8"))["ofertas"]
    else:
        from horma.ingesta import ErrorApi

        try:
            candidatas = _cliente_api().catalogo()["ofertas"]
        except ErrorApi as e:
            typer.echo(f"La API respondió con un error: {e}", err=True)
            raise typer.Exit(1) from e
    proveedor = None
    if simulado:
        if respuestas is None:
            typer.echo("--simulado necesita --respuestas <archivo.json>", err=True)
            raise typer.Exit(2)
        proveedor = ProveedorSimulado(json.loads(respuestas.read_text(encoding="utf-8")))
    else:
        _sin_clave_de_anthropic()
    prefs = Preferencias(rango_min=minimo, rango_max=maximo)
    try:
        estado = flujo_recomendar.crear(proveedor=proveedor).run({
            "perfil": datos_perfil.model_dump(mode="json"),
            "preferencias": prefs.model_dump(mode="json"), "candidatas": candidatas})
    except ErrorDePaso as e:
        typer.echo(f"Falló el {e}", err=True)
        raise typer.Exit(1) from e
    titulos = {c["oferta_id"]: c["oferta"].get("titulo") or "(sin título)" for c in candidatas}
    en_rango = sorted((m for m in estado["recomendaciones"] if minimo <= m["nota"] <= maximo),
                      key=lambda m: -m["nota"])
    for m in en_rango:
        typer.echo(f"{m['nota']:>3}  {titulos.get(m['oferta_id'], m['oferta_id'])}  "
                   f"· condiciones {m['condiciones']}")
        if m["retirada"]:
            typer.echo("     (explicación retirada: mencionaba un rasgo personal)")
        elif m["explicacion"]:
            typer.echo(f"     {m['explicacion']}")
    typer.echo(f"\n{len(en_rango)} de {len(estado['recomendaciones'])} ofertas en el rango "
               f"{minimo}-{maximo} · {estado['quedan_sin_puntuar']} sin puntuar")
