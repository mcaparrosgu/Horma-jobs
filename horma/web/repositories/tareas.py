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


def registrar_llamadas(s: Session, tarea_id: int, llamadas: list[Llamada]) -> None:
    for ll in llamadas:
        s.execute(text(
            "insert into llm_llamadas (tarea_id, agente, modelo, tokens_entrada, tokens_salida, "
            "coste, latencia_ms, resultado) values (:t, :a, :m, :ti, :to, :c, :l, :r)"),
            {"t": tarea_id, "a": ll.agente, "m": ll.modelo, "ti": ll.tokens_entrada,
             "to": ll.tokens_salida, "c": ll.coste, "l": ll.latencia_ms, "r": ll.resultado})


def actualizar(s: Session, tarea_id: int, estado: str, coste_extra: float = 0.0,
               motivo: str | None = None) -> None:
    s.execute(text("update tareas set estado=:e, coste_acumulado=coste_acumulado+:c, "
                   "motivo_error=:m where id=:i"),
              {"i": tarea_id, "e": estado, "c": coste_extra, "m": motivo})
