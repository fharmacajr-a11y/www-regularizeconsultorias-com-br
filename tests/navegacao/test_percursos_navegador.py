"""Percursos e interações no Chromium, conferidos pelo que fica na tela.

- percursos: Home → Serviços → Contato → WhatsApp, e Home → manual → orçamento
  → catálogo → POP SNCR → serviço SNCR. Os links de WhatsApp abrem a página
  /whatsapp/, que redireciona; o wa.me é interceptado e nada é enviado.
- ancoras: o destino de "Ver catálogo" e de /servicos/#servico-sncr para abaixo
  da faixa regulatória e da navbar fixas.
- carrossel: setas e Tab na vitrine de Manuais da home; cada card focado fica
  inteiro na área visível.
- noticias: busca sem acento, categoria + busca, vazio, ordenação, "Ver mais"
  com o foco no primeiro card revelado e a coluna fixa abaixo do cabeçalho.
- modal: a imagem ampliada do Comunicado prende o foco em "Fechar".

Cada modo roda num subprocesso, como em layout/test_rodape_espaco.py.
"""
import json
import os
import re
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from support import SITE_DIR


WHATSAPP_NUMBER = "5519996275900"

SETTLE_JS = """async () => {
    // Espera a rolagem (suave ou por snap) parar por 200 ms.
    const position = () => [window.scrollY].concat(
        [...document.querySelectorAll('[data-home-manuals-carousel]')].map(node => node.scrollLeft)
    ).join(',');
    let last = position();
    let stableSince = performance.now();
    const started = performance.now();
    while (performance.now() - stableSince < 200 && performance.now() - started < 4000) {
        await new Promise(done => setTimeout(done, 50));
        const current = position();
        if (current !== last) { last = current; stableSince = performance.now(); }
    }
}"""
HEADER_BOTTOM_JS = "() => document.getElementById('navbar').getBoundingClientRect().bottom"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass


def _settle(page):
    page.evaluate(SETTLE_JS)


def _whatsapp_message(context, page, link):
    """Clica no link, segue o redirecionamento da página /whatsapp/ e devolve o texto do wa.me."""
    requests = []

    def intercept(route):
        requests.append(route.request.url)
        route.abort()

    context.route(re.compile(r"https://wa\.me/.*"), intercept)
    with context.expect_page() as popup_info:
        link.click()
    popup = popup_info.value
    for _ in range(50):
        if requests:
            break
        page.wait_for_timeout(100)
    popup.close()
    context.unroute(re.compile(r"https://wa\.me/.*"))
    assert requests, "a página /whatsapp/ não redirecionou para o wa.me"
    target = urlsplit(requests[0])
    assert (target.netloc, target.path) == ("wa.me", f"/{WHATSAPP_NUMBER}"), requests[0]
    sent = parse_qs(target.query).get("text", [""])[0]
    expected = parse_qs(urlsplit(link.get_attribute("href")).query).get("text", [""])[0]
    assert sent == expected, (sent, expected)
    return sent


def _percursos(browser, base):
    failures = []
    for width, height in ((390, 844), (1440, 900)):
        context = browser.new_context(viewport={"width": width, "height": height})
        page = context.new_page()
        label = f"@{width}"

        page.goto(base + "/")
        page.get_by_role("link", name="Conheça Nossos Serviços").click()
        page.wait_for_url("**/servicos/")
        if "Serviços especializados" not in page.locator("h1").inner_text():
            failures.append(f"{label}: 'Conheça Nossos Serviços' não abriu Serviços")

        if width < 768:
            page.locator("#menu-toggle").click()
            page.locator("#mobile-menu a[href='/contato/']").click()
        else:
            page.locator("#navbar nav[aria-label='Navegação principal'] a[href='/contato/']").click()
        page.wait_for_url("**/contato/")
        message = _whatsapp_message(context, page, page.get_by_role("link", name="Conversar no WhatsApp"))
        if "solicitar uma análise" not in message:
            failures.append(f"{label}: mensagem do Contato inesperada: {message}")

        page.goto(base + "/")
        page.locator(".home-manuals-card[href='/manuais-e-pops/manual-boas-praticas-drogaria/']").click()
        page.wait_for_url("**/manuais-e-pops/manual-boas-praticas-drogaria/")
        quote = page.locator(".manuals-hero-actions a[href^='/whatsapp/']")
        message = _whatsapp_message(context, page, quote)
        if "orçamento" not in message or "Drogarias e Farmácias" not in message:
            failures.append(f"{label}: orçamento do manual com mensagem inesperada: {message}")

        page.locator("nav[aria-label='Breadcrumb'] a[href='/manuais-e-pops/']").click()
        page.wait_for_url("**/manuais-e-pops/")
        page.locator(".manuals-filter-dropdown summary").click()
        page.locator(".manuals-filter-dropdown-panel a[href='/manuais-e-pops/pop-sncr/']").click()
        page.wait_for_url("**/manuais-e-pops/pop-sncr/")
        page.locator("a[href='/servicos/#servico-sncr']").first.click()
        page.wait_for_url("**/servicos/#servico-sncr")
        _settle(page)
        top = page.locator("#servico-sncr").evaluate("node => node.getBoundingClientRect().top")
        if top < page.evaluate(HEADER_BOTTOM_JS) or top > height:
            failures.append(f"{label}: serviço SNCR fora da área visível após o link do POP (topo {top:.0f})")
        context.close()
    return failures


