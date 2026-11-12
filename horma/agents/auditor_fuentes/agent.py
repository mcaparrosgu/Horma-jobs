from horma.agents.auditor_fuentes.schemas import EntradaAuditorFuentes, SalidaAuditorFuentes
from horma.agents.base import Agente


class AuditorFuentes(Agente[EntradaAuditorFuentes, SalidaAuditorFuentes]):
    nombre = "auditor-fuentes"
    modelo = "mayor"
    entrada = EntradaAuditorFuentes
    salida = SalidaAuditorFuentes
