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
    source = COMUNICADO_PATH.read_text(encoding="utf-8")
    root = _parse_html(COMUNICADO_PATH)
    notice_lists = [node for node in root.descendants() if node.attrs.get("id") == "avisos-lista"]
    assert len(notice_lists) == 1
    articles = [node for node in notice_lists[0].descendants() if node.tag == "article"]
    inactive = [
        article
        for article in articles
        if article.attrs.get("data-status", "").casefold() in {"resolved", "normalizado"}
        or "data-placeholder" in article.attrs
    ]
    active = [article for article in articles if article not in inactive]
    badges = [node for node in root.descendants() if node.has_class("aviso-badge")]

    assert len(articles) == 10
    assert len(active) == 7
    assert Counter(article.attrs.get("data-status", "").casefold() for article in inactive) == {"resolved": 1, "normalizado": 2}
    assert "data-placeholder" in source
    assert len(badges) == 2
    assert [badge.text() for badge in badges] == ["7", "7"]


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
        mobile_classes = mobile_links[0].attrs.get("class", "").split()
        assert "relative" in mobile_classes, relative_path
        assert "gap-2" in mobile_classes, relative_path
    assert pages_with_navbar == 78


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