def _ancoras(browser, base):
    failures = []
    for width, height in ((320, 844), (390, 844), (768, 1024), (1440, 900)):
        context = browser.new_context(viewport={"width": width, "height": height})
        page = context.new_page()
        page.goto(base + "/manuais-e-pops/")
        page.locator("a[href='#catalogo']").click()
        _settle(page)
        header = page.evaluate(HEADER_BOTTOM_JS)
        top = page.locator("#catalogo").evaluate("node => node.getBoundingClientRect().top")
        if not header <= top <= header + 32:
            failures.append(f"@{width}: catálogo com topo em {top:.0f} px; o cabeçalho termina em {header:.0f} px")

        page.goto(base + "/servicos/#servico-sncr")
        page.wait_for_load_state("load")
        _settle(page)
        header = page.evaluate(HEADER_BOTTOM_JS)
        top = page.locator("#servico-sncr").evaluate("node => node.getBoundingClientRect().top")
        if not header <= top <= height - 100:
            failures.append(f"@{width}: #servico-sncr com topo em {top:.0f} px; o cabeçalho termina em {header:.0f} px")
        context.close()
    return failures


CAROUSEL_STATE_JS = """() => {
    const carousel = document.querySelector('[data-home-manuals-carousel]');
    const box = carousel.getBoundingClientRect();
    const cards = [...carousel.querySelectorAll('.home-manuals-card')];
    const whole = cards.map((card, index) => [card.getBoundingClientRect(), index])
        .filter(([rect]) => rect.left >= box.left - 1 && rect.right <= box.right + 1)
        .map(([, index]) => index);
    const active = document.activeElement;
    const focused = cards.indexOf(active);
    const rect = active.getBoundingClientRect();
    return {whole, focused, focusedVisible: Math.min(rect.right, box.right) - Math.max(rect.left, box.left), focusedWidth: rect.width};
}"""


def _carrossel(browser, base):
    failures = []
    for width in (320, 360, 600, 1024, 1440):
        context = browser.new_context(viewport={"width": width, "height": 900})
        page = context.new_page()
        page.goto(base + "/")
        page.locator(".home-manuals-carousel-shell").scroll_into_view_if_needed()
        label = f"@{width}"

        page.locator("[data-home-manuals-next]").click()
        _settle(page)
        state = page.evaluate(CAROUSEL_STATE_JS)
        if not state["whole"] or state["whole"][0] != 1:
            failures.append(f"{label}: a seta seguinte não avançou um card ({state['whole']})")
        page.locator("[data-home-manuals-prev]").click()
        _settle(page)
        state = page.evaluate(CAROUSEL_STATE_JS)
        if not state["whole"] or state["whole"][0] != 0:
            failures.append(f"{label}: a seta anterior não voltou ao primeiro card ({state['whole']})")

        page.locator("[data-home-manuals-prev]").focus()
        for expected in range(9):
            page.keyboard.press("Tab")
            _settle(page)
            state = page.evaluate(CAROUSEL_STATE_JS)
            if state["focused"] != expected:
                failures.append(f"{label}: Tab {expected + 1} focou o card {state['focused']}")
                break
            if state["focusedVisible"] < state["focusedWidth"] - 1:
                failures.append(
                    f"{label}: card {expected + 1} focado com {state['focusedVisible']:.0f} de "
                    f"{state['focusedWidth']:.0f} px visíveis"
                )
        context.close()
    return failures


NEWS_STATE_JS = """() => {
    const cards = [...document.querySelectorAll('#news-article-list [data-news-card]')];
    const visible = cards.filter(card => card.getClientRects().length);
    const stamp = card => Date.parse(card.dataset.updated || card.querySelector('time').getAttribute('datetime'));
    return {
        count: document.getElementById('news-result-count').textContent.trim(),
        visible: visible.length,
        categories: [...new Set(visible.map(card => card.dataset.category))],
        // Mesmo texto que a busca do main.js percorre.
        texts: visible.map(card => [card.dataset.title, card.dataset.summary, card.dataset.category,
            card.dataset.keywords, card.dataset.tags, card.textContent].join(' ').normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase()),
        stamps: visible.map(stamp),
        empty: !document.getElementById('news-empty-state').classList.contains('hidden'),
        loadMore: !document.getElementById('carregar-mais-wrapper').classList.contains('hidden'),
    };
}"""


