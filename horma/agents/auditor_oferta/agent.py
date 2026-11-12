from horma.agents.auditor_oferta.schemas import EntradaAuditor, SalidaAuditor
from horma.agents.base import Agente


class AuditorOferta(Agente[EntradaAuditor, SalidaAuditor]):
    nombre = "auditor-oferta"
    modelo = "pequeno"
    entrada = EntradaAuditor
    salida = SalidaAuditor
