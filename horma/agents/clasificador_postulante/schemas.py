from pydantic import BaseModel

from horma.schemas.perfil import Perfil


class EntradaClasificadorPostulante(BaseModel):
    perfil: Perfil
