from horma.agents.analizador_estilo.schemas import EntradaAnalizadorEstilo, SalidaAnalizadorEstilo
from horma.agents.base import Agente


class AnalizadorEstilo(Agente[EntradaAnalizadorEstilo, SalidaAnalizadorEstilo]):
    nombre = "analizador-estilo"
    modelo = "mayor"
    entrada = EntradaAnalizadorEstilo
    salida = SalidaAnalizadorEstilo
