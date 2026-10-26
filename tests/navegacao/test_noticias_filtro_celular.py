"""Filtro da listagem de notícias no celular: o 1º card do resultado aparece na janela.

Abaixo de 1024 px a coluna de filtros vem antes da lista: a pesquisa e, logo abaixo, a faixa com as
categorias e a ordenação (pages/noticias.css), que rola na horizontal com toque; com mouse, desde 23/10/2026,
as categorias ficam num carrossel com setas e a ordenação fora dele (de 21 a 23/10/2026 a faixa quebrava em
linhas). Até 21/10/2026 a coluna vinha depois da lista e o resultado de um filtro ficava inteiro
acima da janela (em 390x844, Enter em "SNCR" deixava o 1º card de −1.488 a −978 px). Agora, depois do clique
numa categoria ou na ordenação, o
assets/js/pages/noticias.js rola até a faixa ficar logo abaixo do cabeçalho quando o topo do 1º card não
aparece; se já aparece, a página não se move.

Casos com toque (hasTouch, isMobile) em retrato de celular (390x844 e 360x640) e no tablet (768x1024), e com
mouse (o contexto padrão do Playwright) em 390x844, 768x1024 e 960x900 (a janela em meia tela):
- teclado: Tab do topo até "SNCR" e Enter;
- toque ou clique: a faixa no pé da janela, com o 1º card abaixo dela (pré-condição, exigida abaixo de
  640 px; em 768x1024 e 960x900 a faixa não chega ao pé da janela e o caso não se aplica), e um toque (ou
  clique) em "SNCR";
- ordenação: Tab até "A-Z Mais velha", no fim da faixa, e Enter.
Em cada um, a contagem e a categoria do resultado têm de bater, o topo do 1º card tem de ficar abaixo do
cabeçalho e pelo menos 96 px acima do fim da janela, e o botão usado continua com o foco (no toque e no
clique, no lugar) e inteiro na janela, abaixo do cabeçalho e dentro da faixa.
Com mouse, a faixa em linhas ocupa mais altura: com a faixa logo abaixo do cabeçalho, o topo do 1º card só fica
96 px acima do fim da janela a partir de 382 px de altura em 960 px de largura, 432 px em 768, 653 px em 390 e
753 px em 360 (oito linhas de botões). Por isso a janela de 360x640 entra só com toque.
Em 1440x900 (coluna ao lado da lista) um clique em "SNCR" não rola a página.

Sem JavaScript (o main.js não roda), a pesquisa e a faixa continuam visíveis em 390 px, com os 85 cards
exibidos, e o bloco "Atendimento técnico" fica fora (display: none); em 1440 px a coluna mantém os quatro
blocos.
"""
import json
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler

import pytest

from support import SITE_DIR, ServidorDeTeste, subprocess_env


# (largura, altura, ponteiro).
STACKED = ((390, 844, "toque"), (360, 640, "toque"), (768, 1024, "toque"),
           (390, 844, "mouse"), (768, 1024, "mouse"), (960, 900, "mouse"))
VISIBLE = 96

