from horma.agents.analizador_oferta.schemas import SalidaAnalizador, TextoOferta
from horma.agents.base import Agente


class AnalizadorOferta(Agente[TextoOferta, SalidaAnalizador]):
    """Una sola llamada por oferta: extrae, clasifica y audita (RF-10.10)."""

    nombre = "analizador-oferta"
    modelo = "pequeno"
    entrada = TextoOferta
    salida = SalidaAnalizador
