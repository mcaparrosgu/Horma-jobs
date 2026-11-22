"""S7, T31: «Revisa esto» en tres grupos (RF-10.13)."""
import json
import subprocess
from pathlib import Path

from horma.schemas.candidatura import Aviso, aviso_de_error

ESTATICOS = Path(__file__).parent.parent / "horma" / "web" / "static"


def test_una_candidatura_antigua_sin_tipo_se_ve_en_revisa():
    a = Aviso.model_validate({"documento": "cv", "frase": None, "mensaje": "Algo"})
    assert a.tipo == "revisa"


def test_frase_sin_origen_y_dato_nuevo_son_dato_dudoso_y_el_resto_revisa():
    assert aviso_de_error("carta", "Frase sin origen en la traza: «Hola»").tipo == "dudoso"
    assert aviso_de_error("carta", "Fecha que no está en tus datos: 2019", "x 2019").tipo == "dudoso"
    assert aviso_de_error("cv", "Rasgo personal en el CV: edad").tipo == "revisa"
    assert aviso_de_error("cv", "Muletilla de IA: «sinergia»").tipo == "revisa"


def _node(codigo: str) -> str:
    textos = (ESTATICOS / "textos.js").read_text(encoding="utf-8")
    r = subprocess.run(["node", "-e", textos + "\n" + codigo], capture_output=True, text=True,
                       encoding="utf-8", check=True)
    return r.stdout.strip()


def test_veinte_requisitos_ausentes_dan_una_sola_linea_no_consta():
    reqs = [f"R{i}" for i in range(20)]
    linea = json.loads(_node(f"console.log(JSON.stringify(textoNoConstaVarios({json.dumps(reqs)})))"))
    assert linea.count(chr(10)) == 0 and linea.startswith("La oferta pide R0, R1") and "R4 y 15 más" in linea
    assert "R5" not in linea and "no constan en tu perfil" in linea
    codigo = 'console.log(JSON.stringify(textoNoConstaVarios(["a" + "b".repeat(100), "c"])))'
    largo = json.loads(_node(codigo))
    assert "…" in largo and len(largo) < 100


def test_la_pantalla_pinta_tres_grupos_y_no_el_panel_vacio():
    js = (ESTATICOS / "candidatura.js").read_text(encoding="utf-8")
    for titulo in ("No consta en tu CV", "Revisa", "Dato dudoso"):
        assert f'"{titulo}"' in js
    assert 'a.tipo || "revisa"' in js and "if (!hayAlgo && c.preparacion" in js
