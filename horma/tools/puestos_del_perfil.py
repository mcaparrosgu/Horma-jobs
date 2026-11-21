"""Filtra los puestos que propone el modelo: solo quedan los que citan un dato presente en el perfil
(RF-9.3, RT-08). Código puro."""
from horma.schemas.perfil import Perfil
from horma.schemas.preferencias import PuestoSugerido
from horma.tools.visibilidad_cv import normalizar

MAX_PUESTOS = 15


def _datos(perfil: Perfil) -> list[str]:
    textos = [x.puesto for x in perfil.experiencias]
    textos += [x.titulo for x in perfil.formacion]
    textos += [x.nombre for x in perfil.habilidades]
    textos += [x.nombre for x in perfil.certificaciones]
    if perfil.titular:
        textos.append(perfil.titular.valor)
    if perfil.resumen:
        textos.append(perfil.resumen.valor)
    return [normalizar(t) for t in textos if t]


def puestos_del_perfil(perfil: Perfil, candidatos: list) -> list[PuestoSugerido]:
    """`candidatos` tienen `titulo` y `dato`. Sin dato en el perfil o repetidos, se descartan."""
    datos = _datos(perfil)
    salida: list[PuestoSugerido] = []
    vistos: set[str] = set()
    for c in candidatos:
        titulo, dato = c.titulo.strip(), normalizar(c.dato)
        if not titulo or not dato or normalizar(titulo) in vistos:
            continue
        if not any(dato in d for d in datos):
            continue
        vistos.add(normalizar(titulo))
        salida.append(PuestoSugerido(titulo=titulo, dato=c.dato.strip()))
    return salida[:MAX_PUESTOS]
