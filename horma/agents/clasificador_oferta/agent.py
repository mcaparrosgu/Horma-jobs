from horma.agents.base import Agente
from horma.agents.clasificador_oferta.schemas import EntradaClasificador
from horma.schemas.taxonomia import Taxonomia


class ClasificadorOferta(Agente[EntradaClasificador, Taxonomia]):
    nombre = "clasificador-oferta"
    modelo = "pequeno"
    entrada = EntradaClasificador
    salida = Taxonomia
