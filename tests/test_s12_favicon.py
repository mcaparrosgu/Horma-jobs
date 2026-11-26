"""El navegador pide /favicon.ico en la raíz: tiene que existir, sin sesión."""

from pathlib import Path

ICO = Path(__file__).parent.parent / "horma" / "web" / "static" / "iconos" / "favicon.ico"


def test_favicon_es_un_ico_y_se_sirve_en_la_raiz():
    assert ICO.read_bytes()[:4] == b"\x00\x00\x01\x00"
    main = (Path(__file__).parent.parent / "horma" / "web" / "main.py").read_text(encoding="utf-8")
    assert '@app.get("/favicon.ico"' in main
