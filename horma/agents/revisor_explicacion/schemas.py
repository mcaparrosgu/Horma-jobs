from pydantic import BaseModel


class EntradaRevisor(BaseModel):
    explicacion: str
    cita_perfil: str
    cita_oferta: str


class SalidaRevisor(BaseModel):
    apoyada: bool
    motivo: str
