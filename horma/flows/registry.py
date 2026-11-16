"""Nombre → fábrica del flujo (la usan la consola, el worker y los evals)."""
from horma.config import ajustes
from horma.flows import (
    calificar_fuente,
    candidatura,
    clasificar_perfil,
    clasificar_respuesta,
    generar_cv_base,
    perfilar,
    procesar_oferta,
    recomendar,
)

FLUJOS = {"procesar_oferta": procesar_oferta.crear, "calificar_fuente": calificar_fuente.crear,
          "perfilar": perfilar.crear, "clasificar_perfil": clasificar_perfil.crear,
          "generar_cv_base": generar_cv_base.crear, "recomendar": recomendar.crear,
          "candidatura": candidatura.crear, "clasificar_respuesta": clasificar_respuesta.crear}
# Clave del estado final donde cada flujo deja su resultado.
RESULTADO = {"procesar_oferta": "oferta", "calificar_fuente": "calificacion", "perfilar": "perfil",
             "clasificar_perfil": "taxonomia", "generar_cv_base": "cv_base",
             "recomendar": "recomendaciones", "candidatura": "preparacion",
             "clasificar_respuesta": "propuesta"}

IMPLEMENTACIONES = ("plain", "langgraph")
# Fase 4 (P1): LangGraph solo para `candidatura`; los demás flujos siguen siendo lineales.
FLUJOS_LANGGRAPH = {"candidatura": candidatura.crear_grafo}


def crear_flujo(nombre: str, impl: str | None = None, **deps):
    """Construye el flujo `nombre` con la implementación pedida (por defecto, `HORMA_FLOW_IMPL`)."""
    impl = impl or ajustes().horma_flow_impl
    if impl not in IMPLEMENTACIONES:
        raise ValueError(f"Implementación de flujos desconocida: «{impl}». "
                         f"Valores válidos: {', '.join(IMPLEMENTACIONES)}.")
    fabrica = FLUJOS_LANGGRAPH.get(nombre) if impl == "langgraph" else None
    return (fabrica or FLUJOS[nombre])(**deps)
