from horma.agents.auditor_fuentes.agent import AuditorFuentes
from horma.agents.auditor_oferta.agent import AuditorOferta
from horma.agents.base import Agente
from horma.agents.clasificador_oferta.agent import ClasificadorOferta
from horma.agents.extractor_oferta.agent import ExtractorOferta

AGENTES: dict[str, type[Agente]] = {
    a.nombre: a for a in (ExtractorOferta, AuditorOferta, ClasificadorOferta, AuditorFuentes)
}
