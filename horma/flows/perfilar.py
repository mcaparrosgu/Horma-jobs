"""Flujo perfilar (RF-2.1 a 2.8b): extraer → verificar_origen → quitar_sensibles → clasificar →
preferencias_desde_cv → componer. Sin bucle y sin acceso a la base de datos.

Estado de entrada: {"cvs": [{"cv_id": int, "nombre": str, "texto": str}, ...]} y, si ya había un perfil,
"de_usuaria": lo que ella escribió o corrigió en él (datos con origen «usuaria», nombre y género de los
puestos), que `conservar_usuaria` lleva al perfil nuevo (RF-10.14).
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
from horma.schemas.perfil import Perfil, PeriodoCubierto, PreguntaPendiente
from horma.schemas.preferencias import Preferencias
from horma.schemas.taxonomia import Taxonomia
from horma.tools.componer_cv_maestro import componer_cv_maestro
from horma.tools.puestos_del_perfil import puestos_del_perfil
from horma.tools.rasgos_personales import AVISO_DATO_PERSONAL, rasgos_personales
from horma.tools.resumenes_cv import resumen_de, titular_de

# (campo del perfil, atributo con el nombre del dato, atributos de texto opcionales)
_LISTAS = (
    ("experiencias", "puesto", ("empresa", "descripcion")),
    ("formacion", "titulo", ("centro",)),
    ("idiomas", "idioma", ("nivel",)),
    ("habilidades", "nombre", ()),
    ("proyectos", "nombre", ("descripcion",)),
    ("certificaciones", "nombre", ("entidad",)),
    ("otros", "valor", ()),
)
_UNICOS = ("titular", "resumen")
_ACTIVIDADES = ("actividades", "descripcion", ())  # se verifican como el resto; aparte al quitar sensibles


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


def _fusionar_idiomas(idiomas: list[dict]) -> tuple[list[dict], list[dict]]:
    """Un idioma nunca se pierde: una entrada por idioma. Si los CV dan niveles distintos, el idioma
    se queda SIN nivel (no se elige uno por ella) y se le pregunta cuál es."""
    grupos: dict[str, list[dict]] = {}
    for x in idiomas:
        grupos.setdefault(x["idioma"], []).append(x)
    salida, pendientes = [], []
    for codigo, grupo in grupos.items():
        niveles = list(dict.fromkeys(_plano(g["nivel"]) for g in grupo if g.get("nivel")))
        primero = next((g for g in grupo if g.get("nivel")), grupo[0])
        if len(niveles) > 1:
            textos = list(dict.fromkeys(g["nivel"] for g in grupo if g.get("nivel")))
            salida.append({**primero, "nivel": None})
            pendientes.append(_pendiente(
                f"idiomas.{codigo}.nivel", "contradiccion",
                f"Tus CV dan niveles distintos de «{codigo}». ¿Cuál es el tuyo?", textos))
        else:
            salida.append(primero)
    return salida, pendientes


def _genero_puestos(perfil: dict) -> list[dict]:
    """Si no está claro en qué género escribir los puestos, se le pregunta; nunca se deduce del nombre."""
    if perfil.get("genero_puestos") or not perfil["experiencias"]:
        return []
    return [_pendiente("genero_puestos", "ambiguo",
                       "¿En qué género quieres que aparezcan tus puestos en los CV (camarera o camarero)?",
                       ["femenino", "masculino"])]


def _actividades_sin_sensibles(actividades: list[dict]) -> tuple[list[dict], list[dict]]:
    """Una actividad con un rasgo personal (salud, familia…) se convierte en un periodo cubierto, solo con
    fechas, y se descarta su texto y su cita (RF-9.1d, RT-09). Sin fecha de inicio válida, se descarta."""
    quedan, periodos = [], []
    for a in actividades:
        if not (rasgos_personales(a["descripcion"]) or rasgos_personales(a["origen"]["fragmento"])):
            quedan.append(a)
            continue
        try:
            periodo = PeriodoCubierto(inicio=a.get("inicio") or "", fin=a.get("fin") or a.get("inicio") or "")
        except ValueError:
            continue
        periodos.append(periodo.model_dump(mode="json"))
    return quedan, periodos


_VACIAS = (("experiencias", "No encuentro experiencia en tu CV. ¿Quieres añadirla?"),
           ("formacion", "No encuentro estudios en tu CV. ¿Quieres añadirlos?"),
           ("idiomas", "No encuentro idiomas en tu CV. ¿Quieres añadirlos?"))


def _clave(x: dict, nombre: str, lugar: str | None) -> tuple:
    return (_plano(str(x.get(nombre) or "")), _plano(str(x.get(lugar) or "")) if lugar else "")


def resumenes_por_cv(perfil: dict, cvs: list[dict]) -> None:
    """El titular y el resumen de cada CV, tal como están escritos y con su origen; ninguno se pierde al
    juntar CV. `titular` y `resumen` quedan como los del CV más reciente que los tenga (RF-10.14d)."""
    for lista, unico, extraer in (("titulares", "titular", titular_de), ("resumenes", "resumen", resumen_de)):
        datos = []
        for c in cvs:
            texto = extraer(c["texto"])
            if texto and not rasgos_personales(texto):
                datos.append({"valor": texto,
                              "origen": {"fuente": "cv", "cv_id": c["cv_id"], "fragmento": texto}})
        perfil[lista] = datos
        if datos:
            perfil[unico] = datos[-1]


def conservar_usuaria(perfil: dict, de_usuaria: dict | None) -> None:
    """Lo que escribió o corrigió la usuaria pasa al perfil nuevo y manda sobre lo que el CV dice de lo mismo
    (mismo puesto y sitio, mismo título…). Lo suyo no se vuelve a comprobar contra un CV (RF-10.14)."""
    if not de_usuaria:
        return
    # Las propuestas que aún no ha confirmado siguen pendientes en la versión nueva (RF-10.15d).
    perfil["preguntas_pendientes"] = [*perfil["preguntas_pendientes"],
                                      *(de_usuaria.get("propuestas") or [])]
    lugares = {c: lugar for c, _, lugar in (
        ("experiencias", "puesto", "empresa"), ("formacion", "titulo", "centro"),
        ("certificaciones", "nombre", "entidad"))}
    for campo, nombre, _ in (*_LISTAS, _ACTIVIDADES):
        suyos = de_usuaria.get(campo) or []
        if not suyos:
            continue
        lugar = lugares.get(campo)
        claves = {_clave(x, nombre, lugar) for x in suyos}
        perfil[campo] = [x for x in perfil[campo] if _clave(x, nombre, lugar) not in claves] + list(suyos)
    for campo in _UNICOS:
        if de_usuaria.get(campo):
            perfil[campo] = de_usuaria[campo]
    for campo in ("nombre", "genero_puestos"):
        if de_usuaria.get(campo):   # el nombre que ella editó manda sobre el del CV (RF-10.5f, RF-10.14)
            perfil[campo] = de_usuaria[campo]
        if campo == "genero_puestos" and perfil.get(campo):
            perfil["preguntas_pendientes"] = [p for p in perfil["preguntas_pendientes"]
                                              if p["campo"] != "genero_puestos"]


def _perfil_vacio(perfil: dict, pendientes: list[dict]) -> list[dict]:
    """Un CV sin experiencia, formación ni idiomas no puede quedarse en silencio: se pregunta por cada
    sección, sin depender de que el modelo lo haga (RF-2.3)."""
    if any(perfil[c] for c, _ in _VACIAS):
        return []
    ya = {p["campo"].split(".")[0] for p in pendientes}
    return [_pendiente(campo, "falta", pregunta) for campo, pregunta in _VACIAS if campo not in ya]


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
        perfil["periodos_cubiertos"] = []  # solo los crea el código (RF-9.1d)
        for campo, nombre, _ in (*_LISTAS, _ACTIVIDADES):
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
        perfil["idiomas"], nuevas = _fusionar_idiomas(perfil["idiomas"])
        pendientes += nuevas
        pendientes += _genero_puestos(perfil)
        pendientes += _perfil_vacio(perfil, pendientes)
        # Instrucciones: solo las que están de verdad en algún CV.
        perfil["instrucciones_embebidas"] = [
            i for i in dict.fromkeys(perfil["instrucciones_embebidas"])
            if any(_plano(i) in t for t in textos.values())]
        perfil["preguntas_pendientes"] = pendientes
        return e

    def quitar_sensibles(e: dict) -> dict:
        """RT-09: ni edad, ni nacionalidad, ni categorías del art. 9 llegan al perfil. El aviso sale también
        si solo está en el texto de un CV (el extractor no los anota, no hay nada que quitar): M12b."""
        perfil = e["extraccion"]["perfil"]
        sin_dato = quitado = False
        for campo, nombre, opcionales in _LISTAS:
            limpios = []
            for x in perfil[campo]:
                if rasgos_personales(x[nombre]) or rasgos_personales(x["origen"]["fragmento"]):
                    sin_dato = True
                    continue
                for o in opcionales:
                    if x.get(o) and rasgos_personales(x[o]):
                        x[o] = None
                        quitado = True
                limpios.append(x)
            perfil[campo] = limpios
        antes = len(perfil["actividades"])
        perfil["actividades"], periodos = _actividades_sin_sensibles(perfil["actividades"])
        perfil["periodos_cubiertos"] = periodos
        quitado = sin_dato or len(perfil["actividades"]) < antes or quitado
        quitado = quitado or any(rasgos_personales(c["texto"]) for c in e["cvs"])
        for campo in _UNICOS:
            dato = perfil[campo]
            if dato and (rasgos_personales(dato["valor"]) or rasgos_personales(
                    dato["origen"]["fragmento"])):
                perfil[campo] = None
                quitado = True
        if perfil["nombre"] and rasgos_personales(perfil["nombre"]):
            perfil["nombre"] = None
            quitado = True
        perfil["preguntas_pendientes"] = [
            p for p in perfil["preguntas_pendientes"]
            if not rasgos_personales(" ".join([p["pregunta"], *p["opciones"]]))]
        if quitado:  # RF-11.25: se le dice siempre, con el mismo texto que al editar el perfil
            perfil["preguntas_pendientes"].append(_pendiente(
                "perfil", "falta", f"{AVISO_DATO_PERSONAL} Si falta algo de tu experiencia, escríbelo tú."))
        return e

    def conservar(e: dict) -> dict:
        resumenes_por_cv(e["extraccion"]["perfil"], e["cvs"])
        conservar_usuaria(e["extraccion"]["perfil"], e.get("de_usuaria"))
        return e

    def clasificar(e: dict) -> dict:
        perfil = Perfil.model_validate(e["extraccion"]["perfil"]).model_copy(
            update={"instrucciones_embebidas": []})
        r = ClasificadorPostulante.run(EntradaClasificadorPostulante(perfil=perfil), proveedor=proveedor)
        e["taxonomia"] = r.model_dump(mode="json", exclude={"puestos"})
        e["puestos"] = [p.model_dump(mode="json") for p in puestos_del_perfil(perfil, r.puestos)]
        return e

    def preferencias_desde_cv(e: dict) -> dict:
        tax = Taxonomia.model_validate(e["taxonomia"])
        perfil = Perfil.model_validate(e["extraccion"]["perfil"])
        grupos = {"familias": [tax.familia] if tax.familia != "otros" else [],
                  "sectores": [tax.sector] if tax.sector != "otros" else [],
                  "idiomas": list(dict.fromkeys(i.idioma for i in perfil.idiomas if i.idioma != "otro"))}
        sugeridos = e.get("puestos") or []
        grupos["puestos"] = [p["titulo"] for p in sugeridos]
        prefs = Preferencias(**grupos, puestos_sugeridos=sugeridos,
                             origen={g: "cv" for g, v in grupos.items() if v})
        e["preferencias"] = prefs.model_dump(mode="json")
        return e

    def componer(e: dict) -> dict:
        perfil = Perfil.model_validate({**e["extraccion"]["perfil"], "taxonomia": e["taxonomia"]})
        e["perfil"] = perfil.model_dump(mode="json")
        e["cv_maestro"] = componer_cv_maestro(perfil)  # siempre por código (RF-5.1)
        SalidaExtractorPerfil.model_validate({"perfil": e["perfil"]})
        return e

    pasos = {"extraer": extraer, "verificar_origen": verificar_origen,
             "quitar_sensibles": quitar_sensibles, "conservar_usuaria": conservar, "clasificar": clasificar,
             "preferencias_desde_cv": preferencias_desde_cv, "componer": componer}
    aristas = {"extraer": "verificar_origen", "verificar_origen": "quitar_sensibles",
               "quitar_sensibles": "conservar_usuaria", "conservar_usuaria": "clasificar",
               "clasificar": "preferencias_desde_cv",
               "preferencias_desde_cv": "componer"}
    return PlainFlow("perfilar", pasos=pasos, aristas=aristas, inicio="extraer", finales={"componer"})
