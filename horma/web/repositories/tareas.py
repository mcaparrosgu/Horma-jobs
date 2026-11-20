from sqlalchemy import text
from sqlalchemy.orm import Session

from horma.llm.metricas import Llamada


def encolar(s: Session, usuaria_id: int, tipo: str, entidad_id: int, tope_coste: float,
            tope_reintentos: int) -> int:
    """La carga son ids, nunca texto."""
    return s.execute(text(
        "insert into tareas (usuaria_id, tipo, entidad_id, tope_coste, tope_reintentos) "
        "values (:u, :t, :e, :c, :r) returning id"),
        {"u": usuaria_id, "t": tipo, "e": entidad_id, "c": tope_coste, "r": tope_reintentos}
    ).scalar_one()


def sin_terminar(s: Session, tipo: str, entidad_id: int) -> bool:
    """¿Hay ya una tarea de este tipo y entidad pendiente o en curso? (evita encolar dos veces)"""
    return s.execute(text("select 1 from tareas where tipo = :t and entidad_id = :e "
                          "and estado in ('pendiente', 'en_curso')"),
                     {"t": tipo, "e": entidad_id}).first() is not None


def pendiente(s: Session, tipo: str, entidad_id: int) -> bool:
    """¿Hay una tarea de este tipo y entidad por empezar? Una en curso no cuenta: ya cargó sus datos."""
    return s.execute(text("select 1 from tareas where tipo = :t and entidad_id = :e "
                          "and estado = 'pendiente'"), {"t": tipo, "e": entidad_id}).first() is not None


def registrar_llamadas(s: Session, tarea_id: int, llamadas: list[Llamada]) -> None:
    for ll in llamadas:
        s.execute(text(
            "insert into llm_llamadas (tarea_id, agente, modelo, tokens_entrada, tokens_salida, "
            "coste, latencia_ms, resultado, senales_entrada) "
            "values (:t, :a, :m, :ti, :to, :c, :l, :r, :s)"),
            {"t": tarea_id, "a": ll.agente, "m": ll.modelo, "ti": ll.tokens_entrada,
             "to": ll.tokens_salida, "c": ll.coste, "l": ll.latencia_ms, "r": ll.resultado,
             "s": list(ll.senales_entrada)})


def actualizar(s: Session, tarea_id: int, estado: str, coste_extra: float = 0.0,
               motivo: str | None = None) -> None:
    s.execute(text("update tareas set estado=:e, coste_acumulado=coste_acumulado+:c, "
                   "motivo_error=:m, actualizada_en=now(), "
                   "progreso = case when :e = 'hecha' then 100 else progreso end where id=:i"),
              {"i": tarea_id, "e": estado, "c": coste_extra, "m": motivo})


# --- Fase 8: topes del día y avance (RF-8.5, RF-8.7) ---------------------------------------------------
TIPOS_GASTO = ("recomendar", "puntuar_propias", "puntuar_una")
_HOY = ("(creada_en at time zone 'Europe/Madrid')::date = (now() at time zone 'Europe/Madrid')::date")


def gasto_hoy(s: Session, usuaria_id: int, tipos: tuple[str, ...] = TIPOS_GASTO) -> float:
    """USD gastados hoy (el día se corta a medianoche de Madrid) en las tareas que puntúan."""
    return float(s.execute(text(
        f"select coalesce(sum(coste_acumulado), 0) from tareas where usuaria_id = :u "
        f"and tipo = any(:t) and {_HOY}"), {"u": usuaria_id, "t": list(tipos)}).scalar_one())


def ultima(s: Session, usuaria_id: int, tipo: str) -> dict | None:
    fila = s.execute(text("select id, estado, creada_en, extract(epoch from (now() - creada_en)) as hace_s "
                          "from tareas where usuaria_id = :u and tipo = :t "
                          "order by creada_en desc, id desc limit 1"),
                     {"u": usuaria_id, "t": tipo}).mappings().first()
    return dict(fila) if fila else None


def sueltas_hoy(s: Session, usuaria_id: int) -> int:
    """Cuántas «Puntuar ahora» ha pedido hoy."""
    return s.execute(text(f"select count(*) from tareas where usuaria_id = :u and tipo = 'puntuar_una' "
                          f"and {_HOY}"), {"u": usuaria_id}).scalar_one()


def activas(s: Session, usuaria_id: int, tipos: list[str] | None = None) -> list[dict]:
    """Las tareas pendientes o en curso de la usuaria, con su avance."""
    filas = s.execute(text(
        "select id, tipo, entidad_id, estado, progreso, motivo_error as motivo from tareas "
        "where usuaria_id = :u and estado in ('pendiente', 'en_curso') "
        "and (cast(:t as text[]) is null or tipo = any(cast(:t as text[]))) order by id"),
        {"u": usuaria_id, "t": tipos}).mappings().all()
    return [dict(f) for f in filas]


def una(s: Session, tarea_id: int) -> dict | None:
    fila = s.execute(text("select id, tipo, entidad_id, estado, progreso, motivo_error as motivo "
                          "from tareas where id = :i"), {"i": tarea_id}).mappings().first()
    return dict(fila) if fila else None


def avanzar(s: Session, tarea_id: int, progreso: int) -> None:
    """El avance nunca baja (RF-8.7)."""
    s.execute(text("update tareas set progreso = greatest(progreso, :p), actualizada_en = now() "
                   "where id = :i"), {"i": tarea_id, "p": max(0, min(100, int(progreso)))})
