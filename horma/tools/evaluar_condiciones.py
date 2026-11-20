"""Cuánto se parecen las condiciones de una oferta a las que busca la usuaria (RF-2.12).

Código puro, sin IA y sin coste. Solo se miran las condiciones que ella ha marcado: contrato, país,
remoto, sueldo mínimo, idiomas y «solo con salario publicado». Cada una sale «cumple», «no cumple» o
«sin dato» (la oferta no lo dice, o no se puede comparar):

- `bajo`: alguna condición marcada no se cumple.
- `medio`: ninguna falla, pero de alguna no hay dato (p. ej. pide sueldo mínimo y la oferta no lo publica).
- `alto`: todas las marcadas se cumplen, o no ha marcado ninguna."""
from typing import Literal

from horma.schemas.oferta import Oferta
from horma.schemas.preferencias import Preferencias
from horma.tools.normalizar_oferta import normalizar_oferta

Nivel = Literal["bajo", "medio", "alto"]


def evaluar_condiciones(oferta: Oferta, prefs: Preferencias) -> Nivel:
    n = normalizar_oferta(oferta)
    resultados: list[bool | None] = []  # True cumple · False no cumple · None sin dato

    if prefs.contratos:
        resultados.append(None if n.tipo_contrato is None else n.tipo_contrato in prefs.contratos)
    if prefs.paises:
        resultados.append(None if n.pais in (None, "REMOTO") else n.pais in prefs.paises)
    if prefs.idiomas:
        resultados.append(None if not n.idiomas else bool(set(n.idiomas) & set(prefs.idiomas)))
    if prefs.solo_remoto:
        resultados.append(False if oferta.modalidad is None else oferta.modalidad == "remoto")
    if prefs.sueldo_minimo is not None:
        resultados.append(None if n.salario_anual_eur_max is None
                          else n.salario_anual_eur_max >= prefs.sueldo_minimo)
    if prefs.solo_salario:
        resultados.append(oferta.auditoria.salario_publicado)

    if any(r is False for r in resultados):
        return "bajo"
    return "medio" if any(r is None for r in resultados) else "alto"
