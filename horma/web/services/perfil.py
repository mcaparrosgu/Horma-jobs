"""Servicio de perfil: cualquier cambio de la usuaria crea una versión nueva y conserva la anterior
(RF-2.4). El dato que escribe ella lleva como origen «usuaria»; la taxonomía se recalcula en segundo
plano con `clasificar_perfil` y los CV base y matches de versiones anteriores quedan desfasados, sin
regenerarse solos."""
from collections.abc import Callable
from datetime import date

from pydantic import ValidationError
from sqlalchemy import Engine

from horma.config import ajustes
from horma.schemas.perfil import CAMPO_PROPUESTA, Perfil, PeriodoCubierto
from horma.tools.avisos_perfil import agrupar_avisos, aviso_de_hueco, avisos_perfil
from horma.tools.componer_cv_maestro import componer_cv_maestro
from horma.tools.detectar_huecos import detectar_huecos
from horma.tools.generar_pdf import generar_pdf
from horma.tools.huella_perfil import huella_clasificacion
from horma.tools.rasgos_personales import AVISO_DATO_PERSONAL, rasgos_personales
from horma.web.db import sesion_de
from horma.web.repositories import perfiles
from horma.web.services import presupuesto
from horma.web.services.presupuesto import SinPresupuesto

LISTAS = ("experiencias", "formacion", "idiomas", "habilidades", "proyectos", "certificaciones",
          "actividades", "otros")
UNICOS = ("titular", "resumen")


class SinPerfil(Exception):
    """La usuaria aún no tiene un perfil construido."""


class DatoNoValido(Exception):
    """El cambio pedido no es posible o el dato no cumple el esquema."""


def _origen_usuaria(dato: dict) -> dict:
    texto = " · ".join(str(v) for k, v in dato.items() if k != "origen" and v not in (None, "", []))
    return {"fuente": "usuaria", "fragmento": texto or "usuaria"}


def _con_origen(dato: dict) -> dict:
    return {**{k: v for k, v in dato.items() if k != "origen"}, "origen": _origen_usuaria(dato)}




_NOMBRES_DE_DATO = ("nombre", "puesto", "titulo", "idioma", "valor", "descripcion")


def _periodo_de(dato: dict) -> dict:
    try:
        p = PeriodoCubierto(inicio=dato.get("inicio") or "", fin=dato.get("fin") or dato.get("inicio") or "")
    except ValidationError as e:
        raise DatoNoValido("Pon al menos la fecha de inicio (MM-AAAA o AAAA).") from e
    return p.model_dump(mode="json")


def _actividad_nueva(p: dict, dato: dict, antigua: int | None = None) -> str | None:
    """Una actividad suya con un rasgo personal se guarda solo como periodo cubierto (RF-9.1d, RT-09)."""
    sensible = rasgos_personales(str(dato.get("descripcion") or ""))
    if antigua is not None:
        p["actividades"].pop(antigua)
    if sensible:
        p["periodos_cubiertos"].append(_periodo_de(dato))
        return AVISO_DATO_PERSONAL
    nuevo = _con_origen(dato)
    if antigua is None:
        p["actividades"].append(nuevo)
    else:
        p["actividades"].insert(antigua, nuevo)
    return None


def _sin_sensibles(dato: dict) -> tuple[dict | None, bool]:
    """RT-09 en las ediciones a mano: el texto con un rasgo personal no se guarda. Si lo tiene el nombre del
    dato (puesto, título…), el dato entero se descarta; si lo tiene otro campo (descripción…), solo ese."""
    for k in _NOMBRES_DE_DATO[:-1]:  # sin «descripcion»: esa se limpia, no descarta el dato
        if isinstance(dato.get(k), str) and rasgos_personales(dato[k]):
            return None, True
    limpio, quitado = dict(dato), False
    for k, v in dato.items():
        if k != "origen" and isinstance(v, str) and rasgos_personales(v):
            limpio[k], quitado = None, True
    return limpio, quitado