def _noticias(browser, base):
    failures = []
    for width, height in ((390, 844), (1440, 900)):
        context = browser.new_context(viewport={"width": width, "height": height})
        page = context.new_page()
        page.goto(base + "/noticias/")
        label = f"@{width}"
        state = lambda: page.evaluate(NEWS_STATE_JS)

        initial = state()
        if initial["visible"] != 5 or not initial["loadMore"]:
            failures.append(f"{label}: listagem inicial com {initial['visible']} cards e 'Ver mais' {initial['loadMore']}")

        page.locator("#news-search").fill("vigilancia")
        plain = state()
        page.locator("#news-search").fill("VIGILÂNCIA")
        accented = state()
        if plain["count"] != accented["count"] or plain["count"].startswith("0 "):
            failures.append(f"{label}: busca sem acento '{plain['count']}' x com acento '{accented['count']}'")

        page.locator("#news-search").fill("termo-que-nao-existe")
        empty = state()
        if not empty["empty"] or empty["visible"] or empty["loadMore"] or not empty["count"].startswith("0 "):
            failures.append(f"{label}: estado vazio incorreto {empty}")

        page.locator("#news-search").fill("portaria")
        page.locator("[data-news-category='farmacia-popular']").click()
        combined = state()
        if combined["categories"] != ["farmacia-popular"] or not all("portaria" in text for text in combined["texts"]):
            failures.append(f"{label}: categoria + busca misturou resultados {combined['categories']}")

        page.locator("#news-search").fill("")
        page.locator("[data-news-category='todos']").click()
        page.locator("[data-news-sort='asc']").click()
        ascending = state()["stamps"]
        page.locator("[data-news-sort='desc']").click()
        descending = state()["stamps"]
        if ascending != sorted(ascending) or descending != sorted(descending, reverse=True):
            failures.append(f"{label}: ordenação fora da data efetiva")

        sixth_link = page.evaluate(
            "() => [...document.querySelectorAll('#news-article-list [data-news-card]')][5].querySelector('a[href]').getAttribute('href')"
        )
        page.locator("#btn-carregar-mais").focus()
        page.keyboard.press("Enter")
        expanded = state()
        focused = page.evaluate("() => document.activeElement.getAttribute('href')")
        if expanded["visible"] != len(expanded["stamps"]) or expanded["loadMore"]:
            failures.append(f"{label}: 'Ver mais' não revelou toda a lista")
        if focused != sixth_link:
            failures.append(f"{label}: depois de 'Ver mais' o foco foi para {focused!r}, não para {sixth_link!r}")

        if width >= 1024:
            page.evaluate("() => window.scrollTo(0, 3000)")
            _settle(page)
            top = page.locator("aside .sticky").evaluate("node => node.getBoundingClientRect().top")
            if top < page.evaluate(HEADER_BOTTOM_JS):
                failures.append(f"{label}: coluna de filtros presa sob o cabeçalho (topo {top:.0f} px)")
        context.close()
    return failures


def _modal(browser, base):
    failures = []
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    page.goto(base + "/comunicado/")
    trigger = page.locator("[data-aviso-image-trigger]").first
    history = trigger.locator("xpath=ancestor::*[@data-aviso-history-card][1]")
    if history.count() and not trigger.is_visible():
        history.locator("[data-aviso-history-toggle]").click()
    trigger.focus()
    page.keyboard.press("Enter")
    page.locator("#aviso-imagem-modal").wait_for(state="visible")
    for key in ("Tab", "Shift+Tab", "Tab"):
        page.keyboard.press(key)
        inside = page.evaluate("() => !!document.activeElement.closest('#aviso-imagem-modal')")
        if not inside:
            failures.append(f"{key} levou o foco para fora do modal aberto")
    page.keyboard.press("Escape")
    if page.locator("#aviso-imagem-modal").is_visible():
        failures.append("Escape não fechou o modal")
    if not page.evaluate("() => document.activeElement.hasAttribute('data-aviso-image-trigger')"):
        failures.append("o foco não voltou para a imagem que abriu o modal")
    context.close()
    return failures


MODES = {"percursos": _percursos, "ancoras": _ancoras, "carrossel": _carrossel, "noticias": _noticias, "modal": _modal}


def _collect(mode):
    from playwright.sync_api import sync_playwright

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(SITE_DIR)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                return MODES[mode](browser, f"http://127.0.0.1:{server.server_port}")
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _run(mode):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), mode],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=240,
        env=env,
    )
    assert completed.returncode == 0, completed.stderr
    failures = json.loads(completed.stdout)["failures"]
    assert not failures, "\n".join(failures)


def test_home_services_contact_and_manual_quote_flows():
    _run("percursos")


def test_anchor_targets_land_below_the_fixed_header():
    _run("ancoras")


def test_home_manuals_carousel_by_arrows_and_keyboard():
    _run("carrossel")


def test_news_listing_search_filters_sort_and_load_more_focus():
    _run("noticias")


def test_comunicado_image_modal_keeps_keyboard_focus():
    _run("modal")


if __name__ == "__main__":
    print(json.dumps({"failures": _collect(sys.argv[1])}, ensure_ascii=False))
