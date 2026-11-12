from pydantic import BaseModel

from horma.schemas.oferta import OfertaExtraida


class EntradaClasificador(BaseModel):
    """La oferta ya extraída. Las instrucciones embebidas no se le pasan al clasificador."""

    oferta: OfertaExtraida
