"""Nombre → fábrica del flujo (la usan la consola, el worker y los evals)."""
from horma.flows import calificar_fuente, procesar_oferta

FLUJOS = {"procesar_oferta": procesar_oferta.crear, "calificar_fuente": calificar_fuente.crear}
# Clave del estado final donde cada flujo deja su resultado.
RESULTADO = {"procesar_oferta": "oferta", "calificar_fuente": "calificacion"}
