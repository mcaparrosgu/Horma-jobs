from horma.agents.base import Agente
from horma.agents.matcher.schemas import EntradaMatcher, SalidaMatcher


class Matcher(Agente[EntradaMatcher, SalidaMatcher]):
    nombre = "matcher"
    modelo = "mayor"
    entrada = EntradaMatcher
    salida = SalidaMatcher
