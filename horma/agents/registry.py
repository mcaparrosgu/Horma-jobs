from horma.agents.base import Agente
from horma.agents.extractor_oferta.agent import ExtractorOferta

AGENTES: dict[str, type[Agente]] = {ExtractorOferta.nombre: ExtractorOferta}
