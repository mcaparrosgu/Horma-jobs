"""Único lugar donde se escribe SQL sobre ofertas y su origen."""
import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from horma.schemas.oferta import OfertaExtraida


def crear(s: Session, usuaria_id: int, texto: str) -> int:
    return s.execute(text("insert into ofertas (usuaria_id, texto_crudo) values (:u, :t) "
                          "returning id"), {"u": usuaria_id, "t": texto}).scalar_one()


def texto_de(s: Session, oferta_id: int) -> str:
    return s.execute(text("select texto_crudo from ofertas where id=:i"),
                     {"i": oferta_id}).scalar_one()


def guardar_extraccion(s: Session, oferta_id: int, usuaria_id: int, o: OfertaExtraida,
                       origenes: list[tuple[str, str]]) -> None:
    sal = o.salario
    s.execute(text(
        "update ofertas set estado='procesada', motivo_error=null, titulo=:titulo, "
        "empresa=:empresa, ubicacion=:ubicacion, remoto=:remoto, contrato=:contrato, "
        "salario_minimo=:smin, salario_maximo=:smax, salario_moneda=:smon, "
        "idiomas=cast(:idiomas as jsonb), requisitos=cast(:req as jsonb), "
        "fecha_publicacion=:fecha, url=:url, "
        "instrucciones_embebidas=cast(:instr as jsonb) where id=:id"),
        {"id": oferta_id, "titulo": o.titulo, "empresa": o.empresa, "ubicacion": o.ubicacion,
         "remoto": o.remoto, "contrato": o.contrato, "smin": sal.minimo if sal else None,
         "smax": sal.maximo if sal else None, "smon": sal.moneda if sal else None,
         "idiomas": json.dumps(o.idiomas, ensure_ascii=False),
         "req": json.dumps(o.requisitos, ensure_ascii=False), "fecha": o.fecha_publicacion,
         "url": str(o.url) if o.url else None,
         "instr": json.dumps(o.instrucciones_embebidas, ensure_ascii=False)})
    s.execute(text("delete from origen where entidad='oferta' and entidad_id=:i"), {"i": oferta_id})
    for campo, fragmento in origenes:
        s.execute(text("insert into origen (usuaria_id, entidad, entidad_id, campo, fragmento) "
                       "values (:u, 'oferta', :i, :c, :f)"),
                  {"u": usuaria_id, "i": oferta_id, "c": campo, "f": fragmento})


def marcar_error(s: Session, oferta_id: int, motivo: str) -> None:
    s.execute(text("update ofertas set estado='error', motivo_error=:m where id=:i"),
              {"i": oferta_id, "m": motivo})


def listar(s: Session) -> list[dict]:
    """Las ofertas de la usuaria de la sesión (RLS filtra el resto)."""
    filas = s.execute(text(
        "select id, estado, motivo_error, titulo, empresa, ubicacion, remoto, contrato, "
        "salario_minimo, salario_maximo, salario_moneda, idiomas, fecha_publicacion, url, "
        "instrucciones_embebidas, creada_en from ofertas order by id desc")).mappings().all()
    return [dict(f) for f in filas]
