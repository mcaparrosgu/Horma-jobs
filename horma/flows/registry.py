"""Nombre → fábrica del flujo (la usan la consola, el worker y los evals)."""
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
