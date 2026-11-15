from horma.agents.base import Agente
from horma.agents.selector_cv_base.schemas import EntradaSelectorCvBase, SalidaSelectorCvBase


class SelectorCvBase(Agente[EntradaSelectorCvBase, SalidaSelectorCvBase]):
    nombre = "selector-cv-base"
    modelo = "pequeno"
    entrada = EntradaSelectorCvBase
    salida = SalidaSelectorCvBase
