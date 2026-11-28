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
    # Precio en USD por millón de tokens (entrada, salida): tarifa oficial de Anthropic consultada el
    # 21-nov-2026 (platform.claude.com/docs/en/about-claude/pricing). Haiku 5.5: tramo de hasta 100K tokens
    # por petición (0,50 / 2,50 por encima); nuestras peticiones son siempre más cortas.
    precio_pequeno: tuple[float, float] = (0.10, 0.50)
    precio_mayor: tuple[float, float] = (2.0, 10.0)
    llm_timeout_s: float = 240.0  # una tanda con marcas por requisito pasa de 60 s (spec 012, D-126)
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
    tope_coste_estilo: float = 0.50  # fase 5: la guía de estilo (una llamada)

    # Fase 5 · Lector de URL (Apify). Sin token no se lee ninguna URL; límite por usuaria y hora (RF-5.3j)
    apify_token: str = ""
    apify_timeout_s: float = 60.0
    limite_url_hora: int = 10

    # Simplificación S5 (RF-10.9): un solo presupuesto al día por usuaria, para todo lo que hace por ella.
    # PROVISIONAL (RF-10.9d): la cifra definitiva sale del estudio de costes.
    presupuesto_diario_usd: float = 1.0  # USD por usuaria y día natural (Madrid)

    # Fase 8 · puntuar sin botón (RF-8.5)
    intervalo_recomendar_min: int = 60  # entre dos puntuaciones al abrir Recomendadas
    tope_coste_puntuar_una: float = 0.05  # USD por oferta suelta

    # Fase 3: topes de construcción (USD); el de uso real se fija al medir el coste, antes de usuarias
    tope_coste_candidatura: float = 1.00

    # Fase 4 · Límites de ritmo por minuto (RF-4.6d): login por IP; CV y candidaturas por usuaria
    limite_login_por_minuto: int = 20
    limite_cv_por_minuto: int = 10
    limite_candidaturas_por_minuto: int = 10

    # Simplificación S2 (RF-10.3d): con `true` se usa un CV base si existe; por defecto se parte del maestro
    horma_cv_base_respaldo: bool = False

    # Simplificación S5 (RF-10.10): una sola llamada (`analizador-oferta`) en vez de tres por oferta.
    # Evals reales del 21-nov con el agente nuevo: `ofertas` 8 de 8 pasadas y `red-teaming` sin fallos nuevos.
    # `false` vuelve a las tres llamadas de antes (RF-10.10b).
    horma_oferta_un_agente: bool = True

    # Fase 4: implementación del flujo `candidatura` ("plain" o "langgraph")
    horma_flow_impl: str = "langgraph"

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
