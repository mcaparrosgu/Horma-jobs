import json
from pathlib import Path

import typer

from horma.agents.registry import AGENTES
from horma.llm import SalidaInvalida
from horma.llm.simulado import ProveedorSimulado

app = typer.Typer(help="Consola de Horma: probar agentes y evals.", no_args_is_help=True)
agente = typer.Typer(help="Ejecutar agentes uno a uno.", no_args_is_help=True)
evals = typer.Typer(help="Correr sets de evals.", no_args_is_help=True)
app.add_typer(agente, name="agente")
app.add_typer(evals, name="eval")


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
    else:
        datos = clase.entrada(texto=texto)
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


@evals.command("correr")
def correr_eval(
    conjunto: str = typer.Argument(..., metavar="SET"),
    solo: str | None = typer.Option(None, help="Correr un solo caso."),
    simulado: bool = typer.Option(False, help="Usa esperado.json como respuesta: solo prueba el harness."),
    umbral: float = typer.Option(0.9, help="Precisión mínima por campo."),
    raiz: Path = typer.Option(Path("evals"), help="Carpeta de evals."),
) -> None:
    """Corre un set de evals y deja la ejecución en evals/resultados/."""
    from horma.evals import SETS, correr_set

    if conjunto not in SETS:
        typer.echo(f"Set desconocido: {conjunto}", err=True)
        raise typer.Exit(2)
    proveedor = None
    if simulado:
        casos = sorted(p for p in (raiz / conjunto / "casos").iterdir() if p.is_dir())
        if solo:
            casos = [c for c in casos if c.name == solo]
        proveedor = ProveedorSimulado(
            [json.loads((c / "esperado.json").read_text(encoding="utf-8")) for c in casos])
    res = correr_set(conjunto, raiz=raiz, proveedor=proveedor, umbral=umbral, solo=solo,
                     simulado=simulado)
    for campo, valor in res["campos"].items():
        typer.echo(f"{campo:<26}{valor:.2f}")
    typer.echo(f"\n{res['casos']} casos · {'APROBADO' if res['aprobado'] else 'NO APROBADO'}")
    raise typer.Exit(0 if res["aprobado"] else 1)
