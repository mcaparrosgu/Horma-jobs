from horma.agents.base import Agente
from horma.agents.redactor_cv.schemas import EntradaRedactorCv, SalidaRedactorCv


class RedactorCv(Agente[EntradaRedactorCv, SalidaRedactorCv]):
    nombre = "redactor-cv"
    modelo = "mayor"
    entrada = EntradaRedactorCv
    salida = SalidaRedactorCv
