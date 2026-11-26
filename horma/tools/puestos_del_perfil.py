"""Puerta de puestos por niveles de evidencia (spec 012, RF-12.5 a 12.8; RT-08). Código puro.

El nivel lo decide el campo del que sale el `dato`, comparado entero (un trozo no vale):
- puesto de una experiencia y el título es ese mismo puesto (`relacion`) → nivel 1, «lo has sido»;
- titulación, certificación o puesto con un título distinto → nivel 2, «afín»;
- habilidad, titular, resumen o trozo → fuera.
Nunca se sugiere por encima del nivel del perfil, salvo un puesto que ya ha tenido (D-038)."""
from horma.schemas.perfil import Perfil
from horma.schemas.preferencias import PuestoSugerido
from horma.tools.normalizar_titulo import canonico, supera_nivel
from horma.tools.visibilidad_cv import normalizar

MAX_PUESTOS = 15


def _campos(perfil: Perfil) -> dict[str, str]:
    """Campo entero normalizado → tipo de dato. El puesto manda si el mismo texto está en dos sitios."""
    campos = {normalizar(x.nombre): "certificacion" for x in perfil.certificaciones}
    campos |= {normalizar(x.titulo): "titulacion" for x in perfil.formacion}
    campos |= {normalizar(x.puesto): "puesto" for x in perfil.experiencias}
    return campos


def puestos_del_perfil(perfil: Perfil, candidatos: list,
                       nivel: str = "sin_especificar") -> list[PuestoSugerido]:
    """`candidatos` tienen `titulo` y `dato`; `nivel` es el de la taxonomía del perfil."""
    campos = _campos(perfil)
    tenidos = {canonico(x.puesto) for x in perfil.experiencias}
    salida: list[PuestoSugerido] = []
    vistos: set[str] = set()
    for c in candidatos:
        titulo, tipo = c.titulo.strip(), campos.get(normalizar(c.dato))
        if not titulo or tipo is None or normalizar(titulo) in vistos:
            continue
        if canonico(titulo) not in tenidos and supera_nivel(titulo, nivel):
            continue
        vistos.add(normalizar(titulo))
        # S1: lo que dice el modelo solo baja de nivel; sin un puesto entero nunca hay nivel 1.
        grado = 1 if tipo == "puesto" and getattr(c, "relacion", "mismo") == "mismo" else 2
        # RF-12.7: sin ninguna experiencia, lo que sale de la titulación llega marcado.
        marcado = grado == 1 or (tipo == "titulacion" and not perfil.experiencias)
        salida.append(PuestoSugerido(titulo=titulo, dato=c.dato.strip(), nivel=grado, tipo_dato=tipo,
                                     marcado=marcado))
    return salida[:MAX_PUESTOS]
