"""Contrato do main.js para os cards de /noticias/: ordem, "Ver mais" e formato.

Dois modelos (12/10/2026, revisão v2): os cinco primeiros do resultado ordenado ou filtrado perdem
news-card-compact e usam o modelo maior; do sexto em diante o compacto de 3b1694f permanece. "Ver mais" só revela.

Data (R2): o card leva a data válida da matéria com a precisão dela; uma data só com o dia (AAAA-MM-DD) conta, para
ordenar, como o início desse dia em Brasília (-03:00). Sem essa regra, o navegador lê AAAA-MM-DD como meia-noite UTC,
21h do dia anterior em Brasília, e a data subia ou descia em relação a cards do dia anterior. Empates mantêm a ordem do
HTML (a ordenação do Array é estável).
"""
import base64
import functools
import subprocess
import sys
import threading
import textwrap
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from support import SITE_DIR, subprocess_env


ROOT = Path(__file__).parents[2]
MAIN_PATHS = (ROOT / "assets/js/main.js", ROOT / "assets/js/main.min.js")
INITIAL_VISIBLE_LIMIT = 5
# (título, datetime, data-updated). O card 4 tem só o dia; o 3 é da noite anterior e o 5, da manhã do mesmo dia.
CARDS = (
    ("Card 0", "2026-01-01T00:00:00-03:00", None),
    ("Card 1", "2026-01-02T00:00:00-03:00", None),
    ("Card 2", "2026-01-03T00:00:00-03:00", None),
    ("Card 3", "2026-01-06T22:00:00-03:00", None),
    ("Card 4", "2026-01-07", None),
    ("Card 5", "2026-01-07T08:00:00-03:00", None),
    ("Card 6", "2026-01-01T00:00:00-03:00", "2030-01-01T00:00:00-03:00"),
)


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass


@pytest.fixture(scope="module")
def site_url():
    handler = functools.partial(_QuietHandler, directory=str(SITE_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _fixture_html(site_url):
    cards = []
    for title, moment, updated in CARDS:
        updated_attr = f' data-updated="{updated}"' if updated else ""
        cards.append(
            f'<article class="news-card news-card-compact" data-news-card '
            f'data-category="categoria" data-title="{title}"{updated_attr}>'
            f'<time datetime="{moment}"></time>'
            "</article>"
        )

    return f"""
        <!doctype html>
        <style>.hidden {{ display: none; }}</style>
        <input id="news-search">
        <button data-news-category="todos"><span>Todos</span><span>0</span></button>
        <button data-news-category="categoria"><span>Categoria</span><span>0</span></button>
        <button data-news-sort="desc" aria-pressed="true">Mais nova</button>
        <button data-news-sort="asc" aria-pressed="false">Mais velha</button>
        <p id="news-result-count"></p>
        <div id="news-empty-state" class="hidden"></div>
        <div id="news-article-list">{''.join(cards)}</div>
        <div id="carregar-mais-wrapper" class="hidden">
          <button id="btn-carregar-mais">Ver mais noticias</button>
        </div>
        <script src="{site_url}/assets/js/main.min.js"></script>
    """


def test_news_card_contract_is_identical_in_both_javascript_files():
    assert MAIN_PATHS[0].read_bytes() == MAIN_PATHS[1].read_bytes()
    source = MAIN_PATHS[0].read_text(encoding="utf-8")
    assert "var INITIAL_VISIBLE_LIMIT = 5;" in source
    assert "classList.toggle('news-card-compact', index >= 5)" in source
    assert "function parseCardDate(value)" in source
    assert source.index("sortArticles();", source.index("updateCategoryFilters();")) < source.index(
        "updateResults();", source.index("updateCategoryFilters();")
    )


def test_order_uses_the_card_date_precision_and_the_first_five_use_the_larger_model(site_url):
    fixture = base64.b64encode(_fixture_html(site_url).encode("utf-8")).decode("ascii")
    script = textwrap.dedent(
        '''
        import base64
        import sys
        from playwright.sync_api import sync_playwright

        from support import new_page

        html = base64.b64decode(sys.argv[1]).decode("utf-8")

        def card_state(page):
            return page.locator("[data-news-card]").evaluate_all(
                """cards => cards.map(card => ({
                    title: card.dataset.title,
                    hidden: card.classList.contains('hidden'),
                    compact: card.classList.contains('news-card-compact')
                }))"""
            )

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = new_page(browser)
            page.set_content(html, wait_until="load")

            newest = card_state(page)
            assert [card["title"] for card in newest] == [
                "Card 6", "Card 5", "Card 4", "Card 3", "Card 2", "Card 1", "Card 0"], newest
            assert sum(not card["hidden"] for card in newest) == 5
            assert [card["compact"] for card in newest] == [False, False, False, False, False, True, True]
            assert newest[5]["hidden"] and newest[6]["hidden"]

            page.locator("[data-news-sort='asc']").click()
            oldest = card_state(page)
            assert [card["title"] for card in oldest] == [
                "Card 0", "Card 1", "Card 2", "Card 3", "Card 4", "Card 5", "Card 6"], oldest
            assert sum(not card["hidden"] for card in oldest) == 5
            assert [card["compact"] for card in oldest] == [False, False, False, False, False, True, True]

            page.locator("[data-news-sort='desc']").click()
            page.locator("#btn-carregar-mais").click()
            expanded = card_state(page)
            assert all(not card["hidden"] for card in expanded)
            assert [card["compact"] for card in expanded] == [False, False, False, False, False, True, True]

            page.fill("#news-search", "Card 4")
            searched = [card for card in card_state(page) if not card["hidden"]]
            assert [card["title"] for card in searched] == ["Card 4"]
            assert searched[0]["compact"] is False
            browser.close()
        '''
    )
    completed = subprocess.run(
        [sys.executable, "-c", script, fixture],
        capture_output=True,
        text=True,
        timeout=30,
        env=subprocess_env(),
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
