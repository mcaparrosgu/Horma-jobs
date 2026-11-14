"""Configuración desde .env (nunca secretos en el código)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Ajustes(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "info"
    anthropic_api_key: str = ""
    # Modelo real por tamaño de modelo (ajustables por entorno)
    modelo_pequeno: str = "claude-haiku-5-5"
    modelo_mayor: str = "claude-sonnet-5-5"
    # Precio en USD por millón de tokens (entrada, salida): ESTIMADOS, revisar con la tarifa oficial
    precio_pequeno: tuple[float, float] = (1.0, 5.0)
    precio_mayor: tuple[float, float] = (3.0, 15.0)
    llm_timeout_s: float = 60.0
    llm_reintentos: int = 3

    database_url: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    session_secret: str = ""
    horma_flujo_en_linea: bool = False
    tope_coste_tarea: float = 0.50
    tope_reintentos_tarea: int = 3

    # Fase 1
    horma_admins: str = ""  # identificadores `sub` de Google separados por comas
    limite_ofertas_por_minuto: int = 60  # por clave de API
    # Ingestor y consola: hablan con la API, nunca con la base de datos (RF-1.2)
    horma_api_url: str = "http://127.0.0.1:8000"
    horma_clave_ingesta: str = ""

    # Fase 2: archivos de CV (volumen solo de la API) y topes de coste por tipo de tarea (USD)
    ruta_archivos: str = "data/archivos"
    max_cv_bytes: int = 5 * 1024 * 1024
    tope_coste_perfilar: float = 0.50
    tope_coste_cv_base: float = 0.50
    tope_coste_recomendar: float = 1.00

    def admins(self) -> set[str]:
        return {s.strip() for s in self.horma_admins.split(",") if s.strip()}


@lru_cache
def ajustes() -> Ajustes:
    return Ajustes()
