// Capturas de las pantallas a 390 y 1280 px, en claro y en oscuro (RF-6.4b), contra la Horma local.
// Uso: node tests/capturas.js [carpeta]   (antes: docker compose up -d --build)
// Entra con una cuenta vacía de prueba y la borra al terminar. Solo en local: no gasta API.
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const BASE = 'http://localhost:8000';
const salida = process.argv[2] || path.join(os.tmpdir(), 'horma-capturas');

function playwright() {
  try { return require('playwright'); } catch {}
  const cache = path.join(process.env.LOCALAPPDATA || path.join(os.homedir(), '.npm'),
    process.env.LOCALAPPDATA ? 'npm-cache' : '', '_npx');
  for (const d of fs.existsSync(cache) ? fs.readdirSync(cache) : []) {
    const p = path.join(cache, d, 'node_modules', 'playwright');
    if (fs.existsSync(p)) return require(p);
  }
  throw new Error('Falta Playwright: ejecuta una vez «npx playwright --version»');
}

const compose = (args, input) => execFileSync('docker', ['compose', 'exec', '-T', ...args], { input, encoding: 'utf8' }).trim();

const SESION = `
import base64, json, os
from itsdangerous import TimestampSigner
from sqlalchemy import create_engine, text
from horma.web.db import sesion_sin_usuaria
with sesion_sin_usuaria(create_engine(os.environ["DATABASE_URL"])) as s:
    u = s.execute(text("select obtener_o_crear_usuaria('prueba-capturas')")).scalar_one()
d = base64.b64encode(json.dumps({"usuaria_id": u, "sub": "prueba-capturas", "csrf": "prueba"}).encode())
print(u, TimestampSigner(os.environ["SESSION_SECRET"]).sign(d).decode())
`;

(async () => {
  const { chromium } = playwright();
  fs.mkdirSync(salida, { recursive: true });
  const [id, cookie] = compose(['api', 'python', '-'], SESION).split(' ');
  let navegador;
  try {
    navegador = await chromium.launch({ channel: 'chrome' });
    for (const ancho of [390, 1280]) {
      for (const tema of ['light', 'dark']) {
        for (const ruta of ['portada', '/perfil', '/ofertas', '/candidaturas']) {
          const ctx = await navegador.newContext({ viewport: { width: ancho, height: 844 }, colorScheme: tema,
            isMobile: ancho < 900, hasTouch: ancho < 900 });
          if (ruta !== 'portada') await ctx.addCookies([{ name: 'horma_sesion', value: cookie, url: BASE }]);
          const p = await ctx.newPage();
          await p.goto(BASE + (ruta === 'portada' ? '/' : ruta), { waitUntil: 'networkidle' });
          const total = await p.evaluate(() => document.documentElement.scrollWidth);
          const nombre = `${ruta.replace('/', '')}-${ancho}-${tema}.png`;
          await p.screenshot({ path: path.join(salida, nombre), fullPage: true });
          console.log(total > ancho ? `DESBORDA (${total} px)` : 'ok', nombre);
          await ctx.close();
        }
      }
    }
  } finally {
    if (navegador) await navegador.close();
    if (/^\d+$/.test(id)) {
      compose(['postgres', 'sh', '-c', `psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "delete from usuarias where id=${id}"`]);
    }
  }
  console.log(salida);
})();
