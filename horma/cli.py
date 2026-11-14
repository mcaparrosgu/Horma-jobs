"""Consola `horma`: sin lógica propia y sin credenciales de la base de datos. Lo que hay que guardar
se pide a la API con una clave (RF-1.2)."""
import copy
import json
from pathlib import Path

import typer

from horma.agents.registry import AGENTES
from horma.config import ajustes
from horma.flows.base import ErrorDePaso
from horma.flows.registry import FLUJOS, RESULTADO
from horma.llm import SalidaInvalida
from horma.llm.simulado import ProveedorSimulado

app = typer.Typer(help="Consola de Horma: agentes, flujos, ingesta, fuentes y evals.",
                  no_args_is_help=True)
agente = typer.Typer(help="Ejecutar agentes uno a uno.", no_args_is_help=True)
flujo = typer.Typer(help="Ejecutar flujos, también paso a paso.", no_args_is_help=True)
evals = typer.Typer(help="Correr sets de evals.", no_args_is_help=True)
fuente = typer.Typer(help="Calificar fuentes de ofertas.", no_args_is_help=True)
app.add_typer(agente, name="agente")
app.add_typer(flujo, name="flujo")
app.add_typer(evals, name="eval")
app.add_typer(fuente, name="fuente")


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


@agente.command("correr")
def correr(
    nombre: str,
    entrada: Path = typer.Option(..., help="Archivo de entrada (.md = texto; .json = esquema)."),
    salida: Path | None = typer.Option(None, help="Archivo donde guardar la salida."),
    simulado: bool = typer.Option(False, help="No llama al modelo: usa --respuesta."),
    respuesta: Path | None = typer.Option(None, help="JSON con la respuesta simulada."),
) -> None:
    """Ejecuta un agente con una entrada en archivo y valida su salida."""
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


def _resumen(valor) -> str:
    texto = json.dumps(valor, ensure_ascii=False)
    return texto if len(texto) <= 240 else texto[:237] + "…"


@flujo.command("correr")
def flujo_correr(
    nombre: str,
    entrada: Path = typer.Option(..., help="Estado inicial: .md = {texto}; .json = estado."),
    paso_a_paso: bool = typer.Option(False, "--paso-a-paso", help="Pausa tras cada paso."),
    traza: Path | None = typer.Option(None, help="Carpeta donde guardar cada paso como JSON."),
    salida: Path | None = typer.Option(None, help="Archivo donde guardar el resultado."),
    simulado: bool = typer.Option(False, help="No llama al modelo ni a la red: usa --respuestas."),
    respuestas: Path | None = typer.Option(None, help="JSON con la lista de respuestas simuladas."),
) -> None:
    """Ejecuta un flujo mostrando la entrada y la salida de cada paso (RT-05)."""
    if nombre not in FLUJOS:
        typer.echo(f"Flujo desconocido: {nombre}", err=True)
        raise typer.Exit(2)
    texto = entrada.read_text(encoding="utf-8")
    estado = json.loads(texto) if entrada.suffix == ".json" else {"texto": texto}
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
    f = FLUJOS[nombre](**deps)
    orden = f.pasos()
    if traza:
        traza.mkdir(parents=True, exist_ok=True)
    paso, n = f.inicio, 0
    try:
        while paso is not None:
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
                    indent=2), encoding="utf-8")
            paso = f.siguiente(paso, estado)
            if paso_a_paso and paso is not None:
                typer.prompt("  Enter para seguir", default="", show_default=False,
                             prompt_suffix="")
    except ErrorDePaso as e:
        typer.echo(f"Falló el {e}", err=True)
        raise typer.Exit(1) from e
    resultado = json.dumps(estado.get(RESULTADO[nombre]), ensure_ascii=False, indent=2)
    if salida:
        salida.write_text(resultado, encoding="utf-8")
    typer.echo(resultado)


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


# --- eval --------------------------------------------------------------------------------------
@evals.command("correr")
def correr_eval(
    conjunto: str = typer.Argument(..., metavar="SET"),
    solo: str | None = typer.Option(None, help="Correr un solo caso."),
    simulado: bool = typer.Option(False, help="Cada caso responde con su esperado: solo prueba el "
                                              "harness, NO mide el modelo."),
    umbral: float = typer.Option(0.9, help="Precisión mínima por campo."),
    tope_coste: float = typer.Option(1.0, help="Tope de coste por ejecución, en USD: al superarlo "
                                               "el eval se detiene (RF-2.17)."),
    raiz: Path = typer.Option(Path("evals"), help="Carpeta de evals."),
) -> None:
    """Corre un set de evals y deja la ejecución en evals/resultados/."""
    from horma.evals import SETS, correr_set

    if conjunto not in SETS:
        typer.echo(f"Set desconocido: {conjunto}", err=True)
        raise typer.Exit(2)
    if not simulado:
        _sin_clave_de_anthropic()
    res = correr_set(conjunto, raiz=raiz, umbral=umbral, solo=solo, simulado=simulado,
                     tope_coste=tope_coste)
    for campo, valor in res["campos"].items():
        typer.echo(f"{campo:<30}{valor:.2f}")
    typer.echo(f"{'adversarias':<30}{res['adversarias']:.2f}")
    typer.echo(f"\n{res['casos_ejecutados']} de {res['casos']} casos · coste {res['coste']:.4f} USD "
               f"(tope {tope_coste:g}) · {'APROBADO' if res['aprobado'] else 'NO APROBADO'}")
    if res["detenido_por_coste"]:
        typer.echo("El eval se detuvo al superar el tope de coste: el resultado no es completo.")
    raise typer.Exit(0 if res["aprobado"] else 1)
