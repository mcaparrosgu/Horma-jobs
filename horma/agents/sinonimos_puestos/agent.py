from horma.agents.base import Agente
from horma.agents.sinonimos_puestos.schemas import EntradaSinonimos, SalidaSinonimos


class SinonimosPuestos(Agente[EntradaSinonimos, SalidaSinonimos]):
    nombre = "sinonimos-puestos"
    modelo = "pequeno"
    entrada = EntradaSinonimos
    salida = SalidaSinonimos
