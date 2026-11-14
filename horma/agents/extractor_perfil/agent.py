from horma.agents.base import Agente
from horma.agents.extractor_perfil.schemas import EntradaExtractorPerfil, SalidaExtractorPerfil


class ExtractorPerfil(Agente[EntradaExtractorPerfil, SalidaExtractorPerfil]):
    nombre = "extractor-perfil"
    modelo = "mayor"
    entrada = EntradaExtractorPerfil
    salida = SalidaExtractorPerfil
