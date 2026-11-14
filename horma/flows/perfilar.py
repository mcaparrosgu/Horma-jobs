"""Flujo perfilar (RF-2.1 a 2.8b): extraer → verificar_origen → quitar_sensibles → clasificar →
preferencias_desde_cv → componer. Sin bucle y sin acceso a la base de datos.

Estado de entrada: {"cvs": [{"cv_id": int, "nombre": str, "texto": str}, ...]}.
Estado de salida: además, "perfil" (Perfil, versión 1: la versión real la pone el worker),
"cv_maestro" (Markdown) y "preferencias" (Preferencias con lo que sale del CV).

Lo que el modelo propone, el código lo comprueba (RT-08, RT-09): un dato cuyo fragmento no está en su
CV va a `preguntas_pendientes`; dos CV que se contradicen dejan un pendiente sin elegir; edad,
nacionalidad y demás rasgos personales se descartan aunque el modelo los deje pasar."""
import re
import unicodedata

from horma.agents.clasificador_postulante.agent import ClasificadorPostulante
from horma.agents.clasificador_postulante.schemas import EntradaClasificadorPostulante
from horma.agents.extractor_perfil.agent import ExtractorPerfil
from horma.agents.extractor_perfil.schemas import CvEntrada, EntradaExtractorPerfil, SalidaExtractorPerfil
from horma.flows.plain import PlainFlow
from horma.llm.proveedor import Proveedor
from horma.schemas.perfil import Perfil, PreguntaPendiente
from horma.schemas.preferencias import Preferencias
from horma.schemas.taxonomia import Taxonomia
from horma.tools.rasgos_personales import rasgos_personales

# (campo del perfil, atributo con el nombre del dato, atributos de texto opcionales)
_LISTAS = (
    ("experiencias", "puesto", ("empresa", "descripcion")),
    ("formacion", "titulo", ("centro",)),
    ("idiomas", "idioma", ("nivel",)),
    ("habilidades", "nombre", ()),
)
_UNICOS = ("titular", "resumen")


def _plano(texto: str) -> str:
    t = unicodedata.normalize("NFKC", texto).casefold()
    return re.sub(r"\s+", " ", t).strip()


def _pendiente(campo: str, motivo: str, pregunta: str, opciones: list[str] | None = None) -> dict:
    return PreguntaPendiente(campo=campo, motivo=motivo, pregunta=pregunta,
                             opciones=opciones or []).model_dump(mode="json")


def _origen_valido(origen: dict, textos: dict[int, str]) -> bool:
    if origen.get("fuente") != "cv" or origen.get("cv_id") not in textos:
        return False
    return _plano(origen["fragmento"]) in textos[origen["cv_id"]]


def _periodo(x: dict) -> str:
    return f"{x.get('inicio') or '?'}-{x.get('fin') or '?'}"


def _contradicciones(campo: str, items: list[dict], clave_nombre: str, clave_lugar: str,
                     ) -> tuple[list[dict], list[dict]]:
    """Mismo puesto (o titulación) en el mismo sitio con periodos distintos en CV distintos."""
    grupos: dict[tuple, list[dict]] = {}
    for x in items:
        if x.get(clave_lugar):
            grupos.setdefault((_plano(x[clave_nombre]), _plano(x[clave_lugar])), []).append(x)
    quitar: set[int] = set()
    pendientes: list[dict] = []
    for grupo in grupos.values():
        cvs = {g["origen"]["cv_id"] for g in grupo}
        periodos = list(dict.fromkeys(_periodo(g) for g in grupo))
        if len(cvs) > 1 and len(periodos) > 1:
            quitar.update(id(g) for g in grupo)
            pendientes.append(_pendiente(
                campo, "contradiccion",
                f"Tus CV dicen fechas distintas para «{grupo[0][clave_nombre]}» "
                f"({grupo[0][clave_lugar]}). ¿Cuáles son las correctas?", periodos))
    return [x for x in items if id(x) not in quitar], pendientes


