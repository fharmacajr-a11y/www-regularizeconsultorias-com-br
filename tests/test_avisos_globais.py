import functools
import re
import threading
from collections import Counter
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).parents[1]
COMUNICADO_PATH = ROOT / "comunicado" / "index.html"
MAIN_PATHS = (ROOT / "assets/js/main.js", ROOT / "assets/js/main.min.js")
CSS_PATHS = (
    ROOT / "assets/css/components.css",
    ROOT / "assets/css/custom.css",
    ROOT / "assets/css/custom.min.css",
)
CURRENT_STORAGE_VERSION = "2026-08-06-avisos-7"
REPRESENTATIVE_ROUTES = (
    "/",
    "/farmacia-popular/",
    "/noticias/anvisa-alerta-soroterapia-promessas-sem-evidencia/",
    "/comunicado/",
)
VIEWPORT_WIDTHS = (390, 767, 768, 820, 899, 900, 1180)


class _Node:
    def __init__(self, tag="root", attrs=(), parent=None):
        self.tag = tag
        self.attrs = dict(attrs)
        self.parent = parent
        self.children = []
        self.text_parts = []

    def has_class(self, class_name):
        return class_name in self.attrs.get("class", "").split()

    def descendants(self):
        for child in self.children:
            yield child
            yield from child.descendants()

    def inside_id(self, element_id):
        node = self
        while node:
            if node.attrs.get("id") == element_id:
                return True
            node = node.parent
        return False

    def text(self):
        return "".join(self.text_parts + [child.text() for child in self.children]).strip()


