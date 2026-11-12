from typer.testing import CliRunner


def test_paquete_importable():
    import horma

    assert horma.__doc__


def test_consola_responde_a_help():
    from horma.cli import app

    r = CliRunner().invoke(app, ["--help"])
    assert r.exit_code == 0
    assert "agente" in r.output and "eval" in r.output
