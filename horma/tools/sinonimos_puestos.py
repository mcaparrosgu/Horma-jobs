"""Otras formas de anunciar un puesto (RF-12.4c, D-061). Tabla fija; las del modelo llegan aparte.

No se amplía mirando pares de medida: si no, la cifra deja de decir nada."""
from horma.tools.normalizar_titulo import canonico

TABLA = [
    ["camarero", "waiter", "mesero"], ["camarero de barra", "bartender", "barman"],
    ["dependiente", "sales assistant", "shop assistant", "vendedor de tienda"], ["cajero", "cashier"],
    ["ayudante de cocina", "kitchen porter", "pinche"], ["cocinero", "chef"],
    ["mozo de almacén", "warehouse operative", "peón de logística", "personal de almacén"],
    ["carretillero", "forklift driver"], ["repartidor", "delivery driver", "mensajero"],
    ["conductor de camión", "conductor de tráiler", "camionero", "hgv driver"],
    ["recepcionista", "receptionist", "front desk agent", "guest services agent"],
    ["auxiliar administrativo", "office clerk", "back office"],
    ["enfermero", "registered nurse", "nurse", "due"],
    ["auxiliar de geriatría", "gerocultor"], ["auxiliar de enfermería", "care assistant"],
    ["programador", "desarrollador", "developer", "software developer", "ingeniero de software"],
    ["programador web", "web developer", "desarrollador web"], ["data scientist", "científico de datos"],
    ["data analyst", "analista de datos"],
    ["técnico de selección", "recruiter", "reclutador", "talent acquisition"],
    ["responsable de recursos humanos", "hr manager"],
    ["community manager", "responsable de redes sociales"], ["content writer", "redactor de contenidos"],
    ["fotógrafo", "photographer"], ["profesor de inglés", "english teacher"],
    ["abogado", "lawyer", "letrado"],
    ["electricista", "electrician"], ["técnico de climatización", "frigorista"],
    ["técnico de soporte informático", "help desk"], ["contable", "accountant"],
    ["agente de atención al cliente", "teleoperador"], ["personal de limpieza", "cleaner", "limpiador"],
    ["jefe de cocina", "head chef"], ["jefe de sala", "maître"], ["promotor de ventas", "azafata de tienda"],
]

_INDICE: dict[str, list[str]] = {}
for _grupo in TABLA:
    for _forma in _grupo:
        _INDICE.setdefault(canonico(_forma), []).extend(_grupo)


def otras_formas(puesto: str, del_modelo: list[str] | tuple[str, ...] = ()) -> list[str]:
    """El puesto y, detrás, sus otras formas de la tabla y del modelo, sin repetir."""
    return list(dict.fromkeys([puesto, *_INDICE.get(canonico(puesto), []), *del_modelo]))
