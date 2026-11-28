from pydantic import BaseModel


class EntradaRevisor(BaseModel):
    explicacion: str
    cita_perfil: str
    cita_oferta: str
    perfil: dict  # la copia sin nombre ni género que leyó el `matcher`
    oferta: dict


class SalidaRevisor(BaseModel):
    apoyada: bool
    motivo: str
