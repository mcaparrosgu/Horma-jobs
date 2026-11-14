from horma.agents.base import Agente
from horma.agents.clasificador_postulante.schemas import EntradaClasificadorPostulante
from horma.schemas.taxonomia import Taxonomia


class ClasificadorPostulante(Agente[EntradaClasificadorPostulante, Taxonomia]):
    nombre = "clasificador-postulante"
    modelo = "pequeno"
    entrada = EntradaClasificadorPostulante
    salida = Taxonomia
