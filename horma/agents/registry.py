from horma.agents.auditor_fuentes.agent import AuditorFuentes
from horma.agents.auditor_oferta.agent import AuditorOferta
from horma.agents.base import Agente
from horma.agents.clasificador_oferta.agent import ClasificadorOferta
from horma.agents.clasificador_postulante.agent import ClasificadorPostulante
from horma.agents.clasificador_respuesta.agent import ClasificadorRespuesta
from horma.agents.extractor_oferta.agent import ExtractorOferta
from horma.agents.extractor_perfil.agent import ExtractorPerfil
from horma.agents.generador_cv_base.agent import GeneradorCvBase
from horma.agents.juez_carta.agent import JuezCarta
from horma.agents.juez_cv.agent import JuezCv
from horma.agents.matcher.agent import Matcher
from horma.agents.redactor_carta.agent import RedactorCarta
from horma.agents.redactor_cv.agent import RedactorCv
from horma.agents.selector_cv_base.agent import SelectorCvBase

AGENTES: dict[str, type[Agente]] = {
    a.nombre: a for a in (ExtractorOferta, AuditorOferta, ClasificadorOferta, AuditorFuentes,
                          ExtractorPerfil, ClasificadorPostulante, GeneradorCvBase, Matcher,
                          RedactorCv, JuezCv, RedactorCarta, JuezCarta, ClasificadorRespuesta,
                          SelectorCvBase)
}