def _nueva_version(engine: Engine, usuaria_id: int, cambio: Callable[[dict], str | None]) -> dict:
    a = ajustes()
    with sesion_de(engine, usuaria_id) as s:
        fila = perfiles.vigente(s)
        if fila is None:
            raise SinPerfil
        datos = perfiles.perfil_modelo(fila).model_dump(mode="json")
        aviso = cambio(datos)
        try:
            perfil = Perfil.model_validate(datos)
        except ValidationError as e:
            raise DatoNoValido("El dato no es válido: " + "; ".join(
                f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors()[:3])) from e
        anterior = perfiles.perfil_modelo(fila)
        antes = huella_clasificacion(anterior)
        cambia_clasificacion = antes != huella_clasificacion(perfil)
        perfil_id, version = perfiles.nueva_version(s, usuaria_id)
        perfiles.guardar_perfil(s, usuaria_id, perfil_id, perfil.model_copy(update={"version": version}),
                                componer_cv_maestro(perfil))
        if perfil.genero_puestos != anterior.genero_puestos:
            perfiles.reescribir_puestos(s, usuaria_id, perfil.genero_puestos)
        if cambia_clasificacion:  # RF-10.10d y RF-12.30h: solo si cambia lo que lee el clasificador
            try:  # sin presupuesto la edición se guarda y la clasificación espera a otro cambio (RF-10.9c)
                presupuesto.encolar(s, usuaria_id, "clasificar_perfil", perfil_id, a.tope_coste_perfilar,
                                    a.tope_reintentos_tarea)
            except SinPresupuesto:
                pass
    return {"id": perfil_id, "version": version, **({"aviso": aviso} if aviso else {})}


def _buscar(elementos: list[dict], clave: str) -> int | None:
    """Posición del dato al que se refiere la pregunta (por empresa, centro, idioma…), si lo hay."""
    clave = clave.strip().lower()
    for i, x in enumerate(elementos):
        if any(isinstance(v, str) and v.strip().lower() == clave
               for k, v in x.items() if k != "origen"):
            return i
    return None


def _nombre_de_dato(dato: dict) -> str:
    for k in _NOMBRES_DE_DATO:
        if dato.get(k):
            return str(dato[k])
    return ""


SECCIONES_PROPUESTA = ("experiencias", "habilidades", "formacion", "otros")   # RF-10.15d


def _descartar_propuesta(engine: Engine, usuaria_id: int, indice: int) -> dict | None:
    """Descartar una propuesta no cambia ningún dato: se quita de «Por resolver» sin crear versión, y así
    nada queda «desfasado» (RF-10.15d). Devuelve `None` si ese pendiente no es una propuesta."""
    with sesion_de(engine, usuaria_id) as s:
        fila = perfiles.vigente(s)
        if fila is None:
            raise SinPerfil
        pendientes = list(fila["preguntas_pendientes"] or [])
        if not 0 <= indice < len(pendientes) or pendientes[indice]["campo"] != CAMPO_PROPUESTA:
            return None
        pendientes.pop(indice)
        perfiles.guardar_pendientes(s, fila["id"], pendientes)
        return {"id": fila["id"], "version": fila["version"]}