PROBE = r"""
import json, sys
from playwright.sync_api import sync_playwright
from support import new_context, watch_local_loading

base, mode, width, height, visible = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
pointer = sys.argv[6]
TOUCH = {"has_touch": True, "is_mobile": True} if pointer == "toque" else {}
output = {"failures": [], "load_failures": [], "other_load_failures": [], "cases": {}}

SETTLE = '''async () => {
  await document.fonts.ready;
  await new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done)));
}'''
STATE = '''(selector) => {
  const cards = [...document.querySelectorAll('#news-article-list [data-news-card]')].filter(c => c.getClientRects().length);
  const first = cards[0] ? cards[0].getBoundingClientRect() : null;
  const button = document.querySelector(selector), b = button.getBoundingClientRect();
  const strip = document.querySelector('.news-filters__strip');
  const s = strip ? strip.getBoundingClientRect() : {left: 0, right: innerWidth};
  const header = document.getElementById('navbar').getBoundingClientRect().bottom;
  return {
    count: document.getElementById('news-result-count').textContent.trim(),
    categories: [...new Set(cards.map(c => c.dataset.category))],
    firstTop: first ? first.top : null, header, innerHeight, scrollY,
    focused: document.activeElement === button,
    buttonShown: b.top >= header - 0.5 && b.bottom <= innerHeight + 0.5 && b.left >= s.left - 0.5 && b.right <= s.right + 0.5,
    button: {top: Math.round(b.top), bottom: Math.round(b.bottom), left: Math.round(b.left), right: Math.round(b.right)},
  };
}'''


def check(name, state, before=None, count=None, category=None, focused=True):
    output["cases"][name] = {"antes": before, "depois": state}
    label = f"{width}x{height} {pointer} {name}"
    if count and state["count"] != count:
        output["failures"].append(f"{label}: contagem '{state['count']}', esperada '{count}'")
    if category and state["categories"] != [category]:
        output["failures"].append(f"{label}: categorias do resultado {state['categories']}")
    top = state["firstTop"]
    if top is None or top < state["header"] - 0.5 or top > state["innerHeight"] - visible:
        output["failures"].append(f"{label}: topo do 1º card em {top if top is None else round(top)} px; janela de "
                                  f"{state['header']:.0f} a {state['innerHeight'] - visible} px (cabeçalho até o fim menos {visible})")
    if focused and not state["focused"]:
        output["failures"].append(f"{label}: o botão usado perdeu o foco")
    if not state["buttonShown"]:
        output["failures"].append(f"{label}: o botão usado não aparece inteiro {state['button']}")


def tab_to(page, selector, limit=80):
    page.evaluate("() => { window.scrollTo(0, 0); document.activeElement && document.activeElement.blur(); }")
    for _ in range(limit):
        page.keyboard.press("Tab")
        if page.evaluate("s => document.activeElement === document.querySelector(s)", selector):
            return True
    output["failures"].append(f"{width}x{height} {pointer}: {selector} não recebeu o foco em {limit} Tabs")
    return False


def open_page(browser, **options):
    context = new_context(browser, viewport={"width": width, "height": height}, locale="pt-BR", **options)
    page = context.new_page()
    closing = watch_local_loading(page, base, output["load_failures"], output["other_load_failures"])
    page.goto(base + "/noticias/", wait_until="load")
    page.evaluate(SETTLE)
    return context, page, closing


try:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        sncr, asc = "[data-news-category=sncr]", "[data-news-sort=asc]"
        if mode == "empilhada":
            context, page, closing = open_page(browser, **TOUCH)
            if tab_to(page, sncr):
                page.keyboard.press("Enter")
                page.evaluate(SETTLE)
                check("teclado: Enter em SNCR", page.evaluate(STATE, sncr), count="2 notícias encontradas", category="sncr")
            closing()
            context.close()

            context, page, closing = open_page(browser, **TOUCH)
            button = page.locator(sncr)
            button.scroll_into_view_if_needed()
            page.evaluate('''s => { const b = document.querySelector(s).getBoundingClientRect();
                window.scrollBy(0, b.bottom - innerHeight + 8); }''', sncr)
            page.evaluate(SETTLE)
            before = page.evaluate(STATE, sncr)
            applicable = before["firstTop"] is not None and before["firstTop"] > before["innerHeight"] - visible
            gesture = "toque" if pointer == "toque" else "clique"
            if not applicable and width < 640:
                output["failures"].append(f"{width}x{height} {pointer}: pré-condição falhou, o 1º card já aparecia antes do "
                                          f"{gesture} (topo {before['firstTop']})")
            if applicable:
                button.tap() if pointer == "toque" else button.click()
                page.evaluate(SETTLE)
                check(f"{gesture} em SNCR com a faixa no pé da janela", page.evaluate(STATE, sncr), before,
                      count="2 notícias encontradas", category="sncr", focused=False)
            else:
                # Janela alta (tablet em retrato): a faixa não chega ao pé da janela e o 1º card já aparece.
                output["cases"][f"{gesture} em SNCR com a faixa no pé da janela"] = {"antes": before, "depois": "não se aplica"}
            closing()
            context.close()

            context, page, closing = open_page(browser, **TOUCH)
            if tab_to(page, asc):
                page.keyboard.press("Enter")
                page.evaluate(SETTLE)
                state = page.evaluate(STATE, asc)
                check("teclado: Enter em A-Z Mais velha", state, count="85 notícias encontradas")
            closing()
            context.close()
        else:
            context, page, closing = open_page(browser)
            page.evaluate("window.scrollTo(0, 400)")
            page.evaluate(SETTLE)
            before = page.evaluate("scrollY")
            page.locator(sncr).click()
            page.evaluate(SETTLE)
            after = page.evaluate("scrollY")
            output["cases"]["lado a lado: clique em SNCR"] = {"antes": before, "depois": after}
            if after != before:
                output["failures"].append(f"{width}x{height} {pointer}: o clique em SNCR rolou a página de {before} para {after}")
            closing()
            context.close()
        browser.close()
finally:
    print(json.dumps(output, ensure_ascii=False))
"""

