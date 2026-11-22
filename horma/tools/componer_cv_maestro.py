"""Compone el CV maestro en Markdown a partir del perfil (RF-5.1).

Código puro y determinista: el mismo perfil da siempre el mismo texto. El perfil es la fuente de verdad
y el maestro se deriva de él, así lo que la usuaria edita o borra se refleja en el maestro y la
trazabilidad de los CV adaptados sigue funcionando (RF-5.1b). No escribe rasgos personales: solo usa
los datos del perfil con encabezados fijos, y las secciones vacías no salen."""
import re

from horma.schemas.perfil import Perfil

_IDIOMAS = {
    "es": "Español", "en": "Inglés", "fr": "Francés", "de": "Alemán", "it": "Italiano", "pt": "Portugués",
    "ca": "Catalán", "eu": "Euskera", "gl": "Gallego", "nl": "Neerlandés", "pl": "Polaco", "ru": "Ruso",
    "zh": "Chino", "ar": "Árabe", "ro": "Rumano", "otro": "Otro idioma",
}


def _nombre_idioma(i) -> str:
    """«Valenciano» si el CV lo dice así (T63); el esquema solo tiene `ca` para catalán y valenciano."""
    if i.idioma == "ca" and "valenci" in i.origen.fragmento.casefold():
        return "Valenciano"
    return _IDIOMAS[i.idioma]


def _linea(*partes: str | None) -> str:
    return " · ".join(p.strip() for p in partes if p and p.strip())


def _fecha(valor: str | None) -> str | None:
    """«2021-03» → «03-2021» (MM-AAAA); «2021», «actual» y lo que no sea AAAA-MM se dejan como están."""
    if not valor:
        return None
    v = valor.strip()
    m = re.fullmatch(r"((?:19|20)\d{2})-(\d{2})", v)
    return f"{m.group(2)}-{m.group(1)}" if m else v


def _periodo(inicio: str | None, fin: str | None) -> str | None:
    inicio, fin = _fecha(inicio), _fecha(fin)
    if inicio and fin:
        # con meses (03-2021) el guion largo evita «03-2021-09-2023»; con solo años se queda «2021-2024»
        return f"{inicio} – {fin}" if "-" in inicio + fin else f"{inicio}-{fin}"
    return inicio or fin


def _seccion(titulo: str, lineas: list[str]) -> list[str]:
    return [f"## {titulo}", *lineas, ""] if lineas else []


def componer_cv_maestro(perfil: Perfil) -> str:
    salida: list[str] = []
    if perfil.nombre:
        salida += [f"# {perfil.nombre.strip()}", ""]
    if perfil.titular:
        salida += [perfil.titular.valor.strip(), ""]
    salida += _seccion("Resumen", [perfil.resumen.valor.strip()] if perfil.resumen else [])

    experiencia: list[str] = []
    for x in perfil.experiencias:
        experiencia.append(_linea(x.puesto, x.empresa, _periodo(x.inicio, x.fin)))
        if x.descripcion and x.descripcion.strip():
            experiencia.append(x.descripcion.strip())
    salida += _seccion("Experiencia", experiencia)

    salida += _seccion("Formación", [
        _linea(f.titulo, f.centro, _periodo(f.inicio, f.fin)) for f in perfil.formacion])
    salida += _seccion("Idiomas", [
        _linea(_nombre_idioma(i) + (f" {i.nivel.strip()}" if i.nivel and i.nivel.strip() else ""))
        for i in perfil.idiomas])
    salida += _seccion("Habilidades", [h.nombre.strip() for h in perfil.habilidades])

    proyectos: list[str] = []
    for p in perfil.proyectos:
        proyectos.append(_linea(p.nombre, _fecha(p.fecha)))
        if p.descripcion and p.descripcion.strip():
            proyectos.append(p.descripcion.strip())
    salida += _seccion("Proyectos", proyectos)
    salida += _seccion("Certificaciones", [_linea(c.nombre, c.entidad, _fecha(c.fecha))
                                           for c in perfil.certificaciones])
    salida += _seccion("Otras actividades", [
        _linea(a.descripcion, _periodo(a.inicio, a.fin)) for a in perfil.actividades])
    # «Información adicional» y no «Otros»: un título que los filtros de CV reconocen (RF-10.16a)
    salida += _seccion("Información adicional", [o.valor.strip() for o in perfil.otros])
    return "\n".join(salida).rstrip() + "\n"
