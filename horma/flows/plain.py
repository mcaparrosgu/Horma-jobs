"""PlainFlow: recorre PASOS siguiendo ARISTAS en Python plano."""
from horma.flows.base import Decision, ErrorDePaso, Paso


class PlainFlow:
    def __init__(self, nombre: str, *, pasos: dict[str, Paso], aristas: dict[str, str | Decision],
                 inicio: str, finales: set[str]):
        for origen, destino in aristas.items():
            if origen not in pasos or (isinstance(destino, str) and destino not in pasos):
                raise ValueError(f"arista inválida en {nombre}: {origen} → {destino}")
        if inicio not in pasos or not finales <= set(pasos):
            raise ValueError(f"inicio o finales inválidos en {nombre}")
        self.nombre = nombre
        self.inicio = inicio
        self.finales = finales
        self._pasos = pasos
        self._aristas = aristas

    def pasos(self) -> list[str]:
        return list(self._pasos)

    def run_step(self, paso: str, estado: dict) -> dict:
        try:
            return self._pasos[paso](estado)
        except ErrorDePaso:
            raise
        except Exception as e:  # noqa: BLE001 - cualquier fallo se atribuye a su paso
            raise ErrorDePaso(paso, e) from e

    def siguiente(self, paso: str, estado: dict) -> str | None:
        if paso in self.finales or paso not in self._aristas:
            return None
        destino = self._aristas[paso]
        destino = destino if isinstance(destino, str) else destino(estado)
        if destino not in self._pasos:
            raise ErrorDePaso(paso, f"arista hacia un paso desconocido: {destino}")
        return destino

    def run(self, estado: dict, max_pasos: int = 50) -> dict:
        paso: str | None = self.inicio
        for _ in range(max_pasos):
            estado = self.run_step(paso, estado)
            paso = self.siguiente(paso, estado)
            if paso is None:
                return estado
        raise ErrorDePaso(paso or "?", f"más de {max_pasos} pasos: posible bucle")
