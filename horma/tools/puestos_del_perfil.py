"""Puerta de puestos por niveles de evidencia (spec 012, RF-12.5 a 12.8; RT-08). Código puro.

El nivel lo decide el campo del que sale el `dato`, comparado entero (un trozo no vale):
- puesto de una experiencia y el título es ese mismo puesto (`relacion`) → nivel 1, «lo has sido»;
- titulación, certificación o puesto con un título distinto → nivel 2, «afín»;
- habilidad, titular, resumen o trozo → fuera.
Nunca se sugiere por encima del nivel del perfil, salvo un puesto que ya ha tenido (D-038).

El modelo lee la copia ciega, así que el `dato` se compara con los campos de la copia (RF-12.30g); se
guarda el texto original y el título se escribe en el género que ella eligió (RF-12.30f)."""
from horma.schemas.perfil import Perfil
from horma.schemas.preferencias import Preferencias, PuestoSugerido
from horma.tools.copia_ciega import copia_ciega
from horma.tools.lexico_genero import a_copia, en_genero
from horma.tools.normalizar_titulo import canonico, supera_nivel
from horma.tools.visibilidad_cv import normalizar

MAX_PUESTOS = 15


def _campos(perfil: Perfil) -> dict[str, tuple[str, str]]:
    """Campo entero de la copia, normalizado → (tipo de dato, texto original). El puesto manda si el mismo
    texto está en dos sitios."""
    copia = copia_ciega(perfil)
    campos: dict[str, tuple[str, str]] = {}
    for tipo, ciegos, originales, atributo in (
            ("certificacion", copia.certificaciones, perfil.certificaciones, "nombre"),
            ("titulacion", copia.formacion, perfil.formacion, "titulo"),
            ("puesto", copia.experiencias, perfil.experiencias, "puesto")):
        campos |= {normalizar(getattr(c, atributo)): (tipo, getattr(o, atributo))
                   for c, o in zip(ciegos, originales, strict=True)}
    return campos


def _titulo(titulo: str, genero: str | None) -> str:
    return en_genero(a_copia(titulo.strip(), titulo=True), genero)


def en_su_genero(prefs: Preferencias, genero: str | None) -> Preferencias:
    """Los puestos sugeridos, y los marcados que salen de ellos, en otro género y sin llamar al modelo
    (RF-12.30f). Los que escribió ella no se tocan."""
    nuevos = {p.titulo: _titulo(p.titulo, genero) for p in prefs.puestos_sugeridos}
    return prefs.model_copy(update={
        "puestos": list(dict.fromkeys(nuevos.get(t, t) for t in prefs.puestos)),
        "puestos_sugeridos": [p.model_copy(update={"titulo": nuevos[p.titulo]})
                              for p in prefs.puestos_sugeridos]})


def puestos_del_perfil(perfil: Perfil, candidatos: list,
                       nivel: str = "sin_especificar") -> list[PuestoSugerido]:
    """`candidatos` tienen `titulo` y `dato`; `nivel` es el de la taxonomía del perfil."""
    campos = _campos(perfil)
    tenidos = {canonico(c.puesto) for c in copia_ciega(perfil).experiencias}
    salida: list[PuestoSugerido] = []
    vistos: set[str] = set()
    for c in candidatos:
        titulo = _titulo(c.titulo, perfil.genero_puestos)
        hallado = campos.get(normalizar(a_copia(c.dato.strip(), titulo=True)))
        if not titulo or hallado is None or normalizar(titulo) in vistos:
            continue
        tipo, original = hallado
        if canonico(titulo) not in tenidos and supera_nivel(titulo, nivel):
            continue
        vistos.add(normalizar(titulo))
        # S1: lo que dice el modelo solo baja de nivel; sin un puesto entero nunca hay nivel 1.
        grado = 1 if tipo == "puesto" and getattr(c, "relacion", "mismo") == "mismo" else 2
        # RF-12.7: sin ninguna experiencia, lo que sale de la titulación llega marcado.
        marcado = grado == 1 or (tipo == "titulacion" and not perfil.experiencias)
        salida.append(PuestoSugerido(titulo=titulo, dato=original, nivel=grado, tipo_dato=tipo,
                                     marcado=marcado))
    return salida[:MAX_PUESTOS]
