from horma.agents.base import Agente
from horma.agents.extractor_oferta.schemas import TextoOferta
from horma.schemas.oferta import OfertaExtraida


class ExtractorOferta(Agente[TextoOferta, OfertaExtraida]):
    nombre = "extractor-oferta"
    modelo = "pequeno"
    entrada = TextoOferta
    salida = OfertaExtraida
