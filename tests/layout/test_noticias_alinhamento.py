"""Bordas da coluna lateral das Notícias em relação aos outros cards.

Abaixo de 1024 px a coluna vem depois da lista e cada bloco dela (Pesquisar,
Categorias, Ordenar, Atendimento técnico) tem de ocupar a mesma largura útil
de "Orientação técnica", dos cards de notícia e de "Sobre o conteúdo". Até a
rodada de 04/10/2026 um margin-right só da coluna a terminava 56 a 60 px antes
da borda dos demais. A partir de 1024 px ficam as duas colunas do grid: a
lateral na borda esquerda de "Sobre o conteúdo" e a lista na borda direita.
"""
import json
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from support import SITE_DIR


STACKED_WIDTHS = (320, 360, 390, 414, 639, 640, 767, 768, 940, 944, 950, 960, 1023)
TWO_COLUMN_WIDTHS = (1024, 1279, 1280, 1440, 1920)
TOLERANCE = 0.5

PROBE = r'''
import json
import sys
from playwright.sync_api import sync_playwright

base, widths = sys.argv[1], json.loads(sys.argv[2])
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
        blocks: [...sidebar.children].map(el => ({
            name: el.querySelector('h2, p').textContent.trim(), ...box(el)})),
        aside: box(sidebar.closest('aside')), listColumn: box(list.parentElement),
        card: box(list.querySelector('[data-news-card]')),
        orientacao: box(kicker('Orientação técnica')),
        sobre: box(kicker('Sobre o conteúdo')),
    };
}"""
# Com cada botão flutuante na altura de cada controle da lateral, o centro do
# controle continua sendo dele.
COVERED = """async () => {
    document.documentElement.style.scrollBehavior = 'auto';
    const frame = () => new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done)));
    const middle = r => r.top + r.height / 2;
    const covered = [];
    for (const node of document.querySelectorAll('aside .news-sidebar :is(a[href], button, input)')) {
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
    for width in widths:
        context = browser.new_context(viewport={"width": width, "height": 900})
        page = context.new_page()
        page.route("**/*", lambda route: route.continue_()
                   if route.request.url.startswith(base) else route.abort())
        page.goto(base + "/noticias/", wait_until="load")
        state = page.evaluate(MEASURE)
        state["covered"] = page.evaluate(COVERED)
        results[width] = state
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
             json.dumps(STACKED_WIDTHS + TWO_COLUMN_WIDTHS)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=180,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert completed.returncode == 0, completed.stderr
    return {int(width): state for width, state in json.loads(completed.stdout).items()}


def _edges(box):
    return round(box["left"], 2), round(box["right"], 2)


def _assert_common(state, width):
    assert state["innerWidth"] == width and state["clientWidth"] == width, state
    assert state["overflowX"] <= 0, state["overflowX"]
    names = [block["name"] for block in state["blocks"]]
    assert names == ["Pesquisar notícias", "Categorias", "Ordenar notícias", "Atendimento técnico"], names
    assert state["covered"] == [], f"@{width}: botões flutuantes sobre o centro de {state['covered']}"


@pytest.mark.parametrize("width", STACKED_WIDTHS)
def test_stacked_sidebar_blocks_share_the_edges_of_the_other_cards(geometry, width):
    state = geometry[width]
    _assert_common(state, width)
    # Empilhada: a lateral vem depois da lista.
    assert state["aside"]["top"] >= state["listColumn"]["bottom"] - TOLERANCE, (state["aside"], state["listColumn"])

    reference = state["sobre"]
    for name in ("orientacao", "card"):
        assert _edges(state[name]) == pytest.approx(_edges(reference), abs=TOLERANCE), (name, state[name], reference)
    for block in state["blocks"]:
        assert block["left"] == pytest.approx(reference["left"], abs=TOLERANCE), (block, reference)
        assert block["right"] == pytest.approx(reference["right"], abs=TOLERANCE), (
            f"@{width}: '{block['name']}' termina em {block['right']:.2f} px, "
            f"'Sobre o conteúdo' e 'Orientação técnica' em {reference['right']:.2f} px"
        )


@pytest.mark.parametrize("width", TWO_COLUMN_WIDTHS)
def test_two_column_sidebar_keeps_the_grid_edges(geometry, width):
    state = geometry[width]
    _assert_common(state, width)
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
