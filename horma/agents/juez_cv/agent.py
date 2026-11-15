from horma.agents.base import Agente
from horma.agents.juez_cv.schemas import EntradaJuezCv, SalidaJuezCv


class JuezCv(Agente[EntradaJuezCv, SalidaJuezCv]):
    nombre = "juez-cv"
    modelo = "mayor"
    entrada = EntradaJuezCv
    salida = SalidaJuezCv
