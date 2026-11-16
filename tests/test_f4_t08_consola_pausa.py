"""Fase 4 · T08: `flujo correr candidatura` se para en la pausa y con `--aprobar` sigue con `entregar` y
guarda los dos PDF en la carpeta de la traza (RF-4.1b, RF-4.3)."""
import pytest
from test_f4_t04_implementacion import _consola

from horma import config
from horma.flows.registry import IMPLEMENTACIONES


@pytest.fixture(params=IMPLEMENTACIONES)
def impl(request, monkeypatch):
    monkeypatch.setenv("HORMA_FLOW_IMPL", request.param)
    config.ajustes.cache_clear()
    yield request.param
    config.ajustes.cache_clear()


def test_sin_aprobar_termina_en_pausa_y_no_hay_pdf(tmp_path, impl):
    r = _consola(tmp_path, "--traza", str(tmp_path / "t"))
    assert r.exit_code == 0, r.output
    assert "En pausa: falta la aprobación" in r.output
    assert not list((tmp_path / "t").glob("*.pdf"))


def test_con_aprobar_sigue_con_entregar_y_guarda_los_dos_pdf(tmp_path, impl):
    r = _consola(tmp_path, "--aprobar", "--traza", str(tmp_path / "t"))
    assert r.exit_code == 0, r.output
    assert "En pausa" not in r.output and "entregar" in r.output
    carpeta = tmp_path / "t"
    assert (carpeta / "cv.pdf").read_bytes().startswith(b"%PDF")
    assert (carpeta / "carta.pdf").read_bytes().startswith(b"%PDF")
    assert sorted(p.name for p in carpeta.glob("*.json"))[-1].endswith("entregar.json")


def test_aprobar_sin_traza_avisa_de_que_no_guarda_los_pdf(tmp_path, impl):
    r = _consola(tmp_path, "--aprobar")
    assert r.exit_code == 0, r.output
    assert "--traza" in r.output


def test_aprobar_en_un_flujo_sin_pausa_da_error(tmp_path):
    from typer.testing import CliRunner

    from horma.cli import app as cli

    entrada = tmp_path / "e.md"
    entrada.write_text("texto", encoding="utf-8")
    resp = tmp_path / "r.json"
    resp.write_text("[]", encoding="utf-8")
    r = CliRunner().invoke(cli, ["flujo", "correr", "procesar_oferta", "--entrada", str(entrada),
                                 "--aprobar", "--simulado", "--respuestas", str(resp)])
    assert r.exit_code == 2 and "pausa" in r.output
