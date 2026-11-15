"""Compara dos versiones de un texto línea a línea (RF-3.8d). Código puro, con `difflib`.

Devuelve las líneas en orden con su marca: `igual`, `añadida` (está en la nueva) o `quitada` (estaba
en la anterior). Lo añadido y lo quitado no se guarda: se calcula al mostrar el historial."""
import difflib


def comparar_versiones(anterior: str, siguiente: str) -> list[dict[str, str]]:
    resultado = []
    for linea in difflib.ndiff(anterior.splitlines(), siguiente.splitlines()):
        codigo, texto = linea[:2], linea[2:]
        if codigo == "? ":  # pista de ndiff sobre los cambios dentro de la línea, no es una línea
            continue
        marca = {"  ": "igual", "+ ": "añadida", "- ": "quitada"}[codigo]
        resultado.append({"linea": texto, "marca": marca})
    return resultado
