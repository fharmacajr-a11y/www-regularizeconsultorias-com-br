"""Link com âncora para logo abaixo do cabeçalho, mesmo com a Inter atrasada.

Até 20/10/2026 o custom.min.css tinha `html { scroll-behavior: smooth; }`. Ao
abrir /comunicado/#instabilidade-anvisa-2026-10-19, o Chromium calculava o
destino da rolagem suave com a fonte de reserva; quando a Inter chegava durante
a animação, o conteúdo acima do card crescia e a rolagem terminava no destino
antigo. Ao vivo, depois do deploy de 64beb17, o card parou 358 px abaixo do
cabeçalho em 390x844 e 160 px em 1280x900, com o botão "Ver histórico completo"
fora da tela em 390. Sem a rolagem suave, o navegador reposiciona a âncora
quando a fonte troca, e o card para a 16 px do cabeçalho (o scroll-padding-top).

Os demais testes servem a Inter local na hora, e o defeito não aparece. Aqui a
folha do Google Fonts aponta para um servidor local que entrega a fonte com
atraso. Com 300 e 800 ms o defeito se repetiu na base 64beb17 (358 e 160 px);
com 1500 ms a fonte chega depois da animação e a base também passa.

Roda em subprocesso com o ServidorDeTeste, como os demais testes de navegação:
o Playwright síncrono não abre dentro do laço asyncio que outro módulo deixa
aberto no processo do pytest.
"""
import functools
import json
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler

import pytest

from support import FONT_FILE, SITE_DIR, ServidorDeTeste, subprocess_env


ROUTE = "/comunicado/#instabilidade-anvisa-2026-10-19"
CARD_ID = "instabilidade-anvisa-2026-10-19"
VIEWPORTS = ((390, 844), (1280, 900))
FONT_DELAYS_MS = (300, 800)
# Folga esperada: 16 px nas duas larguras (scroll-padding-top menos a altura da navbar fixa).
MAX_GAP = 24

PROBE = r"""
import json, sys
from playwright.sync_api import sync_playwright
from support import new_context

site, fonts, route, card_id, width, height, delay = sys.argv[1:8]
css = ("@font-face{font-family:'Inter';font-style:normal;font-weight:400 800;font-display:swap;"
       f"src:url('{fonts}/inter-latin-variable-v20.woff2?atraso={delay}') format('woff2')}}")
MEASURE = '''async (id) => {
  const started = performance.now();
  let last = scrollY, since = performance.now();
  while (performance.now() - since < 700 && performance.now() - started < 8000) {
    await new Promise((done) => requestAnimationFrame(done));
    if (scrollY !== last) { last = scrollY; since = performance.now(); }
  }
  await document.fonts.ready;
  const card = document.getElementById(id).getBoundingClientRect();
  const navbar = document.getElementById('navbar').getBoundingClientRect().bottom;
  return {gap: card.top - navbar, bottom: card.bottom, innerHeight, scrollY,
          inter: document.fonts.check('16px Inter'), scrollBehavior: getComputedStyle(document.documentElement).scrollBehavior};
}'''
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    context = new_context(browser, viewport={"width": int(width), "height": int(height)})
    page = context.new_page()
    page.route("https://fonts.googleapis.com/**", lambda request: request.fulfill(
        status=200, body=css, content_type="text/css; charset=utf-8", headers={"Access-Control-Allow-Origin": "*"}))
    page.goto(site + route, wait_until="load")
    state = page.evaluate(MEASURE, card_id)
    context.close()
    browser.close()
print(json.dumps(state))
"""


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass


class _SlowFontHandler(BaseHTTPRequestHandler):
    font = b""

    def log_message(self, _format, *_args):
        pass

    def do_GET(self):
        # O atraso vem na própria URL (?atraso=ms), definida pela sonda.
        delay = int(self.path.rsplit("atraso=", 1)[1]) if "atraso=" in self.path else 0
        time.sleep(delay / 1000)
        self.send_response(200)
        self.send_header("Content-Type", "font/woff2")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(self.font)))
        self.end_headers()
        self.wfile.write(self.font)


def _serve(handler):
    server = ServidorDeTeste(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


@pytest.fixture(scope="module")
def servers():
    _SlowFontHandler.font = FONT_FILE.read_bytes()
    started = [_serve(functools.partial(_QuietHandler, directory=str(SITE_DIR))), _serve(_SlowFontHandler)]
    try:
        yield tuple(f"http://127.0.0.1:{server.server_port}" for server, _ in started)
    finally:
        for server, thread in started:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()


@pytest.mark.parametrize("delay_ms", FONT_DELAYS_MS)
@pytest.mark.parametrize("width,height", VIEWPORTS)
def test_anchor_lands_below_navbar_when_inter_arrives_late(servers, width, height, delay_ms):
    site, fonts = servers
    completed = subprocess.run(
        [sys.executable, "-c", PROBE, site, fonts, ROUTE, CARD_ID, str(width), str(height), str(delay_ms)],
        capture_output=True, text=True, encoding="utf-8", timeout=120, env=subprocess_env(),
    )
    try:
        state = json.loads(completed.stdout)
    except ValueError:
        pytest.fail(f"sonda sem saída válida (código {completed.returncode}):\n{completed.stdout[-2000:]}\n{completed.stderr[-4000:]}")

    case = f"{width}x{height}, Inter com {delay_ms} ms de atraso"
    assert state["inter"], f"{case}: a Inter não carregou ({state})"
    assert 0 <= state["gap"] <= MAX_GAP, f"{case}: card a {state['gap']:.0f} px do cabeçalho ({state})"
    assert state["bottom"] <= state["innerHeight"], f"{case}: card cortado na base da janela ({state})"
    assert state["scrollBehavior"] == "auto", f"{case}: rolagem suave no html ({state})"
