"""Alertas de gasto y de errores (RF-4.7b): se crean, se escriben en el log y se envían por correo, como
mucho una por tipo y día. Ni la alerta ni el correo llevan datos personales: solo tipo, valor y umbral."""
import logging
import smtplib
from collections.abc import Callable
from datetime import datetime
from email.message import EmailMessage
from zoneinfo import ZoneInfo

from sqlalchemy import Engine, text

from horma.config import Ajustes
from horma.web.db import sesion_sistema

log = logging.getLogger("horma.alertas")
ZONA = ZoneInfo("Europe/Madrid")
Enviar = Callable[[str, str, Ajustes], None]


def correo_configurado(a: Ajustes) -> bool:
    return bool(a.smtp_host and a.alertas_correo)


def _formato(tipo: str, valor: float, umbral: float) -> tuple[str, str]:
    if tipo == "gasto_dia":
        return "Gasto del día", f"{valor:.4f} USD (umbral {umbral:.4f} USD)"
    return "Tasa de errores", f"{valor * 100:.1f} % (umbral {umbral * 100:.1f} %)"


def _texto_correo(tipo: str, valor: float, umbral: float, a: Ajustes) -> tuple[str, str]:
    nombre, cifras = _formato(tipo, valor, umbral)
    enlace = f"https://{a.horma_dominio}/costes" if a.horma_dominio else "/costes en tu instalación de Horma"
    return f"Horma · alerta: {nombre}", f"{nombre}: {cifras}.\nDetalle: {enlace}\n"


def enviar_correo(asunto: str, cuerpo: str, a: Ajustes) -> None:
    """Correo por SMTP con STARTTLS. Texto fijo: sin datos de usuarias."""
    msg = EmailMessage()
    msg["Subject"], msg["To"] = asunto, a.alertas_correo
    msg["From"] = a.smtp_usuario or a.alertas_correo
    msg.set_content(cuerpo)
    with smtplib.SMTP(a.smtp_host, a.smtp_port, timeout=15) as smtp:
        smtp.starttls()
        if a.smtp_usuario:
            smtp.login(a.smtp_usuario, a.smtp_password)
        smtp.send_message(msg)


def _gasto_del_dia(s, dia) -> float:
    return float(s.execute(text(
        "select coalesce(sum(coste), 0) from llm_llamadas "
        "where (creada_en at time zone 'Europe/Madrid')::date = :d"), {"d": dia}).scalar_one())


def _errores_ultima_hora(s, ahora: datetime) -> tuple[int, float]:
    n, tasa = s.execute(text(
        "select count(*), coalesce(avg((resultado <> 'ok')::int), 0) from llm_llamadas "
        "where creada_en >= :a - interval '1 hour' and creada_en <= :a"), {"a": ahora}).one()
    return n, float(tasa)


def _ya_hay(s, tipo: str, dia) -> bool:
    return s.execute(text(
        "select 1 from alertas where tipo = :t and (creada_en at time zone 'Europe/Madrid')::date = :d"),
        {"t": tipo, "d": dia}).first() is not None


def comprobar(engine: Engine, a: Ajustes, ahora: datetime | None = None,
              enviar: Enviar = enviar_correo) -> list[dict]:
    """Crea las alertas que toquen y devuelve las nuevas (tipo, valor, umbral, correo_enviado)."""
    ahora = (ahora or datetime.now(ZONA)).astimezone(ZONA)
    dia = ahora.date()
    nuevas: list[dict] = []
    with sesion_sistema(engine) as s:
        candidatas: list[tuple[str, float, float]] = []
        gasto = _gasto_del_dia(s, dia)
        if gasto > a.alerta_gasto_dia_usd:
            candidatas.append(("gasto_dia", gasto, a.alerta_gasto_dia_usd))
        n, tasa = _errores_ultima_hora(s, ahora)
        if n >= a.alerta_min_llamadas and tasa > a.alerta_tasa_errores:
            candidatas.append(("tasa_errores", tasa, a.alerta_tasa_errores))
        for tipo, valor, umbral in candidatas:
            if _ya_hay(s, tipo, dia):
                continue
            nombre, cifras = _formato(tipo, valor, umbral)
            log.warning("ALERTA %s: %s", nombre, cifras)
            enviado = False
            if correo_configurado(a):
                try:
                    enviar(*_texto_correo(tipo, valor, umbral, a), a)
                    enviado = True
                except Exception as e:  # noqa: BLE001 - un fallo de correo no debe parar el worker
                    log.error("No se pudo enviar el correo de alerta (%s)", type(e).__name__)
            s.execute(text(
                "insert into alertas (tipo, valor, umbral, creada_en, correo_enviado) "
                "values (:t, :v, :u, :c, :e)"),
                {"t": tipo, "v": valor, "u": umbral, "c": ahora, "e": enviado})
            nuevas.append({"tipo": tipo, "valor": valor, "umbral": umbral, "correo_enviado": enviado})
    return nuevas
