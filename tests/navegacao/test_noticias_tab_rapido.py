"""Foco visível depois de Tabs rápidos na listagem de notícias.

Até 19/10/2026 o base.css tinha `html { scroll-behavior: smooth; }`. Na
listagem, a coluna lateral (busca, categorias, ordenação e atendimento) vem
antes da lista no documento e termina abaixo da dobra: até 21/10/2026, abaixo
de 1024 px ela aparecia depois da lista; a partir daí, à esquerda. Desde
21/10/2026 ela vem antes da lista também na tela, compacta abaixo de 1024 px
(test_noticias_ordem_tab.py). Tabs seguidos por ela
iniciavam rolagens suaves que o Tab seguinte redirecionava antes de a página
andar. O foco chegava ao link do 1º card ainda visível, e o Chromium não rolava
para ele nem interrompia a animação em curso. A página terminava na coluna, com
o link focado fora da tela: em 960x900, scrollY 3280 e o link a -2546 px; em
1440x900, 1315 e -484. Com Tab a cada 100 ms ou mais, o movimento terminava
certo. O diagnóstico está no pacote diagnostico-tabs-rapidos-2026-10-18.

O teste usa o CSS real da pasta servida, sem regra que desligue a rolagem suave.
Aperta Tab sem pausa até o link do 1º card: cada tecla é seguida só da
conferência do foco, como no diagnóstico. Depois espera a página parar, com
scrollY igual por 500 ms e no máximo 5 s, e exige que o link continue com o
foco, inteiro na janela, abaixo da navbar e sem outro elemento sobre o centro
dele. A mensagem separa o link fora da janela, o link sob a navbar e o link
coberto por outro elemento.

Sobre o artefato do build de 2ebc9df o teste falha em 960 e 1440; com a
correção, passa nas três janelas. A janela de 390 px entra como controle: lá o
link está abaixo da dobra quando recebe o foco e a página rola até ele.

Roda em subprocesso com o ServidorDeTeste (fila de 128; ver tests/support.py).
A sonda registra os recursos locais que não carregaram. Documento, CSS,
JavaScript ou fonte sem carregar reprova o caso como falha de carregamento,
separada da falha de foco.
"""
import json
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler

import pytest

from support import SITE_DIR, ServidorDeTeste, subprocess_env


VIEWPORTS = ((960, 900), (1440, 900), (390, 844))

PROBE = r"""
import json, sys
from playwright.sync_api import sync_playwright
from support import new_context, watch_local_loading

base, width, height = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
output = {"failures": [], "load_failures": [], "other_load_failures": [], "tabs": 0, "estado": None}

# Link do 1º card visível da lista, na ordem da tela.
TARGET = '''() => {
  const cards = [...document.querySelectorAll('#news-article-list [data-news-card]')]
    .filter(card => card.getClientRects().length)
    .sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
  window.__alvoTab = cards.length ? cards[0].querySelector('a[href]') : null;
  return window.__alvoTab ? window.__alvoTab.getAttribute('href') : null;
}'''
# Página parada: scrollY igual por 500 ms, no máximo 5 s.
SETTLE = '''async () => {
  const started = performance.now();
  let last = scrollY, since = performance.now();
  while (performance.now() - since < 500 && performance.now() - started < 5000) {
    await new Promise(done => requestAnimationFrame(done));
    if (scrollY !== last) { last = scrollY; since = performance.now(); }
  }
  return {parada: performance.now() - since >= 500, esperou: Math.round(performance.now() - started)};
}'''
STATE = '''() => {
  const alvo = window.__alvoTab, rect = alvo.getBoundingClientRect();
  const navbar = document.getElementById('navbar').getBoundingClientRect().bottom;
  const x = (rect.left + rect.right) / 2, y = (rect.top + rect.bottom) / 2;
  const inside = rect.top >= 0 && rect.bottom <= innerHeight && rect.left >= 0 && rect.right <= document.documentElement.clientWidth;
  const hit = inside ? document.elementFromPoint(x, y) : null;
  return {foco: document.activeElement === alvo, scrollY, top: rect.top, bottom: rect.bottom, innerHeight, navbar, inside,
          abaixo_da_navbar: rect.top >= navbar - 0.5,
          centro: hit ? (alvo.contains(hit) ? 'alvo' : (hit.id || hit.tagName.toLowerCase() + '.' + String(hit.className).split(' ')[0])) : null};
}'''

try:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = new_context(browser, viewport={"width": width, "height": height}, locale="pt-BR")
        page = context.new_page()
        closing = watch_local_loading(page, base, output["load_failures"], output["other_load_failures"])
        page.goto(base + "/noticias/", wait_until="networkidle")
        href = page.evaluate(TARGET)
        if not href:
            output["failures"].append("nenhum card visível na listagem")
        else:
            page.evaluate("window.scrollTo(0, 0)")
            for tabs in range(1, 81):
                page.keyboard.press("Tab")
                if page.evaluate("() => document.activeElement === window.__alvoTab"):
                    break
            else:
                output["failures"].append(f"o link {href} não recebeu o foco em 80 Tabs")
            output["tabs"] = tabs
            settle = page.evaluate(SETTLE)
            state = page.evaluate(STATE)
            output["estado"] = {**state, **settle, "href": href}
            label = f"{href} depois de {tabs} Tabs sem pausa"
            if not settle["parada"]:
                output["failures"].append(f"{label}: a página ainda rolava 5 s depois do foco (scrollY {state['scrollY']})")
            if not state["foco"]:
                output["failures"].append(f"{label}: o link perdeu o foco")
            elif not state["inside"]:
                output["failures"].append(f"{label}: link focado fora da janela (top {state['top']:.0f}, bottom {state['bottom']:.0f}, "
                                          f"janela {state['innerHeight']}, scrollY {state['scrollY']})")
            elif not state["abaixo_da_navbar"]:
                output["failures"].append(f"{label}: link focado sob a navbar (top {state['top']:.0f}, navbar até {state['navbar']:.0f})")
            elif state["centro"] != "alvo":
                output["failures"].append(f"{label}: link focado coberto por {state['centro']}")
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


@pytest.mark.parametrize("viewport", VIEWPORTS, ids=[f"{w}x{h}" for w, h in VIEWPORTS])
def test_fast_tabs_keep_the_first_news_card_link_visible(base_url, viewport):
    width, height = viewport
    completed = subprocess.run(
        [sys.executable, "-c", PROBE, base_url, str(width), str(height)],
        capture_output=True, text=True, encoding="utf-8", timeout=180, env=subprocess_env(),
    )
    try:
        output = json.loads(completed.stdout)
    except ValueError:
        output = None
    if not isinstance(output, dict) or not isinstance(output.get("failures"), list):
        pytest.fail(f"sonda sem saída válida (código {completed.returncode}):\n{completed.stdout[-2000:]}\n{completed.stderr[-4000:]}")
    if completed.returncode:
        pytest.fail(f"sonda caiu (código {completed.returncode}); falhas já registradas {output['failures']}; "
                    f"carregamento {output['load_failures']}:\n{completed.stderr[-4000:]}")
    assert not output["load_failures"], f"recursos locais que não carregaram em {width}x{height}: {output['load_failures']}"
    assert not output["failures"], f"{width}x{height}: " + "; ".join(output["failures"])
