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
    tope_coste_puntuar_propias: float = 1.00  # fase 5: las ofertas que la usuaria añade

    # Fase 5 · Lector de URL (Apify). Sin token no se lee ninguna URL; límite por usuaria y hora (RF-5.3j)
    apify_token: str = ""
    apify_timeout_s: float = 60.0
    limite_url_hora: int = 10

    # Fase 3: topes de construcción (USD); el de uso real se fija al medir el coste, antes de usuarias
    tope_coste_candidatura: float = 1.00

    # Fase 4 · Límites de ritmo por minuto (RF-4.6d): login por IP; CV y candidaturas por usuaria
    limite_login_por_minuto: int = 20
    limite_cv_por_minuto: int = 10
    limite_candidaturas_por_minuto: int = 10

    # Fase 4: implementación del flujo `candidatura` ("plain" o "langgraph")
    horma_flow_impl: str = "plain"

    # Fase 4 · Alertas (RF-4.7b). Sin `SMTP_HOST` solo hay pantalla y log.
    alerta_gasto_dia_usd: float = 5.0
    alerta_tasa_errores: float = 0.5  # fracción de llamadas con resultado distinto de «ok», última hora
    alerta_min_llamadas: int = 10  # mínimo de llamadas en la última hora para evaluar la tasa
    alerta_intervalo_min: int = 5  # cada cuántos minutos comprueba el worker
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_usuario: str = ""
    smtp_password: str = ""
    alertas_correo: str = ""
    horma_dominio: str = ""  # para el enlace a /costes del correo

    def admins(self) -> set[str]:
        return {s.strip() for s in self.horma_admins.split(",") if s.strip()}


@lru_cache
def ajustes() -> Ajustes:
    return Ajustes()
