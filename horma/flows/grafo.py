"""LangGraphFlow (RF-4.1): los mismos pasos y aristas que PlainFlow, ejecutados con un grafo de LangGraph.

Es el único módulo que importa `langgraph` (contrato de import-linter). El checkpointer de Postgres se crea
fuera (`horma.web.checkpointer`) y se inyecta; sin checkpointer se usa uno en memoria. `run_step`,
`siguiente` y `pasos` son los de PlainFlow: la consola recorre las mismas funciones que el grafo."""
import copy
import uuid
from typing import Any, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, StateGraph

from horma.flows.base import Decision, ErrorDePaso, Paso
from horma.flows.plain import PlainFlow


class LangGraphFlow(PlainFlow):
    def __init__(self, nombre: str, *, pasos: dict[str, Paso], aristas: dict[str, str | Decision],
                 inicio: str, finales: set[str], claves: set[str] | frozenset[str],
                 pausas: set[str] | None = None, checkpointer: Any = None,
                 al_paso: Any = None):
        super().__init__(nombre, pasos=pasos, aristas=aristas, inicio=inicio, finales=finales,
                         pausas=pausas, al_paso=al_paso)
        self.checkpointer = checkpointer if checkpointer is not None else InMemorySaver()
        self.claves = frozenset(claves)
        self.ultimo_hilo: str | None = None
        # Sin reductores: cada nodo sobrescribe las claves que devuelve.
        estado = TypedDict(f"Estado_{nombre}", dict.fromkeys(claves, Any), total=False)  # type: ignore[misc]
        g = StateGraph(estado)
        for paso in self._pasos:
            g.add_node(paso, self._nodo(paso))
        g.set_entry_point(inicio)
        for paso in self._pasos:
            destino = self._aristas.get(paso)
            if paso in self.finales or destino is None:
                g.add_edge(paso, END)
            elif isinstance(destino, str):
                g.add_edge(paso, destino)
            else:
                posibles = getattr(destino, "destinos", None) or tuple(self._pasos)
                g.add_conditional_edges(paso, lambda e, _d=destino: _d(e), {p: p for p in posibles})
        self._grafo = g.compile(checkpointer=self.checkpointer, interrupt_before=sorted(self.pausas))

    def _nodo(self, paso: str):
        def nodo(e: dict) -> dict:
            # Copia profunda: los pasos mutan el estado y lo que viene del checkpoint no debe cambiar.
            return self.run_step(paso, copy.deepcopy(dict(e)))
        return nodo

    def _estado_actual(self, cfg: dict) -> dict:
        snap = self._grafo.get_state(cfg)
        estado = dict(snap.values)
        if self.pausas:
            estado["en_pausa"] = snap.next[0] if snap.next else None
        return estado

    def run(self, estado: dict, max_pasos: int = 50, *, hilo: str | None = None) -> dict:
        """Corre desde el inicio hasta un final o hasta la pausa. Con un `hilo` que ya existía, empieza
        de cero. Sin `hilo` usa uno efímero (`ultimo_hilo`)."""
        desconocidas = sorted(set(estado) - self.claves)
        if desconocidas:  # LangGraph las descartaría en silencio
            raise ErrorDePaso(self.nombre, f"claves de entrada no declaradas: {', '.join(desconocidas)}")
        hilo = hilo or f"efimero-{uuid.uuid4().hex}"
        self.ultimo_hilo = hilo
        self.checkpointer.delete_thread(hilo)
        cfg = {"configurable": {"thread_id": hilo}, "recursion_limit": max_pasos}
        try:
            self._grafo.invoke({k: v for k, v in estado.items() if k != "en_pausa"}, cfg)
        except ErrorDePaso:
            raise
        except Exception as e:  # noqa: BLE001 - un fallo del grafo se atribuye al flujo
            raise ErrorDePaso(self.nombre, e) from e
        return self._estado_actual(cfg)

    def reanudar(self, hilo: str, cambios: dict, estado: dict | None = None,
                 max_pasos: int = 50) -> dict:
        """Lee el hilo del checkpointer, aplica `cambios` y sigue desde el paso en pausa. Ignora `estado`."""
        if not self.pausas:
            raise ErrorDePaso(self.nombre, "este flujo no tiene pausas")
        cfg = {"configurable": {"thread_id": hilo}, "recursion_limit": max_pasos}
        snap = self._grafo.get_state(cfg)
        if not snap.next or snap.next[0] not in self.pausas:
            raise ErrorDePaso(self.nombre, "no hay nada en pausa que reanudar en ese hilo")
        try:
            if cambios:
                self._grafo.update_state(cfg, cambios)
            self._grafo.invoke(None, cfg)
        except ErrorDePaso:
            raise
        except Exception as e:  # noqa: BLE001
            raise ErrorDePaso(self.nombre, e) from e
        return self._estado_actual(cfg)
