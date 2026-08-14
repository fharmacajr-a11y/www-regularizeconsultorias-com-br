import base64
import functools
import subprocess
import sys
import threading
import textwrap
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
MAIN_PATHS = (ROOT / "assets/js/main.js", ROOT / "assets/js/main.min.js")
INITIAL_VISIBLE_LIMIT = 5


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass


@pytest.fixture(scope="module")
def site_url():
    handler = functools.partial(_QuietHandler, directory=str(ROOT))
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
    for index in range(7):
        updated = ' data-updated="2030-01-01T00:00:00-03:00"' if index == 6 else ""
        compact = " news-card-compact" if index >= INITIAL_VISIBLE_LIMIT else ""
        cards.append(
            f'<article class="news-card{compact}" data-news-card '
            f'data-category="categoria" data-title="Card {index}"{updated}>'
            f'<time datetime="2026-01-{index + 1:02d}T00:00:00-03:00"></time>'
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
    assert "updateCardLayouts(matchingCards);" in source
    assert source.index("sortArticles();", source.index("updateCategoryFilters();")) < source.index(
        "updateResults();", source.index("updateCategoryFilters();")
    )


def test_layout_uses_sorted_result_position_instead_of_original_dom_position(site_url):
    fixture = base64.b64encode(_fixture_html(site_url).encode("utf-8")).decode("ascii")
    script = textwrap.dedent(
        '''
        import base64
        import sys
        from playwright.sync_api import sync_playwright

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
            page = browser.new_page()
            page.set_content(html, wait_until="load")

            newest = card_state(page)
            assert newest[0]["title"] == "Card 6"
            assert sum(not card["hidden"] for card in newest) == 5
            assert all(not card["compact"] for card in newest[:5])
            assert newest[5]["hidden"] and newest[5]["compact"]

            page.locator("[data-news-sort='asc']").click()
            oldest = card_state(page)
            assert oldest[0]["title"] == "Card 0"
            assert sum(not card["hidden"] for card in oldest) == 5
            assert all(not card["compact"] for card in oldest[:5])
            assert oldest[5]["hidden"] and oldest[5]["compact"]

            page.locator("[data-news-sort='desc']").click()
            page.locator("#btn-carregar-mais").click()
            expanded = card_state(page)
            assert all(not card["hidden"] for card in expanded)
            assert all(not card["compact"] for card in expanded[:5])
            assert all(card["compact"] for card in expanded[5:])
            browser.close()
        '''
    )
    completed = subprocess.run(
        [sys.executable, "-c", script, fixture],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