NO_SCRIPT = r"""
import json, sys
from playwright.sync_api import sync_playwright
from support import new_context

base = sys.argv[1]
result = {}
with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    for width, height in ((390, 844), (1440, 900)):
        context = new_context(browser, viewport={"width": width, "height": height}, java_script_enabled=False)
        page = context.new_page()
        page.goto(base + "/noticias/", wait_until="load")
        result[width] = page.evaluate('''() => {
          const box = el => { if (!el || !el.getClientRects().length) return null; const r = el.getBoundingClientRect();
            return {top: r.top + scrollY, bottom: r.bottom + scrollY, left: r.left, right: r.right, height: r.height}; };
          const visible = el => { const b = box(el); return !!b && b.height > 0 && getComputedStyle(el).visibility === 'visible'; };
          const list = document.getElementById('news-article-list').getBoundingClientRect();
          return {
            search: visible(document.getElementById('news-search')),
            strip: visible(document.querySelector('.news-filters__strip')),
            todos: visible(document.querySelector('[data-news-category=todos]')),
            sort: visible(document.querySelector('[data-news-sort=asc]')),
            contact: visible(document.querySelector('main aside a[href="/contato/"]')),
            cards: [...document.querySelectorAll('#news-article-list [data-news-card]')].filter(visible).length,
            filtersBeforeList: document.querySelector('main aside').getBoundingClientRect().bottom <= list.top + 0.5,
            overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
          };
        }''')
        context.close()
    browser.close()
print(json.dumps(result))
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


def _probe(base_url, mode, width, height, pointer="mouse"):
    completed = subprocess.run(
        [sys.executable, "-c", PROBE, base_url, mode, str(width), str(height), str(VISIBLE), pointer],
        capture_output=True, text=True, encoding="utf-8", timeout=240, env=subprocess_env(),
    )
    try:
        output = json.loads(completed.stdout)
    except ValueError:
        output = None
    if not isinstance(output, dict) or not isinstance(output.get("failures"), list):
        pytest.fail(f"sonda sem saída válida (código {completed.returncode}):\n{completed.stdout[-2000:]}\n{completed.stderr[-4000:]}")
    if completed.returncode:
        pytest.fail(f"sonda caiu (código {completed.returncode}); falhas já registradas {output['failures']}:\n{completed.stderr[-4000:]}")
    assert not output["load_failures"], f"recursos locais que não carregaram em {width}x{height}: {output['load_failures']}"
    return output


@pytest.mark.parametrize("width,height,pointer", STACKED, ids=[f"{w}x{h}-{t}" for w, h, t in STACKED])
def test_mobile_filter_shows_the_first_result_card(base_url, width, height, pointer):
    output = _probe(base_url, "empilhada", width, height, pointer)
    assert not output["failures"], "; ".join(output["failures"])


def test_side_by_side_filter_does_not_scroll(base_url):
    output = _probe(base_url, "lado a lado", 1440, 900)
    assert not output["failures"], "; ".join(output["failures"])


def test_listing_without_javascript_keeps_search_and_strip(base_url):
    completed = subprocess.run(
        [sys.executable, "-c", NO_SCRIPT, base_url],
        capture_output=True, text=True, encoding="utf-8", timeout=180, env=subprocess_env(),
    )
    assert completed.returncode == 0, completed.stderr
    result = {int(width): state for width, state in json.loads(completed.stdout).items()}
    phone, desktop = result[390], result[1440]
    for width, state in result.items():
        assert state["search"] and state["strip"] and state["todos"] and state["sort"], (width, state)
        assert state["cards"] == 85, (width, state["cards"])
        assert state["overflowX"] <= 0, (width, state["overflowX"])
    assert phone["filtersBeforeList"] and not phone["contact"], phone
    assert desktop["contact"] and not desktop["filtersBeforeList"], desktop
