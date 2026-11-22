"""Construye la consulta SQL del filtro duro y el pre-orden de la recomendación (RF-2.11, RF-1.9).

Código puro: NO ejecuta nada ni abre la base de datos; devuelve el texto SQL y sus parámetros y el
repositorio los ejecuta (frontera «solo la API y el worker leen Postgres»).

Reglas:
- Solo ofertas procesadas y recomendables (ni fantasma ni fraude), SALVO las propias de la usuaria
  (`usuaria_id` con valor; la RLS deja ver solo las suyas): a esas no se les exige `recomendable`, y
  la usuaria decide qué hacer con ellas (RF-5.3e, P17). Los filtros de Preferencias valen igual para
  las propias y para las del catálogo (RF-7.1f).
- Solo se descarta una oferta si el dato EXISTE y no coincide con el filtro. Si falta (o no es
  comparable), pasa (P2, P17). Un grupo de preferencias vacío no filtra.
  EXCEPCIÓN (RF-7.1c): con «solo remoto», solo pasan las de `modalidad = 'remoto'`;
  sin dato, no pasan.
- Una oferta remota o sin país fijo pasa el filtro de país; si la usuaria marca «REMOTO», también
  pasan las ofertas con `remoto = true` de cualquier país.
- El sueldo mínimo es en euros brutos al año y se compara con el máximo (o el mínimo si no hay
  máximo) de la oferta; `sueldo_comparable` dice si la oferta traía un sueldo que se pudo comparar.
- Puestos y excluidos (RF-9.3c, 9.3d): el título normalizado de la oferta casa con un puesto si lo contiene
  como frase de palabras completas. Con familias o puestos, la oferta pasa si cumple la familia O el título
  casa con un puesto (una oferta de otra familia entra por su título). Un término excluido en el título
  saca la oferta. Sin familias ni puestos no se filtra por puesto.
- Orden «compatibles»: primero la coincidencia de taxonomía con el perfil y con los puestos marcados,
  después la fecha. Orden «recientes»: solo la fecha. No se descarta nada por el orden."""
from dataclasses import dataclass, field

from horma.schemas.preferencias import Preferencias
from horma.schemas.taxonomia import Taxonomia
from horma.tools.normalizar_titulo import normalizar_titulo, variantes_genero


@dataclass(frozen=True)
class Consulta:
    sql: str
    parametros: dict = field(default_factory=dict)


def buscar_ofertas(prefs: Preferencias, taxonomia: Taxonomia | None = None, *,
                   excluir_ids: list[int] | tuple[int, ...] = (), limite: int | None = None) -> Consulta:
    condiciones: list[str] = []
    p: dict = {}

    def lista(nombre: str, valores: list) -> str:
        p[nombre] = list(valores)
        return f"CAST(:{nombre} AS text[])"

    def frases(nombre: str, terminos: list[str]) -> str | None:
        normalizados = [n for n in dict.fromkeys(normalizar_titulo(t) for t in terminos) if n]
        if not normalizados:
            return None
        p[nombre] = [f"% {v} %" for n in normalizados for v in variantes_genero(n)]
        return f"((' ' || coalesce(titulo_norm, '') || ' ') LIKE ANY(CAST(:{nombre} AS text[])))"

    casa_puesto = frases("puestos", prefs.puestos)
    por_puesto = []
    if prefs.familias:
        por_puesto.append(f"(familia IS NULL OR familia = ANY({lista('familias', prefs.familias)}))")
    if casa_puesto:
        por_puesto.append(casa_puesto)
    if por_puesto:
        condiciones.append("(" + " OR ".join(por_puesto) + ")")
    casa_excluido = frases("excluidos", prefs.excluidos)
    if casa_excluido:
        condiciones.append(f"NOT {casa_excluido}")
    if prefs.sectores:
        condiciones.append(f"(sector IS NULL OR sector = ANY({lista('sectores', prefs.sectores)}))")
    if prefs.niveles:
        condiciones.append("(nivel IS NULL OR nivel = 'sin_especificar' OR "
                           f"nivel = ANY({lista('niveles', prefs.niveles)}))")
    if prefs.contratos:
        condiciones.append("(tipo_contrato IS NULL OR "
                           f"tipo_contrato = ANY({lista('contratos', prefs.contratos)}))")
    if prefs.paises:
        extra = " OR remoto IS TRUE" if "REMOTO" in prefs.paises else ""
        condiciones.append("(pais IS NULL OR pais = 'REMOTO' OR "
                           f"pais = ANY({lista('paises', prefs.paises)}){extra})")
    if prefs.idiomas:
        condiciones.append("(idiomas_norm IS NULL OR cardinality(idiomas_norm) = 0 OR "
                           f"idiomas_norm && {lista('idiomas', prefs.idiomas)})")
    if prefs.solo_salario:
        condiciones.append("salario_publicado IS NOT FALSE")
    if prefs.sueldo_minimo is not None:
        p["sueldo_minimo"] = prefs.sueldo_minimo
        condiciones.append("((salario_anual_eur_min IS NULL AND salario_anual_eur_max IS NULL) OR "
                           "coalesce(salario_anual_eur_max, salario_anual_eur_min) >= :sueldo_minimo)")
    if prefs.solo_remoto:
        condiciones.append("modalidad = 'remoto'")
    # Los filtros valen igual para las propias y las del catálogo (RF-7.1f). Solo «recomendable» (ni fantasma
    # ni fraude) se les perdona: la usuaria ve sus ofertas con el aviso del auditor (RF-5.3e).
    donde = ["estado = 'procesada'", "(usuaria_id IS NOT NULL OR recomendable)", *condiciones]
    if excluir_ids:
        p["excluir_ids"] = list(excluir_ids)
        donde.append("NOT (id = ANY(CAST(:excluir_ids AS int[])))")

    orden = ["creada_en DESC", "id DESC"]
    if prefs.orden == "compatibles":
        puntos = []
        if taxonomia is not None:
            p["t_familia"], p["t_sector"], p["t_nivel"] = taxonomia.familia, taxonomia.sector, taxonomia.nivel
            puntos += ["(CASE WHEN familia = :t_familia THEN 3 ELSE 0 END)",
                       "(CASE WHEN sector = :t_sector THEN 2 ELSE 0 END)",
                       "(CASE WHEN nivel = :t_nivel THEN 1 ELSE 0 END)"]
        if casa_puesto:
            puntos.append(f"(CASE WHEN {casa_puesto} THEN 2 ELSE 0 END)")
        if prefs.familias:
            puntos.append("(CASE WHEN familia = ANY(CAST(:familias AS text[])) THEN 2 ELSE 0 END)")
        if puntos:
            orden.insert(0, "(" + " + ".join(puntos) + ") DESC")

    sql = ("SELECT id, (salario_anual_eur_min IS NOT NULL OR salario_anual_eur_max IS NOT NULL) "
           "AS sueldo_comparable FROM ofertas WHERE " + " AND ".join(donde)
           + " ORDER BY " + ", ".join(orden))
    if limite is not None:
        p["limite"] = limite
        sql += " LIMIT :limite"
    return Consulta(sql=sql, parametros=p)
