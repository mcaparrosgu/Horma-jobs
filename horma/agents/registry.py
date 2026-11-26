from horma.agents.analizador_estilo.agent import AnalizadorEstilo
from horma.agents.analizador_oferta.agent import AnalizadorOferta
from horma.agents.auditor_fuentes.agent import AuditorFuentes
from horma.agents.auditor_oferta.agent import AuditorOferta
from horma.agents.base import Agente
from horma.agents.clasificador_oferta.agent import ClasificadorOferta
from horma.agents.clasificador_postulante.agent import ClasificadorPostulante
from horma.agents.clasificador_respuesta.agent import ClasificadorRespuesta
from horma.agents.extractor_oferta.agent import ExtractorOferta
from horma.agents.extractor_perfil.agent import ExtractorPerfil
from horma.agents.generador_cv_base.agent import GeneradorCvBase
from horma.agents.juez_candidatura.agent import JuezCandidatura
from horma.agents.matcher.agent import Matcher
from horma.agents.redactor_carta.agent import RedactorCarta
from horma.agents.redactor_cv.agent import RedactorCv
from horma.agents.sinonimos_puestos.agent import SinonimosPuestos

AGENTES: dict[str, type[Agente]] = {
    a.nombre: a for a in (ExtractorOferta, AuditorOferta, ClasificadorOferta, AuditorFuentes,
                          ExtractorPerfil, ClasificadorPostulante, Matcher,
                          RedactorCv, RedactorCarta, JuezCandidatura,
                          AnalizadorEstilo, AnalizadorOferta, SinonimosPuestos)
}
# Aparcados (RF-10.11d, 21-nov-2026): el código se conserva, pero no están activos ni en la CI.
APARCADOS: dict[str, type[Agente]] = {a.nombre: a for a in (GeneradorCvBase, ClasificadorRespuesta)}
