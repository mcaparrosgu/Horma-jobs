"""Spec 012, T21 (D-126): con las marcas por requisito, puntuar una tanda pasa de 60 s; el límite es 240 s."""
from horma.config import Ajustes


def test_la_espera_del_modelo_da_para_una_tanda_completa():
    assert Ajustes.model_fields["llm_timeout_s"].default == 240.0
