"""Avisos del perfil por reglas, sin modelo (RF-9.2). Código puro.

Cada aviso lleva una `clave` estable y una `huella` de lo que lo causa: si ella lo da por visto con esa
huella no vuelve, y si la causa cambia (otra descripción, otro CV) vuelve (RF-9.2c)."""
import hashlib
import re
from dataclasses import dataclass

from horma.schemas.perfil import Perfil
from horma.tools.detectar_huecos import Hueco
from horma.tools.visibilidad_cv import normalizar

PALABRAS_CV_LARGO = 1000
_CORREO = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_TELEFONO = re.compile(r"(?:\+?\d[\s.\-]?){9,}")


@dataclass(frozen=True)
class Aviso:
    clave: str
    huella: str
    texto: str
    seccion: str  # dónde se corrige: «cv», «resumen», «experiencia» o «cv_fuente»


def _hash(*partes: str) -> str:
    return hashlib.sha1("\u241f".join(partes).encode()).hexdigest()[:10]


def _con_cifras(texto: str) -> bool:
    return bool(re.search(r"\d|%", texto))


def avisos_perfil(perfil: Perfil, cv_maestro: str = "",
                  textos_cv: dict[int, str] | None = None) -> list[Aviso]:
    avisos: list[Aviso] = []
    palabras = len(cv_maestro.split())
    if palabras > PALABRAS_CV_LARGO:
        avisos.append(Aviso("largo", _hash(str(round(palabras, -2))),
                            "Tu CV maestro tiene más de 1.000 palabras; un CV de selección "
                            "suele quedarse por debajo.", "cv"))
    if perfil.resumen is None:
        avisos.append(Aviso("sin_resumen", _hash("sin_resumen"),
                            "Tu perfil no tiene resumen: tres líneas sobre quién eres y qué buscas.",
                            "resumen"))
    for x in perfil.experiencias:
        nombre = " · ".join(p for p in (x.puesto, x.empresa) if p)
        clave = f"{normalizar(x.puesto)}|{normalizar(x.empresa)}"
        descripcion = (x.descripcion or "").strip()
        if not descripcion:
            avisos.append(Aviso(f"sin_descripcion:{clave}", _hash(clave),
                                f"«{nombre}» no tiene descripción: cuenta qué hacías.", "experiencia"))
        elif not _con_cifras(descripcion):
            avisos.append(Aviso(f"sin_cifras:{clave}", _hash(descripcion),
                                f"«{nombre}» no tiene ninguna cifra: un dato concreto (clientes, "
                                "porcentajes, tamaño del equipo) convence más.", "experiencia"))
    for cv_id, texto in (textos_cv or {}).items():
        if not (_CORREO.search(texto) or _TELEFONO.search(texto)):
            avisos.append(Aviso(f"sin_contacto:{cv_id}", _hash(texto),
                                "Uno de tus CV no tiene correo ni teléfono: sin ellos no pueden "
                                "contactarte.", "cv_fuente"))
    return avisos


def aviso_de_hueco(h: Hueco) -> Aviso:
    """Un hueco se da por visto igual que un aviso; su huella es su propia clave (sus fechas)."""
    return Aviso(h.clave, _hash(h.clave), h.texto, "hueco")
