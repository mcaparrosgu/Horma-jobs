"""S8 · T67: el eval simulado informa 0 USD (sin modelo real no hay gasto)."""
import shutil

from horma.evals import correr_set


def test_el_eval_simulado_da_coste_cero(tmp_path):
    raiz = tmp_path / "evals"
    shutil.copytree("evals/ofertas", raiz / "ofertas")
    res = correr_set("ofertas", raiz=raiz, simulado=True)
    assert res["simulado"] is True and res["coste"] == 0
