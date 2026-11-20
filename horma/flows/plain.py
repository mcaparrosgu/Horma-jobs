"""PlainFlow: recorre PASOS siguiendo ARISTAS en Python plano."""
from collections.abc import Callable

from horma.flows.base import Decision, ErrorDePaso, Paso


class PlainFlow:
    def __init__(self, nombre: str, *, pasos: dict[str, Paso], aristas: dict[str, str | Decision],
                 inicio: str, finales: set[str], pausas: set[str] | None = None,
                 al_paso: Callable[[str], None] | None = None):
        for origen, destino in aristas.items():
            if origen not in pasos or (isinstance(destino, str) and destino not in pasos):
                raise ValueError(f"arista inválida en {nombre}: {origen} → {destino}")
        if inicio not in pasos or not finales <= set(pasos):
            raise ValueError(f"inicio o finales inválidos en {nombre}")
        pausas = set(pausas or ())
        if not pausas <= set(pasos):
            raise ValueError(f"pausas inválidas en {nombre}: {sorted(pausas - set(pasos))}")
        self.nombre = nombre
        self.inicio = inicio
        self.finales = finales
        self.pausas = pausas
        self._pasos = pasos
        self._aristas = aristas
        self.al_paso = al_paso  # se llama con el nombre de cada paso al terminarlo (avance, RF-8.7)

    def pasos(self) -> list[str]:
        return list(self._pasos)

    def run_step(self, paso: str, estado: dict) -> dict:
        try:
            nuevo = self._pasos[paso](estado)
        except ErrorDePaso:
            raise
        except Exception as e:  # noqa: BLE001 - cualquier fallo se atribuye a su paso
            raise ErrorDePaso(paso, e) from e
        if self.al_paso is not None:
            self.al_paso(paso)
        return nuevo

    def siguiente(self, paso: str, estado: dict) -> str | None:
        if paso in self.finales or paso not in self._aristas:
            return None
        destino = self._aristas[paso]
        destino = destino if isinstance(destino, str) else destino(estado)
        if destino not in self._pasos:
            raise ErrorDePaso(paso, f"arista hacia un paso desconocido: {destino}")
        return destino

    def _recorrer(self, paso: str | None, estado: dict, max_pasos: int) -> dict:
        for _ in range(max_pasos):
            if paso is None:
                if self.pausas:
                    estado["en_pausa"] = None
                return estado
            if paso in self.pausas:
                estado["en_pausa"] = paso  # se para antes de ejecutarlo
                return estado
            estado = self.run_step(paso, estado)
            paso = self.siguiente(paso, estado)
        raise ErrorDePaso(paso or "?", f"más de {max_pasos} pasos: posible bucle")

    def run(self, estado: dict, max_pasos: int = 50, *, hilo: str | None = None) -> dict:
        """Recorre hasta un paso final o hasta el paso anterior a una pausa (`en_pausa`). `hilo` no se usa:
        PlainFlow no guarda nada."""
        return self._recorrer(self.inicio, estado, max_pasos)

    def reanudar(self, hilo: str, cambios: dict, estado: dict | None = None,
                 max_pasos: int = 50) -> dict:
        """Sigue desde el paso en pausa del `estado` aplicando `cambios`. Sin pausa, es un error."""
        if not self.pausas:
            raise ErrorDePaso(self.nombre, "este flujo no tiene pausas")
        paso = (estado or {}).get("en_pausa")
        if paso not in self.pausas:
            raise ErrorDePaso(self.nombre, "no hay nada en pausa que reanudar")
        estado = {**estado, **cambios, "en_pausa": None}
        estado = self.run_step(paso, estado)
        return self._recorrer(self.siguiente(paso, estado), estado, max_pasos)
