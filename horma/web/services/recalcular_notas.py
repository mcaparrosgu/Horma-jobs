"""Al cambiar «Qué buscas», las notas se vuelven a acotar en código (spec 012, RF-12.37). Sin modelo y sin
tocar la huella del perfil."""
from sqlalchemy.orm import Session

from horma.schemas.match import Marca, frase_de_franja, sin_frase_de_franja
from horma.tools.acotar_nota import acotar_nota, relacion_que_cuenta
from horma.web.repositories import matches, perfiles


def recalcular(s: Session) -> None:
    """Las de la usuaria de la sesión, con su perfil vigente."""
    vigente = perfiles.vigente(s)
    if not vigente:
        return
    perfil = perfiles.perfil_modelo(vigente)
    prefs = perfiles.preferencias(s)
    familia = perfil.taxonomia.familia if perfil.taxonomia else None
    nivel = perfil.taxonomia.nivel if perfil.taxonomia else None
    for m in matches.recalculables(s):
        relacion = relacion_que_cuenta(m["relacion"], m["titulo"], prefs, familia, m["familia"])
        requisitos = m["requisitos"] or []
        nota = acotar_nota(m["nota_modelo"], [Marca.model_validate(x) for x in m["marcas"]], relacion,
                           requisitos, m["nivel"], nivel, bool(perfil.experiencias))
        if nota == m["nota"]:
            continue
        explicacion = m["explicacion"] if m["retirada"] else \
            f"{frase_de_franja(nota)} {sin_frase_de_franja(m['explicacion'])}"
        matches.cambiar_nota(s, m["oferta_id"], m["perfil_version"], nota, explicacion)
