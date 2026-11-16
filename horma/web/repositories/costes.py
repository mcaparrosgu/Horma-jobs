"""Agregados de coste y errores de `llm_llamadas` para `/costes` (RF-4.7). Solo cifras: nunca ids de
usuaria ni de tarea, ni texto."""
from sqlalchemy import text
from sqlalchemy.orm import Session

DIA = "(creada_en at time zone 'Europe/Madrid')::date"
CIFRAS = ("count(*) as llamadas, coalesce(sum(coste), 0) as coste, "
          "coalesce(sum(tokens_entrada), 0) as tokens_entrada, "
          "coalesce(sum(tokens_salida), 0) as tokens_salida, "
          "coalesce(round(avg(latencia_ms)), 0) as latencia_media_ms, "
          "coalesce(avg((resultado <> 'ok')::int), 0) as tasa_errores")


def _filas(s: Session, sql: str, **parametros) -> list[dict]:
    resultado = []
    for f in s.execute(text(sql), parametros).mappings().all():
        resultado.append({k: (float(v) if hasattr(v, "as_tuple") else
                              v.isoformat() if hasattr(v, "isoformat") else v) for k, v in f.items()})
    return resultado


def por_dia(s: Session, dias: int = 30) -> list[dict]:
    return _filas(s, f"select {DIA} as dia, {CIFRAS} from llm_llamadas "
                     f"where creada_en >= now() - make_interval(days => :d) group by 1 order by 1 desc",
                  d=dias)


def por_agente(s: Session, dias: int = 30) -> list[dict]:
    return _filas(s, f"select agente, {CIFRAS} from llm_llamadas "
                     "where creada_en >= now() - make_interval(days => :d) group by 1 order by coste desc",
                  d=dias)


def por_modelo(s: Session, dias: int = 30) -> list[dict]:
    return _filas(s, f"select modelo, {CIFRAS} from llm_llamadas "
                     "where creada_en >= now() - make_interval(days => :d) group by 1 order by coste desc",
                  d=dias)


def tareas_en_error(s: Session) -> list[dict]:
    return [{"tipo": t, "n": n} for t, n in s.execute(text("select tipo, n from tareas_en_error_por_tipo()"))]


def alertas_recientes(s: Session, dias: int = 7) -> list[dict]:
    return _filas(s, "select tipo, valor, umbral, creada_en, correo_enviado from alertas "
                     "where creada_en >= now() - make_interval(days => :d) order by creada_en desc",
                  d=dias)
