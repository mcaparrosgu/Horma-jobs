"""Compone el CV maestro en Markdown a partir del perfil (RF-5.1).

Código puro y determinista: el mismo perfil da siempre el mismo texto. El perfil es la fuente de verdad
y el maestro se deriva de él, así lo que la usuaria edita o borra se refleja en el maestro y la
trazabilidad de los CV adaptados sigue funcionando (RF-5.1b). No escribe rasgos personales: solo usa
los datos del perfil con encabezados fijos, y las secciones vacías no salen."""
from horma.schemas.perfil import Perfil

_IDIOMAS = {
    "es": "Español", "en": "Inglés", "fr": "Francés", "de": "Alemán", "it": "Italiano", "pt": "Portugués",
    "ca": "Catalán", "eu": "Euskera", "gl": "Gallego", "nl": "Neerlandés", "pl": "Polaco", "ru": "Ruso",
    "zh": "Chino", "ar": "Árabe", "ro": "Rumano", "otro": "Otro idioma",
}


def _linea(*partes: str | None) -> str:
    return " · ".join(p.strip() for p in partes if p and p.strip())


def _periodo(inicio: str | None, fin: str | None) -> str | None:
    if inicio and fin:
        return f"{inicio.strip()}-{fin.strip()}"
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
        _linea(_IDIOMAS[i.idioma] + (f" {i.nivel.strip()}" if i.nivel and i.nivel.strip() else ""))
        for i in perfil.idiomas])
    salida += _seccion("Habilidades", [h.nombre.strip() for h in perfil.habilidades])

    proyectos: list[str] = []
    for p in perfil.proyectos:
        proyectos.append(_linea(p.nombre, p.fecha))
        if p.descripcion and p.descripcion.strip():
            proyectos.append(p.descripcion.strip())
    salida += _seccion("Proyectos", proyectos)
    salida += _seccion("Certificaciones", [_linea(c.nombre, c.entidad, c.fecha)
                                           for c in perfil.certificaciones])
    salida += _seccion("Otras actividades", [
        _linea(a.descripcion, _periodo(a.inicio, a.fin)) for a in perfil.actividades])
    salida += _seccion("Otros", [o.valor.strip() for o in perfil.otros])
    return "\n".join(salida).rstrip() + "\n"