def responder(engine: Engine, usuaria_id: int, indice: int, dato: dict | None,
              seccion_elegida: str | None = None) -> dict:
    """Responde una pregunta pendiente: la quita y, si trae un dato, lo añade con origen «usuaria».
    Devuelve también `cambio` (sección y dato que han cambiado) para decírselo a ella (RF-10.14e).
    Una propuesta (RF-10.15d) se coloca en `seccion_elegida`; sin dato, se descarta sin versión nueva."""
    cambiado: dict = {}
    if dato is None and (descartada := _descartar_propuesta(engine, usuaria_id, indice)) is not None:
        return descartada

    def cambio(p: dict) -> str | None:
        pendientes = p["preguntas_pendientes"]
        if not 0 <= indice < len(pendientes):
            raise DatoNoValido("Esa pregunta pendiente no existe.")
        campo = pendientes.pop(indice)["campo"]
        if dato is None:
            return
        if campo == CAMPO_PROPUESTA:
            if seccion_elegida not in SECCIONES_PROPUESTA:
                raise DatoNoValido("Elige dónde va: experiencia, habilidades, formación u otros.")
            campo = seccion_elegida
        # El modelo a veces pregunta por un dato concreto: «experiencias.Hotel Marina.fechas».
        seccion, _, resto = campo.partition(".")
        clave = resto.partition(".")[0]
        nuevo = {k: v for k, v in dato.items() if v not in (None, "")}
        aviso = None
        if seccion != "actividades" and seccion in (*LISTAS, *UNICOS):
            nuevo, quitado = _sin_sensibles(nuevo)
            nuevo = {k: v for k, v in (nuevo or {}).items() if v not in (None, "")}
            aviso = AVISO_DATO_PERSONAL if quitado else None
            if not nuevo:
                return aviso
        if seccion == "actividades":
            cambiado.update(campo="actividades", valor=_nombre_de_dato(nuevo))
            return _actividad_nueva(p, nuevo)
        if seccion in LISTAS:
            existente = _buscar(p[seccion], clave) if clave else None
            if existente is None:
                p[seccion].append(_con_origen(nuevo))
                cambiado.update(campo=seccion, valor=_nombre_de_dato(nuevo))
            else:
                p[seccion][existente] = _con_origen({**p[seccion][existente], **nuevo})
                cambiado.update(campo=seccion, valor=_nombre_de_dato(p[seccion][existente]))
        elif seccion in UNICOS:
            p[seccion] = _con_origen(nuevo)
            cambiado.update(campo=seccion, valor=_nombre_de_dato(nuevo))
        elif seccion == "genero_puestos":
            if nuevo.get("valor") not in ("femenino", "masculino"):
                raise DatoNoValido("Elige «femenino» o «masculino».")
            p["genero_puestos"] = nuevo["valor"]
            cambiado.update(campo="genero_puestos", valor=nuevo["valor"])
        elif seccion == "nombre" and nuevo.get("valor"):
            p["nombre"] = str(nuevo["valor"]).strip()
            cambiado.update(campo="nombre", valor=p["nombre"])
        else:
            raise DatoNoValido(f"La pregunta sobre «{campo}» no admite un dato: respóndela sin dato.")
        return aviso
    resultado = _nueva_version(engine, usuaria_id, cambio)
    return {**resultado, **({"cambio": cambiado} if cambiado else {})}


def corregir(engine: Engine, usuaria_id: int, campo: str, indice: int | None,
             dato: dict | None) -> dict:
    """Cambia o quita un dato del perfil (en una lista, el que está en `indice`)."""
    def cambio(p: dict) -> str | None:
        if campo == "actividades" and dato is not None:
            if indice is not None and not 0 <= indice < len(p[campo]):
                raise DatoNoValido("Ese dato no existe.")
            return _actividad_nueva(p, dato, indice)
        limpio, quitado = (None, False) if dato is None else _sin_sensibles(dato)
        aviso = AVISO_DATO_PERSONAL if quitado else None
        if campo in LISTAS:
            if indice is None and dato is not None:  # sin índice: dato nuevo al final de la lista
                if limpio is not None:
                    p[campo].append(_con_origen(limpio))
                return aviso
            if indice is None or not 0 <= indice < len(p[campo]):
                raise DatoNoValido("Ese dato no existe.")
            if dato is None:
                p[campo].pop(indice)
            elif limpio is None:
                p[campo].pop(indice)
            else:
                p[campo][indice] = _con_origen(limpio)
            return aviso
        elif campo in UNICOS:
            p[campo] = None if limpio is None else _con_origen(limpio)
            return aviso
        elif campo == "nombre":   # su nombre, tal como sale en el encabezado de «Tu CV completo»
            valor = str((dato or {}).get("valor") or "").strip()
            if not valor:
                raise DatoNoValido("Escribe tu nombre.")
            p["nombre"] = valor
        elif campo == "genero_puestos":
            valor = (dato or {}).get("valor")
            if valor not in ("femenino", "masculino"):
                raise DatoNoValido("Elige «femenino» o «masculino».")
            p["genero_puestos"] = valor
        else:
            raise DatoNoValido(f"El campo «{campo}» no se puede corregir.")
    return _nueva_version(engine, usuaria_id, cambio)


