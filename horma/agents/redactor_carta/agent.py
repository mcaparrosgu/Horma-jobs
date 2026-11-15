from horma.agents.base import Agente
from horma.agents.redactor_carta.schemas import EntradaRedactorCarta, SalidaRedactorCarta


class RedactorCarta(Agente[EntradaRedactorCarta, SalidaRedactorCarta]):
    nombre = "redactor-carta"
    modelo = "mayor"
    entrada = EntradaRedactorCarta
    salida = SalidaRedactorCarta