def crear(proveedor: Proveedor | None = None) -> PlainFlow:

    def extraer(e: dict) -> dict:
        cvs = [CvEntrada.model_validate(c) for c in e["cvs"]]
        r = ExtractorPerfil.run(EntradaExtractorPerfil(cvs=cvs), proveedor=proveedor)
        e["extraccion"] = r.model_dump(mode="json")
        return e

    def verificar_origen(e: dict) -> dict:
        textos = {c["cv_id"]: _plano(c["texto"]) for c in e["cvs"]}
        perfil = e["extraccion"]["perfil"]
        pendientes = list(perfil["preguntas_pendientes"])
        for campo, nombre, _ in _LISTAS:
            validos = []
            for x in perfil[campo]:
                if _origen_valido(x["origen"], textos):
                    validos.append(x)
                else:
                    pendientes.append(_pendiente(
                        campo, "falta", f"No he podido confirmar en tus CV «{x[nombre]}». "
                                        "¿Quieres escribirlo tú?"))
            perfil[campo] = validos
        for campo in _UNICOS:
            dato = perfil[campo]
            if dato and not _origen_valido(dato["origen"], textos):
                pendientes.append(_pendiente(campo, "falta", f"No he podido confirmar en tus CV el "
                                                             f"campo «{campo}». ¿Quieres escribirlo tú?"))
                perfil[campo] = None
        for campo, nombre, lugar in (("experiencias", "puesto", "empresa"),
                                     ("formacion", "titulo", "centro")):
            perfil[campo], nuevas = _contradicciones(campo, perfil[campo], nombre, lugar)
            pendientes += nuevas
        # Instrucciones: solo las que están de verdad en algún CV.
        perfil["instrucciones_embebidas"] = [
            i for i in dict.fromkeys(perfil["instrucciones_embebidas"])
            if any(_plano(i) in t for t in textos.values())]
        perfil["preguntas_pendientes"] = pendientes
        return e

    def quitar_sensibles(e: dict) -> dict:
        """RT-09: ni edad, ni nacionalidad, ni categorías del art. 9 llegan al perfil."""
        perfil = e["extraccion"]["perfil"]
        sin_dato = False
        for campo, nombre, opcionales in _LISTAS:
            limpios = []
            for x in perfil[campo]:
                if rasgos_personales(x[nombre]) or rasgos_personales(x["origen"]["fragmento"]):
                    sin_dato = True
                    continue
                for o in opcionales:
                    if x.get(o) and rasgos_personales(x[o]):
                        x[o] = None
                limpios.append(x)
            perfil[campo] = limpios
        for campo in _UNICOS:
            dato = perfil[campo]
            if dato and (rasgos_personales(dato["valor"]) or rasgos_personales(
                    dato["origen"]["fragmento"])):
                perfil[campo] = None
        if perfil["nombre"] and rasgos_personales(perfil["nombre"]):
            perfil["nombre"] = None
        perfil["preguntas_pendientes"] = [
            p for p in perfil["preguntas_pendientes"]
            if not rasgos_personales(" ".join([p["pregunta"], *p["opciones"]]))]
        if sin_dato:
            perfil["preguntas_pendientes"].append(_pendiente(
                "perfil", "falta", "He descartado algún dato de tus CV que no se puede usar. "
                                   "Si falta algo de tu experiencia, escríbelo tú."))
        cv = e["extraccion"]["cv_maestro"]
        e["extraccion"]["cv_maestro"] = "\n".join(
            linea for linea in cv.splitlines() if not rasgos_personales(linea))
        return e

    def clasificar(e: dict) -> dict:
        perfil = Perfil.model_validate(e["extraccion"]["perfil"]).model_copy(
            update={"instrucciones_embebidas": []})
        e["taxonomia"] = ClasificadorPostulante.run(
            EntradaClasificadorPostulante(perfil=perfil), proveedor=proveedor).model_dump(mode="json")
        return e

    def preferencias_desde_cv(e: dict) -> dict:
        tax = Taxonomia.model_validate(e["taxonomia"])
        perfil = Perfil.model_validate(e["extraccion"]["perfil"])
        grupos = {"familias": [tax.familia] if tax.familia != "otros" else [],
                  "sectores": [tax.sector] if tax.sector != "otros" else [],
                  "idiomas": list(dict.fromkeys(i.idioma for i in perfil.idiomas if i.idioma != "otro"))}
        prefs = Preferencias(**grupos, origen={g: "cv" for g, v in grupos.items() if v})
        e["preferencias"] = prefs.model_dump(mode="json")
        return e

    def componer(e: dict) -> dict:
        perfil = Perfil.model_validate({**e["extraccion"]["perfil"], "taxonomia": e["taxonomia"]})
        e["perfil"] = perfil.model_dump(mode="json")
        e["cv_maestro"] = e["extraccion"]["cv_maestro"]
        SalidaExtractorPerfil.model_validate({"perfil": e["perfil"], "cv_maestro": e["cv_maestro"]})
        return e

    pasos = {"extraer": extraer, "verificar_origen": verificar_origen,
             "quitar_sensibles": quitar_sensibles, "clasificar": clasificar,
             "preferencias_desde_cv": preferencias_desde_cv, "componer": componer}
    aristas = {"extraer": "verificar_origen", "verificar_origen": "quitar_sensibles",
               "quitar_sensibles": "clasificar", "clasificar": "preferencias_desde_cv",
               "preferencias_desde_cv": "componer"}
    return PlainFlow("perfilar", pasos=pasos, aristas=aristas, inicio="extraer", finales={"componer"})
