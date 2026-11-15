from horma.agents.base import Agente
from horma.agents.juez_carta.schemas import EntradaJuezCarta, SalidaJuezCarta


class JuezCarta(Agente[EntradaJuezCarta, SalidaJuezCarta]):
    nombre = "juez-carta"
    modelo = "mayor"
    entrada = EntradaJuezCarta
    salida = SalidaJuezCarta
