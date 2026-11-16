from horma.agents.base import Agente
from horma.agents.juez_candidatura.schemas import EntradaJuezCandidatura, SalidaJuezCandidatura


class JuezCandidatura(Agente[EntradaJuezCandidatura, SalidaJuezCandidatura]):
    nombre = "juez-candidatura"
    modelo = "mayor"
    entrada = EntradaJuezCandidatura
    salida = SalidaJuezCandidatura
