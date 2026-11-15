from horma.agents.base import Agente
from horma.agents.clasificador_respuesta.schemas import (
    EntradaClasificadorRespuesta,
    SalidaClasificadorRespuesta,
)


class ClasificadorRespuesta(Agente[EntradaClasificadorRespuesta, SalidaClasificadorRespuesta]):
    nombre = "clasificador-respuesta"
    modelo = "pequeno"
    entrada = EntradaClasificadorRespuesta
    salida = SalidaClasificadorRespuesta
