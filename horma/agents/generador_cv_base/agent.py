from horma.agents.base import Agente
from horma.agents.generador_cv_base.schemas import EntradaGeneradorCvBase, SalidaGeneradorCvBase


class GeneradorCvBase(Agente[EntradaGeneradorCvBase, SalidaGeneradorCvBase]):
    nombre = "generador-cv-base"
    modelo = "mayor"
    entrada = EntradaGeneradorCvBase
    salida = SalidaGeneradorCvBase
