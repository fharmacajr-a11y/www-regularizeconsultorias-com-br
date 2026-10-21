"""Voltar ao topo direto com movimento reduzido e suave nos demais casos.

Até 20/10/2026 o main.js rolava sempre com `behavior: 'smooth'`, inclusive para
quem pede movimento reduzido no sistema (`prefers-reduced-motion: reduce`).
Desde então, com essa preferência, o botão leva ao topo sem animação; sem ela,
a rolagem continua suave. A preferência é lida a cada clique.

O teste rola a página até 1500 px, espera o botão aparecer e clica nele com o
mouse. Um ouvinte de clique registrado depois do main.js lê o scrollY logo
depois da chamada de rolagem, ainda no mesmo evento, e um registro por quadro
acompanha a página até ela parar no topo (scrollY 0 por 300 ms, no máximo 5 s).
Com movimento reduzido, o scrollY já é 0 no evento e nenhum quadro mostra
posição intermediária. Sem a preferência, o scrollY ainda é o de partida no
evento, há quadros intermediários, a posição só diminui e termina em 0. Entram
a Home (base.css e components.css), em 390x844, e o Comunicado (custom.min.css),
em 1280x900.

Roda em subprocesso com o ServidorDeTeste (fila de 128; ver tests/support.py).
A sonda registra os recursos locais que não carregaram.
"""
import json
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler

import pytest

from support import SITE_DIR, ServidorDeTeste, subprocess_env


START_Y = 1500
CASES = (
    ("/", 390, 844, "reduce"),
    ("/", 390, 844, "no-preference"),
    ("/comunicado/", 1280, 900, "reduce"),
    ("/comunicado/", 1280, 900, "no-preference"),
)

PROBE = r"""
import json, sys
from playwright.sync_api import sync_playwright
from support import new_context, watch_local_loading

base, route, width, height, motion, start = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5], int(sys.argv[6])
output = {"load_failures": [], "other_load_failures": [], "medida": None}

READY = '''async (start) => {
  await document.fonts.ready;
  scrollTo(0, start);
  const button = document.getElementById('btn-voltar-topo');
  const began = performance.now();
  while (performance.now() - began < 3000) {
    await new Promise((done) => requestAnimationFrame(done));
    if (button.classList.contains('is-visible') && getComputedStyle(button).opacity === '1') break;
  }
  // Ouvinte registrado depois do main.js: roda logo depois da chamada de rolagem dele.
  window.__voltarTopo = {partida: scrollY, noClique: null, quadros: []};
  button.addEventListener('click', () => { window.__voltarTopo.noClique = scrollY; }, {once: true});
  return {scrollY, visivel: button.classList.contains('is-visible'), reduzido: matchMedia('(prefers-reduced-motion: reduce)').matches};
}'''
FOLLOW = '''async () => {
  const state = window.__voltarTopo;
  const began = performance.now();
  let since = performance.now();
  while (performance.now() - began < 5000) {
    await new Promise((done) => requestAnimationFrame(done));
    state.quadros.push(scrollY);
    if (scrollY !== 0) since = performance.now();
    else if (performance.now() - since >= 300) break;
  }
  return {...state, final: scrollY, esperou: Math.round(performance.now() - began)};
}'''

try:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = new_context(browser, viewport={"width": width, "height": height}, locale="pt-BR", reduced_motion=motion)
        page = context.new_page()
        closing = watch_local_loading(page, base, output["load_failures"], output["other_load_failures"])
        page.goto(base + route, wait_until="networkidle")
        ready = page.evaluate(READY, start)
        page.locator("#btn-voltar-topo").click()
        output["medida"] = {**ready, **page.evaluate(FOLLOW)}
        closing()
        context.close()
        browser.close()
finally:
    print(json.dumps(output, ensure_ascii=False))
"""


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass


@pytest.fixture(scope="module")
def base_url():
    server = ServidorDeTeste(("127.0.0.1", 0), partial(_QuietHandler, directory=str(SITE_DIR)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize("route,width,height,motion", CASES,
                         ids=[f"{route.strip('/') or 'home'}-{width}-{motion}" for route, width, _, motion in CASES])
def test_back_to_top_respects_reduced_motion(base_url, route, width, height, motion):
    completed = subprocess.run(
        [sys.executable, "-c", PROBE, base_url, route, str(width), str(height), motion, str(START_Y)],
        capture_output=True, text=True, encoding="utf-8", timeout=180, env=subprocess_env(),
    )
    try:
        output = json.loads(completed.stdout)
    except ValueError:
        output = None
    if not isinstance(output, dict) or "medida" not in output:
        pytest.fail(f"sonda sem saída válida (código {completed.returncode}):\n{completed.stdout[-2000:]}\n{completed.stderr[-4000:]}")
    if completed.returncode:
        pytest.fail(f"sonda caiu (código {completed.returncode}); carregamento {output['load_failures']}:\n{completed.stderr[-4000:]}")
    assert not output["load_failures"], f"recursos locais que não carregaram: {output['load_failures']}"

    state = output["medida"]
    label = f"{route} {width}x{height}, {motion}"
    assert state["visivel"] and state["scrollY"] == START_Y, f"{label}: botão não apareceu em scrollY {START_Y} ({state})"
    assert state["reduzido"] == (motion == "reduce"), f"{label}: emulação da preferência não aplicada"
    assert state["noClique"] is not None, f"{label}: o clique não chegou ao botão"
    assert state["final"] == 0, f"{label}: a página parou em scrollY {state['final']} depois de {state['esperou']} ms"
    frames = state["quadros"]
    intermediate = [y for y in frames if 0 < y < START_Y]
    if motion == "reduce":
        assert state["noClique"] == 0, f"{label}: logo depois do clique o scrollY era {state['noClique']}, não 0 (rolagem animada)"
        assert not intermediate, f"{label}: {len(intermediate)} quadros com posição intermediária: {intermediate[:10]}"
    else:
        assert state["noClique"] == START_Y, f"{label}: a página saltou para {state['noClique']} no clique, sem rolagem suave"
        assert len(intermediate) >= 3, f"{label}: só {len(intermediate)} quadros intermediários ({frames[:20]})"
        assert all(a >= b for a, b in zip(frames, frames[1:])), f"{label}: a posição subiu e desceu durante a rolagem ({frames[:40]})"