def hay_perfil(engine: Engine, usuaria_id: int) -> bool:
    with sesion_de(engine, usuaria_id) as s:
        return perfiles.vigente(s) is not None


def _estado_ultima(s, usuaria_id: int, fila: dict | None, ultima: dict | None) -> dict:
    """Qué pasa con la versión más nueva que la vigente: se construye, espera presupuesto (RF-10.18g: sin
    tarea y sin presupuesto hoy; la recoge `rehacer_aplazados`) o falló."""
    nueva = ultima is not None and (fila is None or ultima["version"] > fila["version"])
    pendiente = nueva and ultima["estado"] == "pendiente"
    aplazado = pendiente and ultima["sin_tarea"] and \
        presupuesto.restante_hoy(s, usuaria_id) < presupuesto.MIN_USD
    return {"construyendo": pendiente and not aplazado, "aplazado": aplazado,
            "error": ultima["motivo_error"] if nueva and ultima["estado"] == "error" else None}


def ver(engine: Engine, usuaria_id: int) -> dict:
    with sesion_de(engine, usuaria_id) as s:
        fila, ultima = perfiles.vigente(s), perfiles.ultima(s)
        estado = _estado_ultima(s, usuaria_id, fila, ultima)
        if fila is None:
            return {"perfil": None, "origenes": [], **estado}
        return {"perfil": perfiles.perfil_modelo(fila).model_dump(mode="json"),
                "cv_maestro": fila["cv_maestro"], "creado_en": fila["creado_en"],
                "origenes": perfiles.origenes(s, fila["id"]), **estado}


def cv_completo_pdf(engine: Engine, usuaria_id: int) -> bytes:
    """PDF de «Tu CV completo» (RF-10.4): el CV maestro del perfil vigente, sin modelo."""
    with sesion_de(engine, usuaria_id) as s:
        fila = perfiles.vigente(s)
        nombre = perfiles.perfil_modelo(fila).nombre if fila else None
    if fila is None or not (fila["cv_maestro"] or "").strip():
        raise SinPerfil
    return generar_pdf(fila["cv_maestro"], f"CV completo · {nombre}" if nombre else "CV completo")


def avisos(engine: Engine, usuaria_id: int) -> dict:
    """Huecos y avisos por reglas del perfil vigente, sin los que ella dio por vistos (RF-9.1c, RF-9.2).
    Se calculan al pedirlos; no se guardan."""
    with sesion_de(engine, usuaria_id) as s:
        fila = perfiles.vigente(s)
        longitud = perfiles.longitud_cv(s)
        if fila is None:
            return {"huecos": [], "avisos": [], "grupos": [], "total": 0, "longitud": longitud}
        perfil = perfiles.perfil_modelo(fila)
        textos = {c["cv_id"]: c["texto"] for c in perfiles.cvs_fuente(s)}
        vistos = perfiles.avisos_vistos(s)
        huecos = [aviso_de_hueco(h) for h in detectar_huecos(perfil, date.today())]
        por_reglas = avisos_perfil(perfil, fila["cv_maestro"] or "", textos)
    if longitud:  # elegir una longitud cuenta como dar por visto el aviso de CV largo (RF-9.2d)
        por_reglas = [a for a in por_reglas if a.clave != "largo"]

    def visibles(lista):
        return [{"clave": a.clave, "huella": a.huella, "texto": a.texto, "seccion": a.seccion,
                 "indice": a.indice}
                for a in lista if vistos.get(a.clave) != a.huella]
    h, a = visibles(huecos), visibles(por_reglas)
    grupos = agrupar_avisos(h + a)
    return {"huecos": h, "avisos": a, "grupos": grupos, "total": len(grupos), "longitud": longitud}


def dar_por_visto(engine: Engine, usuaria_id: int, clave: str, huella: str) -> None:
    with sesion_de(engine, usuaria_id) as s:
        perfiles.marcar_visto(s, usuaria_id, clave, huella)


def elegir_longitud(engine: Engine, usuaria_id: int, longitud: str) -> None:
    with sesion_de(engine, usuaria_id) as s:
        perfiles.fijar_longitud(s, usuaria_id, longitud)
