"""Bordas da coluna lateral das Notícias em relação aos outros cards.

Abaixo de 1024 px a coluna vem antes da lista (desde 21/10/2026; antes vinha
depois, com order) e fica compacta: o bloco da pesquisa e o cartão da faixa de
categorias e ordenação, sem o bloco "Atendimento técnico". Os dois têm de
ocupar a mesma largura útil de "Orientação técnica", dos cards de notícia e de
"Sobre o conteúdo". Até a rodada de 04/10/2026 um margin-right só da coluna a
terminava 56 a 60 px antes da borda dos demais. A partir de 1024 px ficam as
duas colunas do grid, com os quatro blocos (Pesquisar, Categorias, Ordenar,
Atendimento técnico): a lateral na borda esquerda de "Sobre o conteúdo" e a
lista na borda direita.

Empilhada, cada largura roda com mouse (o contexto padrão do Playwright), em
que as categorias ficam num carrossel com setas desde 23/10/2026 (de 21 a
23/10/2026 a faixa quebrava em linhas), e com toque (has_touch e is_mobile),
em que a faixa rola na horizontal. Lado a lado, só com mouse. As setas do
carrossel ficam fora do Tab e da conta dos controles.
"""
import json
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from support import SITE_DIR, subprocess_env


STACKED_WIDTHS = (320, 360, 390, 414, 639, 640, 767, 768, 940, 944, 950, 960, 1023)
TWO_COLUMN_WIDTHS = (1024, 1279, 1280, 1440, 1920)
STACKED_CASES = tuple((width, pointer) for width in STACKED_WIDTHS for pointer in ("mouse", "toque"))
TOLERANCE = 0.5

PROBE = r'''
import json
import sys
from playwright.sync_api import sync_playwright

from support import new_context

base, cases = sys.argv[1], json.loads(sys.argv[2])
MEASURE = """() => {
    const box = el => { const r = el.getBoundingClientRect();
        return {left: r.left, right: r.right, top: r.top + scrollY, bottom: r.bottom + scrollY}; };
    const kicker = text => [...document.querySelectorAll('main p')]
        .find(p => p.textContent.trim() === text).parentElement;
    const sidebar = document.querySelector('aside .news-sidebar');
    const list = document.getElementById('news-article-list');
    return {
        innerWidth, clientWidth: document.documentElement.clientWidth,
        overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        // Blocos com caixa e borda: abaixo de 1024 px os de categorias e de
        // ordenação são display: contents dentro do cartão da faixa, e o de
        // atendimento é display: none.
        blocks: [...sidebar.querySelectorAll('.news-search-card, .news-filters, .news-filters__block, .news-contact-card')]
            .filter(el => el.getClientRects().length && getComputedStyle(el).borderTopWidth !== '0px')
            .map(el => ({name: el.querySelector('h2, p').textContent.trim(), ...box(el)})),
        aside: box(sidebar.closest('aside')), listColumn: box(list.parentElement),
        card: box(list.querySelector('[data-news-card]')),
        orientacao: box(kicker('Orientação técnica')),
        sobre: box(kicker('Sobre o conteúdo')),
    };
}"""
# Com cada botão flutuante na altura de cada controle exibido da lateral, o
# centro do controle continua sendo dele. Na faixa que rola (com toque), o
# controle é trazido para dentro dela antes (nearest, com o scroll-padding da
# faixa).
COVERED = """async () => {
    document.documentElement.style.scrollBehavior = 'auto';
    const frame = () => new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done)));
    const middle = r => r.top + r.height / 2;
    const covered = [];
    const nodes = [...document.querySelectorAll('aside .news-sidebar :is(a[href], button, input):not([tabindex="-1"])')]
        .filter(node => node.getClientRects().length);
    for (const node of nodes) {
        node.scrollIntoView({block: 'nearest', inline: 'nearest'});
        for (const button of document.querySelectorAll('.floating-buttons .floating-btn')) {
            window.scrollBy(0, middle(node.getBoundingClientRect()) - middle(button.getBoundingClientRect()));
            await frame();
            const r = node.getBoundingClientRect();
            const hit = document.elementFromPoint(r.left + r.width / 2, middle(r));
            if (!hit || !(hit === node || node.contains(hit))) {
                covered.push((node.textContent.trim() || node.id).replace(/\\s+/g, ' ').slice(0, 30));
            }
        }
    }
    return covered;
}"""

results = {}
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    for width, pointer in cases:
        touch = {"has_touch": True, "is_mobile": True} if pointer == "toque" else {}
        context = new_context(browser, allow=(base,), viewport={"width": width, "height": 900}, **touch)
        page = context.new_page()
        page.goto(base + "/noticias/", wait_until="load")
        state = page.evaluate(MEASURE)
        state["covered"] = page.evaluate(COVERED)
        results[f"{width} {pointer}"] = state
        context.close()
    browser.close()
print(json.dumps(results))
'''


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass


@pytest.fixture(scope="module")
def geometry():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_QuietHandler, directory=str(SITE_DIR)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        completed = subprocess.run(
            [sys.executable, "-c", PROBE, f"http://127.0.0.1:{server.server_port}",
             json.dumps([[width, pointer] for width, pointer in STACKED_CASES]
                        + [[width, "mouse"] for width in TWO_COLUMN_WIDTHS])],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=180,
            env=subprocess_env(),
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert completed.returncode == 0, completed.stderr
    return {(int(key.split()[0]), key.split()[1]): state for key, state in json.loads(completed.stdout).items()}


def _edges(box):
    return round(box["left"], 2), round(box["right"], 2)


def _assert_common(state, width, names):
    assert state["innerWidth"] == width and state["clientWidth"] == width, state
    assert state["overflowX"] <= 0, state["overflowX"]
    assert [block["name"] for block in state["blocks"]] == names, state["blocks"]
    assert state["covered"] == [], f"@{width}: botões flutuantes sobre o centro de {state['covered']}"


@pytest.mark.parametrize("width,pointer", STACKED_CASES, ids=[f"{w}-{p}" for w, p in STACKED_CASES])
def test_stacked_sidebar_blocks_share_the_edges_of_the_other_cards(geometry, width, pointer):
    state = geometry[(width, pointer)]
    _assert_common(state, width, ["Pesquisar notícias", "Categorias"])
    # Empilhada: a lateral vem antes da lista, como no HTML.
    assert state["aside"]["bottom"] <= state["listColumn"]["top"] + TOLERANCE, (state["aside"], state["listColumn"])

    reference = state["sobre"]
    for name in ("orientacao", "card"):
        assert _edges(state[name]) == pytest.approx(_edges(reference), abs=TOLERANCE), (name, state[name], reference)
    for block in state["blocks"]:
        assert block["left"] == pytest.approx(reference["left"], abs=TOLERANCE), (block, reference)
        assert block["right"] == pytest.approx(reference["right"], abs=TOLERANCE), (
            f"@{width} {pointer}: '{block['name']}' termina em {block['right']:.2f} px, "
            f"'Sobre o conteúdo' e 'Orientação técnica' em {reference['right']:.2f} px"
        )


@pytest.mark.parametrize("width", TWO_COLUMN_WIDTHS)
def test_two_column_sidebar_keeps_the_grid_edges(geometry, width):
    state = geometry[(width, "mouse")]
    _assert_common(state, width, ["Pesquisar notícias", "Categorias", "Ordenar notícias", "Atendimento técnico"])
    aside, column, sobre = state["aside"], state["listColumn"], state["sobre"]
    # Lado a lado, no topo da seção.
    assert aside["top"] == pytest.approx(column["top"], abs=TOLERANCE), (aside, column)
    assert aside["right"] < column["left"], (aside, column)

    for block in state["blocks"]:
        assert _edges(block) == pytest.approx(_edges(aside), abs=TOLERANCE), (block, aside)
    assert aside["left"] == pytest.approx(sobre["left"], abs=TOLERANCE), (aside, sobre)
    for name in ("orientacao", "card"):
        assert _edges(state[name]) == pytest.approx(_edges(column), abs=TOLERANCE), (name, state[name], column)
    assert column["right"] == pytest.approx(sobre["right"], abs=TOLERANCE), (column, sobre)
