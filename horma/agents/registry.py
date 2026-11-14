from horma.agents.auditor_fuentes.agent import AuditorFuentes
from horma.agents.auditor_oferta.agent import AuditorOferta
from horma.agents.base import Agente
from horma.agents.clasificador_oferta.agent import ClasificadorOferta
from horma.agents.clasificador_postulante.agent import ClasificadorPostulante
from horma.agents.extractor_oferta.agent import ExtractorOferta
from horma.agents.extractor_perfil.agent import ExtractorPerfil
from horma.agents.generador_cv_base.agent import GeneradorCvBase
from horma.agents.matcher.agent import Matcher

AGENTES: dict[str, type[Agente]] = {
    a.nombre: a for a in (ExtractorOferta, AuditorOferta, ClasificadorOferta, AuditorFuentes,
                          ExtractorPerfil, ClasificadorPostulante, GeneradorCvBase, Matcher)
}
