"""T18 (RF-4.6b, RF-4.6c, RF-4.6e): el perfil de producción de Compose. Solo lee la configuración."""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.skipif(shutil.which("docker") is None, reason="Docker no está instalado")


@pytest.fixture(scope="module")
def servicios():
    r = subprocess.run(
        ["docker", "compose", "-f", "docker-compose.yml", "-f", "docker-compose.prod.yml",
         "--profile", "ingesta", "config", "--format", "json"],
        cwd=RAIZ, capture_output=True, text=True, env={**os.environ, "HORMA_DOMINIO": "localhost"})
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)["services"]


def test_postgres_y_la_api_no_publican_puertos(servicios):
    assert not servicios["postgres"].get("ports")
    assert not servicios["api"].get("ports")


def test_solo_el_proxy_publica_puertos(servicios):
    publicados = {n: s["ports"] for n, s in servicios.items() if s.get("ports")}
    assert set(publicados) == {"caddy"}
    assert {p["target"] for p in publicados["caddy"]} == {80, 443}


def test_todos_los_servicios_se_reinician_solos(servicios):
    sin = [n for n, s in servicios.items() if s.get("restart") != "unless-stopped"]
    assert not sin, sin


def test_la_api_tiene_healthcheck_contra_salud(servicios):
    prueba = " ".join(servicios["api"]["healthcheck"]["test"])
    assert "/salud" in prueba


def test_la_api_corre_en_produccion_y_solo_se_fia_del_proxy(servicios):
    api = servicios["api"]
    assert api["environment"]["APP_ENV"] == "produccion"
    comando = " ".join(api["command"])
    assert "--proxy-headers" in comando and "--forwarded-allow-ips 172.29.77.200" in comando
    assert servicios["caddy"]["networks"]["default"]["ipv4_address"] == "172.29.77.200"


def test_el_proxy_tiene_version_fijada_y_no_corre_como_root(servicios):
    caddy = servicios["caddy"]
    assert not caddy["image"].endswith(("latest", ":2")) and ":" in caddy["image"]
    assert caddy["user"] != "0" and caddy["user"] != "root"


def test_la_api_y_el_worker_no_leen_el_env_de_desarrollo(servicios):
    # Si `.env.produccion` no existe, Compose lo omite; lo que nunca debe aparecer es `.env`
    for n in ("api", "worker"):
        rutas = [Path(e["path"]).name for e in servicios[n].get("env_file", [])]
        assert ".env" not in rutas, (n, rutas)
    assert (RAIZ / "docker-compose.prod.yml").read_text(encoding="utf-8").count(".env.produccion") >= 3


def test_el_caddyfile_reenvia_a_la_api():
    t = (RAIZ / "Caddyfile").read_text(encoding="utf-8")
    assert "{$HORMA_DOMINIO" in t and "reverse_proxy api:8000" in t


def test_el_ejemplo_de_produccion_no_lleva_secretos_y_se_versiona():
    claves = {}
    for linea in (RAIZ / ".env.produccion.example").read_text(encoding="utf-8").splitlines():
        if linea and not linea.startswith("#") and "=" in linea:
            k, _, v = linea.partition("=")
            claves[k] = v
    for secreto in ("POSTGRES_PASSWORD", "HORMA_APP_PASSWORD", "HORMA_MIGRADOR_PASSWORD", "SESSION_SECRET",
                    "GOOGLE_CLIENT_SECRET", "ANTHROPIC_API_KEY"):
        assert claves[secreto] == "", secreto
    r = subprocess.run(["git", "check-ignore", "-q", ".env.produccion.example"], cwd=RAIZ)
    assert r.returncode == 1  # no está ignorado
    r = subprocess.run(["git", "check-ignore", "-q", ".env.produccion"], cwd=RAIZ)
    assert r.returncode == 0  # el real sí
