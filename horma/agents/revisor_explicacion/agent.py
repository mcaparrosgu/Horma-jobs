"""Solo para el eval `recomendacion` (RF-12.21, S10): no entra en ningún flujo."""
from horma.agents.base import Agente
from horma.agents.revisor_explicacion.schemas import EntradaRevisor, SalidaRevisor


class RevisorExplicacion(Agente[EntradaRevisor, SalidaRevisor]):
    nombre = "revisor-explicacion"
    modelo = "pequeno"
    entrada = EntradaRevisor
    salida = SalidaRevisor
