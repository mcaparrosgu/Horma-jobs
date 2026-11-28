// Capturas de las pantallas a 390 y 1280 px, en claro y en oscuro (RF-6.4b), contra la Horma local.
// Uso: node tests/capturas.js [carpeta]   (antes: docker compose up -d --build)
// Levanta una copia temporal de la API en el puerto 8010 con una cuenta de prueba (también admin), la llena
// con datos inventados y lo borra todo al terminar. Solo deja pasar peticiones GET: no encola ni gasta API.
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const BASE = 'http://localhost:8010';
const COPIA = 'horma-capturas';
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

const docker = (args, input) => execFileSync('docker', args, { input, encoding: 'utf8' }).trim();
const pulsar = (selector) => async (p) => { await p.locator(selector).first().click(); await p.waitForTimeout(800); };

const pantallas = (candidatura) => [
  ['portada', '/', { anonima: true }],
  ['perfil', '/perfil'],
  ['perfil-ver-cv', '/perfil', { accion: pulsar('#cvs-subidos button:has-text("Ver")'), ventana: true }],
  ['ofertas', '/ofertas'],
  ['ofertas-aviso', '/ofertas', { aviso: true }],
  ['ofertas-que-buscas', '/ofertas', { accion: pulsar('#que-buscas > summary') }],
  ['ofertas-anadir', '/ofertas', { accion: pulsar('#abrir-anadir'), ventana: true }],
  ['candidaturas', '/candidaturas'],
  ['candidatura', `/candidaturas/${candidatura}`],
  ['admin-ingesta', '/ingesta'],
  ['admin-catalogo', '/catalogo'],
  ['admin-costes', '/costes'],
  ['admin-envios', '/envios'],
];

(async () => {
  const { chromium } = playwright();
  fs.mkdirSync(salida, { recursive: true });
  let navegador, id, fichero;
  try {
    docker(['compose', 'run', '-d', '--rm', '--no-deps', '--name', COPIA, '-p', '127.0.0.1:8010:8000',
      '-e', 'HORMA_ADMINS=prueba-capturas', 'api']);
    const [uid, cookie, candidatura, pdf] = docker(['exec', '-i', COPIA, 'python', '-'],
      fs.readFileSync(path.join(__dirname, 'capturas_datos.py'), 'utf8')).split(' ');
    id = uid;
    fichero = pdf;
    for (let i = 0; i < 40; i++) {
      try { if ((await fetch(BASE + '/salud')).ok) break; } catch {}
      await new Promise((r) => setTimeout(r, 500));
    }
    navegador = await chromium.launch({ channel: 'chrome' });
    for (const ancho of [390, 1280]) {
      for (const tema of ['light', 'dark']) {
        for (const [nombre, ruta, { anonima, accion, ventana, aviso } = {}] of pantallas(candidatura)) {
          const ctx = await navegador.newContext({ viewport: { width: ancho, height: 844 }, colorScheme: tema,
            isMobile: ancho < 900, hasTouch: ancho < 900, serviceWorkers: 'block' });
          await ctx.route('**/*', (r) => (r.request().method() === 'GET' ? r.continue() : r.abort()));
          if (!anonima) await ctx.addCookies([{ name: 'horma_sesion', value: cookie, url: BASE }]);
          // La línea «Pide menos de lo que tienes» (RF-12.36) se fuerza en la respuesta: el catálogo no se toca.
          if (aviso) await ctx.route('**/api/recomendaciones', async (r) => {
            const respuesta = await r.fetch();
            const datos = await respuesta.json();
            for (const o of datos.recomendaciones) o.pide_menos = true;
            await r.fulfill({ response: respuesta, json: datos });
          });
          const p = await ctx.newPage();
          const archivo = `${nombre}-${ancho}-${tema}.png`;
          try {
            await p.goto(BASE + ruta, { waitUntil: 'networkidle' });
            if (accion) await accion(p);
            const total = await p.evaluate(() => document.documentElement.scrollWidth);
            await p.screenshot({ path: path.join(salida, archivo), fullPage: !ventana });
            console.log(total > ancho ? `DESBORDA (${total} px)` : 'ok', archivo);
          } catch (e) {
            console.log('FALLA', archivo, e.message.split('\n')[0]);
          }
          await ctx.close();
        }
      }
    }
  } finally {
    if (navegador) await navegador.close();
    if (/^\d+$/.test(id)) {
      docker(['exec', COPIA, 'rm', '-f', fichero]);
      docker(['compose', 'exec', '-T', 'postgres', 'sh', '-c',
        'psql -v ON_ERROR_STOP=1 -q -U "$POSTGRES_USER" -d "$POSTGRES_DB"'],
        fs.readFileSync(path.join(__dirname, 'capturas_borrar.sql'), 'utf8'));
    }
    try { docker(['rm', '-f', COPIA]); } catch {}
  }
  console.log(salida);
})();
