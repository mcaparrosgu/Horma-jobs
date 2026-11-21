from horma.agents.base import Agente
from horma.agents.clasificador_postulante.schemas import (
    ClasificacionPostulante,
    EntradaClasificadorPostulante,
)


class ClasificadorPostulante(Agente[EntradaClasificadorPostulante, ClasificacionPostulante]):
    nombre = "clasificador-postulante"
    modelo = "pequeno"
    entrada = EntradaClasificadorPostulante
    salida = ClasificacionPostulante