class _TreeParser(HTMLParser):
    VOID_ELEMENTS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__()
        self.root = _Node()
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = _Node(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in self.VOID_ELEMENTS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        node = _Node(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                self.stack = self.stack[:index]
                return

    def handle_data(self, data):
        self.stack[-1].text_parts.append(data)


def _parse_html(path):
    parser = _TreeParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.root


def _public_html_paths():
    ignored_roots = {".git", ".pytest_cache", ".venv", ".venv-1", "node_modules", "__pycache__", "tmp", "temp"}
    return sorted(
        path
        for path in ROOT.rglob("*.html")
        if not any(part in ignored_roots or part.endswith(".cache") for part in path.relative_to(ROOT).parts)
        and path.relative_to(ROOT).as_posix() != "noticias/template-noticia.html"
        and path.relative_to(ROOT).as_posix() != "whatsapp/index.html"
    )


def _navbar_links(root):
    navbars = [node for node in root.descendants() if node.attrs.get("id") == "navbar"]
    if not navbars:
        return None
    assert len(navbars) == 1
    return [
        node
        for node in navbars[0].descendants()
        if node.tag == "a" and node.attrs.get("href") == "/comunicado/"
    ]


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


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        yield browser
        browser.close()


def _active_articles_html(count):
    articles = "".join('<article data-status="urgent"></article>' for _ in range(count))
    return f'<!doctype html><div id="avisos-lista">{articles}</div>'


def _notice_response(count):
    def fulfill(route):
        route.fulfill(status=200, content_type="text/html", body=_active_articles_html(count))

    return fulfill


def _badge_texts(page):
    return page.locator(".aviso-badge").all_text_contents()


def test_comunicado_has_seven_active_notices_and_two_static_badges():
    root = _parse_html(COMUNICADO_PATH)
    notice_lists = [node for node in root.descendants() if node.attrs.get("id") == "avisos-lista"]
    assert len(notice_lists) == 1
    articles = [node for node in notice_lists[0].descendants() if node.tag == "article"]
    inactive = [
        article
        for article in articles
        if article.attrs.get("data-status", "").casefold() == "resolved"
        or "data-placeholder" in article.attrs
    ]
    active = [article for article in articles if article not in inactive]
    badges = [node for node in root.descendants() if node.has_class("aviso-badge")]

    assert len(articles) == 11
    assert len(active) == 7
    assert Counter(article.attrs.get("data-status", "").casefold() for article in inactive) == {"resolved": 4}
    assert all("data-placeholder" not in article.attrs for article in articles)
    assert len(badges) == 2
    assert [badge.text() for badge in badges] == ["7", "7"]


def test_comunicado_editorial_organization_and_active_notice_content():
    root = _parse_html(COMUNICADO_PATH)
    notice_list = next(node for node in root.descendants() if node.attrs.get("id") == "avisos-lista")
    articles = [node for node in notice_list.descendants() if node.tag == "article"]
    active = [
        article
        for article in articles
        if article.attrs.get("data-status", "").casefold() != "resolved"
    ]
    active_text = " ".join(article.text() for article in active)
    historical_text = " ".join(article.text() for article in articles if article not in active)
    headings = [node.text() for node in notice_list.descendants() if node.tag == "h2"]
    renewal = active[0]
    renewal_links = [node.attrs.get("href") for node in renewal.descendants() if node.tag == "a"]

    assert len(active) == 7
    assert len(articles) - len(active) == 4
    assert "Histórico / encerrados" in headings
    assert "ciclo atual de renovação termina em 31 de agosto" in renewal.text()
    assert "31/08/2026" in renewal.text()
    assert renewal_links == ["/noticias/farmacia-popular-portaria-12091-2026-novas-regras/"]
    assert "suspensao-temporaria-recadastramento-sifap" not in " ".join(renewal_links)
    assert "período eleitoral" in active_text
    assert "30/09/2026" in active_text
    assert "funcionalidades eletrônicas" in active_text
    assert "28/07/2026" in active_text
    assert "instabilidade observada" not in active_text
    assert "junho de 2026" in active_text
    assert "ciclo de maio de 2026" in historical_text
    assert "13/05/2026" in historical_text
    assert "voltou a funcionar" in historical_text
    assert "SNGPC" in historical_text


def test_comunicado_active_dates_order_and_historical_visual_states():
    source = COMUNICADO_PATH.read_text(encoding="utf-8")
    root = _parse_html(COMUNICADO_PATH)
    notice_list = next(node for node in root.descendants() if node.attrs.get("id") == "avisos-lista")
    articles = [node for node in notice_list.descendants() if node.tag == "article"]
    active = [
        article
        for article in articles
        if article.attrs.get("data-status", "").casefold() != "resolved"
    ]
    historical = [article for article in articles if article not in active]
    titles = [next(node.text() for node in article.descendants() if node.tag == "h3") for article in active]
    timestamps = [article.attrs.get("data-effective-at") for article in active]

    assert titles == [
        "Farmácia Popular: ciclo atual de renovação termina em 31 de agosto",
        "SNCR: funcionalidades eletrônicas seguem em implantação até 30/09/2026",
        "Anvisa suspende medicamento e proíbe produtos irregulares",
        "Farmácia Popular: confira municípios com vagas para credenciamento",
        "Farmácia Popular: atenção aos materiais no período eleitoral",
        "Farmácia Popular: confira as listas EAN vigentes e os controles de prescrição",
        "Cadastro Anvisa/Gov.br: atenção a empresas, usuários e perfis de acesso",
    ]
    assert all(timestamp for timestamp in timestamps)
    assert all(len([node for node in article.descendants() if node.tag == "time"]) == 1 for article in active)
    assert timestamps[1:] == sorted(timestamps[1:], reverse=True)
    assert "URGENTE" in active[4].text()

    useful_badge = next(node for node in active[5].descendants() if node.tag == "span" and node.text() == "ÚTIL")
    useful_cta = next(node for node in active[5].descendants() if node.tag == "a" and "Conferir orientações" in node.text())
    informative_cta = next(node for node in active[6].descendants() if node.tag == "a" and "Leia a notícia completa" in node.text())
    assert {"border-emerald-200", "bg-emerald-50", "text-emerald-700"} <= set(useful_badge.attrs["class"].split())
    assert {"border-emerald-200", "bg-emerald-50"} <= set(active[5].attrs["class"].split())
    informative_to_useful = {
        "comunicado-cta--informativo": "comunicado-cta--util",
        "border-orange-200": "border-emerald-200",
        "text-orange-600": "text-emerald-700",
    }
    assert useful_cta.attrs["class"].split() == [
        informative_to_useful.get(class_name, class_name)
        for class_name in informative_cta.attrs["class"].split()
    ]
    assert "comunicado-util__cta" not in useful_cta.attrs["class"].split()
    assert "bg-white" not in useful_cta.attrs["class"].split()
    assert "bg-emerald-50" not in useful_cta.attrs["class"].split()
    assert ".comunicado-util__cta" not in source
    assert "#avisos-lista .comunicado-cta:hover { border-color: var(--comunicado-cta-hover-border); background-color: var(--comunicado-cta-hover-background); color: var(--comunicado-cta-hover-color); }" in source
    assert "#avisos-lista .comunicado-cta--informativo" in source
    assert "#avisos-lista .comunicado-cta--util" in source

    active_icon_colors = {
        "URGENTE": ("bg-red-100", "text-red-600"),
        "INFORMATIVO": ("bg-orange-100", "text-orange-600"),
        "ATUALIZAÇÃO": ("bg-yellow-100", "text-yellow-600"),
        "ÚTIL": ("bg-emerald-100", "text-emerald-600"),
    }
    assert all(
        any("w-9" in node.attrs.get("class", "").split() for node in article.descendants())
        for article in active
    )
    for article in active:
        badge = next(node for node in article.descendants() if node.tag == "span" and node.text() in active_icon_colors)
        icon_container = next(node for node in article.descendants() if "w-9" in node.attrs.get("class", "").split())
        icon_svg = next(node for node in icon_container.descendants() if node.tag == "svg")
        expected_background, expected_color = active_icon_colors[badge.text()]
        assert expected_background in icon_container.attrs["class"].split()
        assert expected_color in icon_svg.attrs["class"].split()
        assert icon_svg.attrs.get("aria-hidden") == "true"
    assert all("comunicado-historico" in article.attrs.get("class", "").split() for article in historical)
    assert all(
        any("comunicado-historico__meta" in node.attrs.get("class", "").split() for node in article.descendants())
        for article in historical
    )
    assert "HISTÓRICO" in historical[0].text() and "20/05/2026 • 13h00" in historical[0].text()
    assert "HISTÓRICO • maio de 2026" not in historical[0].text()
    assert "ENCERRADO" in historical[1].text() and "18/05/2026 • 08h00" in historical[1].text()
    assert "13/05/2026" in historical[1].text()
    sifap_attention = next(node for node in historical[1].descendants() if node.tag == "strong" and node.text() == "Atenção:")
    assert "text-slate-800" in sifap_attention.attrs["class"].split()
    assert not any(color in sifap_attention.attrs["class"].split() for color in {"text-yellow-600", "text-orange-600", "text-red-600", "text-emerald-600"})
    assert [next(node.text() for node in article.descendants() if node.has_class("comunicado-historico__badge")) for article in historical] == ["HISTÓRICO", "ENCERRADO", "ENCERRADO", "ENCERRADO"]
    assert all("NORMALIZADO" not in article.text() for article in historical)
    assert all("28/04/2026" in article.text() and "12h57" in article.text() for article in historical[2:])
    historical_icons = [
        node
        for article in historical
        for node in article.descendants()
        if node.has_class("comunicado-historico__icon")
    ]
    assert len(historical_icons) == 4
    assert all({"bg-slate-100", "w-9", "h-9"} <= set(node.attrs["class"].split()) for node in historical_icons)
    assert all(
        "text-slate-600" in next(node for node in icon.descendants() if node.tag == "svg").attrs["class"].split()
        for icon in historical_icons
    )
    historical_controls = [node for article in historical for node in article.descendants() if node.tag in {"a", "button"} and "comunicado-historico__control" in node.attrs.get("class", "").split()]
    assert len(historical_controls) == 5
    assert all({"border-slate-300", "text-slate-700", "focus:ring-slate-300"} <= set(node.attrs["class"].split()) for node in historical_controls)
    assert all(not any("blue" in class_name for class_name in node.attrs["class"].split()) for node in historical_controls)
    assert "#avisos-lista .comunicado-historico__control:focus { outline: none; box-shadow: none; }" in source
    assert "#avisos-lista .comunicado-historico__control:focus-visible { outline: 2px solid #475569; outline-offset: 2px; box-shadow: 0 0 0 2px #cbd5e1; }" in source
    assert "#avisos-lista .comunicado-historico__control:active { border-color: #94a3b8; background: #e2e8f0; color: #334155; }" in source
    assert "text-slate-700" in next(node for node in notice_list.descendants() if node.tag == "h2" and node.text() == "Histórico / encerrados").attrs["class"]

    legend_cards = [node for node in root.descendants() if node.has_class("aviso-tipo")]
    assert len(legend_cards) == 6
    assert [next(node.text() for node in card.descendants() if node.tag == "span") for card in legend_cards] == ["Urgente", "Informativo", "ATUALIZAÇÃO", "Útil", "ENCERRADO", "HISTÓRICO"]
    assert all("NORMALIZADO" not in card.text() for card in legend_cards)
    for card in legend_cards[-2:]:
        assert {"bg-slate-50", "border-slate-300"} <= set(card.attrs["class"].split())
        icon = next(node for node in card.descendants() if "w-9" in node.attrs.get("class", "").split())
        assert "text-slate-600" in next(node for node in icon.descendants() if node.tag == "svg").attrs["class"].split()


def test_comunicado_useful_cta_computed_states(site_url, browser):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    try:
        page.goto(f"{site_url}/comunicado/", wait_until="networkidle")
        useful_cta = page.locator('a[href="/noticias/farmacia-popular-listas-ean-junho-2026/"]')
        informative_cta = page.locator('a[href="/noticias/cadastro-anvisa-govbr-transicao-sistemas/"]')

        def computed_state(locator):
            return locator.evaluate(
                """(element) => {
                    const style = getComputedStyle(element);
                    return {
                        hovered: element.matches(':hover'),
                        focusVisible: element.matches(':focus-visible'),
                        transparentBackground: style.backgroundColor === 'rgba(0, 0, 0, 0)',
                        backgroundColor: style.backgroundColor,
                        color: style.color,
                        borderColor: style.borderColor,
                    };
                }"""
            )

        page.mouse.move(0, 0)
        page.wait_for_timeout(250)
        useful_normal = computed_state(useful_cta)
        informative_normal = computed_state(informative_cta)
        assert useful_normal["transparentBackground"]
        assert informative_normal["transparentBackground"]
        assert useful_normal["color"] != informative_normal["color"]
        assert useful_normal["borderColor"] != informative_normal["borderColor"]

        useful_cta.hover()
        page.wait_for_timeout(250)
        useful_hover = computed_state(useful_cta)
        assert useful_hover["hovered"]
        assert not useful_hover["transparentBackground"]
        assert useful_hover["backgroundColor"] != useful_normal["backgroundColor"]
        assert useful_hover["color"] != useful_normal["color"]

        informative_cta.hover()
        page.wait_for_timeout(250)
        informative_hover = computed_state(informative_cta)
        assert informative_hover["hovered"]
        assert not informative_hover["transparentBackground"]
        assert informative_hover["backgroundColor"] != informative_normal["backgroundColor"]
        assert informative_hover["color"] != informative_normal["color"]

        page.mouse.move(0, 0)
        page.wait_for_timeout(250)
        assert computed_state(useful_cta)["transparentBackground"]
        assert computed_state(informative_cta)["transparentBackground"]
        useful_cta.focus()
        page.wait_for_timeout(250)
        useful_focus = computed_state(useful_cta)
        assert useful_focus["focusVisible"]
        assert useful_focus["transparentBackground"]
    finally:
        context.close()


def test_javascript_constants_and_files_are_exactly_equivalent():
    expected_fallback = re.compile(r"^\s*var AVISOS_FALLBACK_COUNT = 7;$", re.MULTILINE)
    expected_version = re.compile(r"^\s*var AVISOS_STORAGE_VERSION = '2026-08-06-avisos-7';$", re.MULTILINE)
    for path in MAIN_PATHS:
        source = path.read_text(encoding="utf-8")
        assert len(expected_fallback.findall(source)) == 1, path
        assert len(expected_version.findall(source)) == 1, path
    assert MAIN_PATHS[0].read_bytes() == MAIN_PATHS[1].read_bytes()


def test_every_public_navbar_has_two_complete_notice_links():
    pages_with_navbar = 0
    for path in _public_html_paths():
        links = _navbar_links(_parse_html(path))
        if links is None:
            continue
        pages_with_navbar += 1
        relative_path = path.relative_to(ROOT)
        assert len(links) == 2, relative_path
        mobile_links = [link for link in links if link.inside_id("mobile-menu")]
        top_links = [link for link in links if not link.inside_id("mobile-menu")]
        assert len(top_links) == 1, relative_path
        assert len(mobile_links) == 1, relative_path
        for link in links:
            badges = [node for node in link.descendants() if node.has_class("aviso-badge")]
            assert len(badges) == 1, relative_path
            assert badges[0].text() == "7", relative_path
            assert badges[0].text() != "3", relative_path
            svgs = [node for node in link.descendants() if node.tag == "svg"]
            assert len(svgs) == 1, relative_path
            assert svgs[0].attrs.get("aria-hidden") == "true", relative_path
            assert "AVISOS!" in link.text(), relative_path
        mobile_classes = mobile_links[0].attrs.get("class", "").split()
        assert "relative" in mobile_classes, relative_path
        assert "gap-2" in mobile_classes, relative_path
    assert pages_with_navbar == 95


def test_tablet_hide_regression_is_absent_and_navbar_rules_remain():
    forbidden = re.compile(
        r'@media\(min-width:768px\)and\(max-width:899px\)\{'
        r'#navbar#mobile-menua\[href="/comunicado/"\]\{display:none!important;?\}\}'
    )
    required = (
        re.compile(r'#navbar>div:first-child>div>nav\{display:none!important;?\}'),
        re.compile(r'#navbar#mobile-menu:not\(\.hidden\)\{display:block!important;?\}'),
        re.compile(r'@media\(min-width:900px\)and\(max-width:1180px\)\{'),
    )
    for path in CSS_PATHS:
        compact = re.sub(r"\s+", "", path.read_text(encoding="utf-8-sig"))
        assert not forbidden.search(compact), path
        assert "@media(max-width:899px){" in compact, path
        for rule in required:
            assert rule.search(compact), f"{path}: {rule.pattern}"


def test_fallback_is_seven_before_delayed_sync(browser, site_url):
    context = browser.new_context()
    context.add_init_script(
        "const originalFetch = window.fetch.bind(window);"
        "window.fetch = (...args) => String(args[0]).endsWith('/comunicado/') ? new Promise(() => {}) : originalFetch(...args);"
    )
    page = context.new_page()
    try:
        page.goto(f"{site_url}/", wait_until="domcontentloaded")
        page.wait_for_function("[...document.querySelectorAll('.aviso-badge')].every(b => b.textContent.trim() === '7')")
        assert _badge_texts(page) == ["7", "7"]
        assert "3" not in _badge_texts(page)
    finally:
        context.close()


def test_old_storage_is_ignored_when_sync_fails(browser, site_url):
    context = browser.new_context()
    context.add_init_script("localStorage.setItem('avisos_count', '3'); localStorage.setItem('avisos_count_version', '2026-05-21-sncr');")
    page = context.new_page()
    page_errors = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    try:
        page.route("**/comunicado/", lambda route: route.abort("failed"))
        page.goto(f"{site_url}/", wait_until="domcontentloaded")
        page.wait_for_function("[...document.querySelectorAll('.aviso-badge')].every(b => b.textContent.trim() === '7')")
        assert _badge_texts(page) == ["7", "7"]
        assert "3" not in _badge_texts(page)
        assert not page_errors
    finally:
        context.close()


def test_successful_sync_persists_seven_and_hides_zero(browser, site_url):
    for count in (7, 0):
        context = browser.new_context()
        page = context.new_page()
        try:
            page.route(
                "**/comunicado/",
                _notice_response(count),
            )
            page.goto(f"{site_url}/", wait_until="domcontentloaded")
            page.wait_for_function(f"localStorage.getItem('avisos_count') === '{count}'")
            assert page.evaluate("localStorage.getItem('avisos_count_version')") == CURRENT_STORAGE_VERSION
            if count:
                assert _badge_texts(page) == ["7", "7"]
                assert all(
                    page.locator(".aviso-badge").nth(index).evaluate("element => getComputedStyle(element).display") == "flex"
                    for index in range(2)
                )
            else:
                assert all(
                    page.locator(".aviso-badge").nth(index).evaluate("element => getComputedStyle(element).display") == "none"
                    for index in range(2)
                )
                assert all(page.locator(".aviso-badge").nth(index).bounding_box() is None for index in range(2))
        finally:
            context.close()


def test_responsive_notice_visibility_matrix(browser, site_url):
    for route in REPRESENTATIVE_ROUTES:
        for width in VIEWPORT_WIDTHS:
            context = browser.new_context(viewport={"width": width, "height": 900})
            page = context.new_page()
            try:
                if route != "/comunicado/":
                    page.route(
                        "**/comunicado/",
                        _notice_response(7),
                    )
                page.goto(f"{site_url}{route}", wait_until="domcontentloaded")
                top = page.locator('#navbar > div:first-child > div > div > a[href="/comunicado/"]')
                toggle = page.locator("#navbar #menu-toggle")
                mobile_menu = page.locator("#navbar #mobile-menu")
                mobile = mobile_menu.locator('a[href="/comunicado/"]')
                assert top.count() == toggle.count() == mobile.count() == 1, (route, width)

                if width < 768:
                    assert not top.is_visible(), (route, width)
                    assert toggle.is_visible(), (route, width)
                    toggle.click()
                    assert mobile.is_visible(), (route, width)
                    assert mobile.locator(".aviso-badge").is_visible(), (route, width)
                    assert mobile.locator(".aviso-badge").text_content().strip() == "7"
                elif width < 900:
                    assert top.is_visible(), (route, width)
                    assert toggle.is_visible(), (route, width)
                    toggle.click()
                    assert mobile.is_visible(), (route, width)
                    assert top.locator(".aviso-badge").is_visible(), (route, width)
                    assert mobile.locator(".aviso-badge").is_visible(), (route, width)
                    assert top.evaluate("element => getComputedStyle(element).display") != "none"
                    assert mobile.evaluate("element => getComputedStyle(element).display") != "none"
                    assert top.locator(".aviso-badge").text_content().strip() == "7"
                    assert mobile.locator(".aviso-badge").text_content().strip() == "7"
                else:
                    assert top.is_visible(), (route, width)
                    assert not toggle.is_visible(), (route, width)
                    assert not mobile_menu.is_visible(), (route, width)
                    assert top.locator(".aviso-badge").is_visible(), (route, width)
                    assert top.locator(".aviso-badge").text_content().strip() == "7"
            finally:
                context.close()
