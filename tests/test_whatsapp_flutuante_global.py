import http.server
import json
import re
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from test_rodapes_globais import ROOT, TreeParser, parse_html, public_html_paths


TEMPLATE_PATH = ROOT / "noticias" / "template-noticia.html"
CANONICAL_PATH = ROOT / "index.html"
NEWS_ROOT = ROOT / "noticias"

CONTEXTUAL_NEWS_EXPECTATIONS = {
    "anvisa-medidas-dispositivos-medicos-irregulares-fiscalizacao": (
        {"dispositivos"},
        {"regularização", "fiscalização"},
    ),
    "anvisa-prazo-adequacao-notificacao-alimentos-setembro-2026": (
        {"alimentos"},
        {"1º de setembro", "1 de setembro"},
    ),
    "canetas-emagrecedoras-glp1-anvisa-fiscalizacao-manipulacao": (
        {"glp-1"},
        {"manipulação", "fiscalização"},
    ),
    "alteracao-cadastral-farmacia-popular-regularizacao": (
        {"farmácia popular"},
        {"cadastral", "cadastro"},
    ),
}

IN_451_NEWS_SLUG = "anvisa-atualiza-fluxo-cbpf-in451-2026"
PLATFORM_NEWS_SLUG = "anvisa-proibe-plataforma-consultas-entrega-medicamentos"


def whatsapp_buttons(root):
    return [
        node
        for node in root.descendants()
        if node.tag == "a"
        and "floating-btn--whatsapp" in node.attrs.get("class", "").split()
    ]


def first_descendant(node, tag):
    return next((child for child in node.descendants() if child.tag == tag), None)


def svg_node(button):
    svg = first_descendant(button, "svg")
    return svg


def svg_path(button):
    path = first_descendant(button, "path")
    return path.attrs.get("d") if path else None


def assert_whatsapp_contract(path, canonical_path):
    relative_path = path.relative_to(ROOT)
    root = parse_html(path)
    canonical_root = parse_html(canonical_path)
    buttons = whatsapp_buttons(root)
    assert len(buttons) == 1, f"{relative_path}: esperado exatamente 1 botão WhatsApp"

    button = buttons[0]
    classes = button.attrs.get("class", "").split()
    assert "floating-btn" in classes, relative_path
    destination = urlsplit(button.attrs.get("href", ""))
    assert destination.path == "/whatsapp/", relative_path
    assert not destination.fragment, relative_path
    if destination.query:
        query = parse_qs(destination.query, keep_blank_values=True)
        assert set(query) == {"text"}, relative_path
        assert len(query["text"]) == 1 and query["text"][0].strip(), relative_path
    assert button.attrs.get("aria-label") == "Conversar pelo WhatsApp", relative_path
    assert button.attrs.get("title") == "Fale conosco no WhatsApp", relative_path
    assert button.attrs.get("target") == "_blank", relative_path
    assert {token.casefold() for token in button.attrs.get("rel", "").split()} >= {
        "noopener",
        "noreferrer",
    }, relative_path

    svgs = [node for node in button.descendants() if node.tag == "svg"]
    assert len(svgs) == 1, f"{relative_path}: esperado exatamente 1 SVG"
    assert svgs[0].attrs.get("aria-hidden") == "true", relative_path
    assert svgs[0].attrs.get("fill", "").casefold() == "currentcolor", relative_path
    assert not [node for node in button.descendants() if node.tag == "img"], relative_path
    assert button.text_content().strip() == "", f"{relative_path}: W/WA ou outro texto visual encontrado"
    canonical_button = whatsapp_buttons(canonical_root)[0]
    assert svg_node(button).attrs.get("viewbox") == svg_node(canonical_button).attrs.get("viewbox"), relative_path
    assert svg_path(button) == svg_path(canonical_button), f"{relative_path}: SVG divergente do canônico"


def test_every_public_page_has_canonical_whatsapp_button():
    paths = public_html_paths()
    assert paths, "Nenhuma página pública encontrada"
    for path in paths:
        assert_whatsapp_contract(path, CANONICAL_PATH)


def test_news_template_has_canonical_whatsapp_button():
    assert_whatsapp_contract(TEMPLATE_PATH, CANONICAL_PATH)


def public_news_paths():
    return sorted(NEWS_ROOT.glob("*/index.html"))


def decoded_whatsapp_message(path):
    buttons = whatsapp_buttons(parse_html(path))
    assert len(buttons) == 1, path.relative_to(ROOT)
    destination = urlsplit(buttons[0].attrs.get("href", ""))
    assert destination.path == "/whatsapp/", path.relative_to(ROOT)
    assert destination.query, path.relative_to(ROOT)
    query = parse_qs(destination.query, keep_blank_values=True)
    assert set(query) == {"text"}, path.relative_to(ROOT)
    assert len(query["text"]) == 1, path.relative_to(ROOT)
    message = query["text"][0].strip()
    assert message, path.relative_to(ROOT)
    assert message.startswith("Olá!"), path.relative_to(ROOT)
    assert not re.search(r"%[0-9a-f]{2}", message, re.IGNORECASE), path.relative_to(ROOT)
    return message


def test_every_public_news_page_has_a_nonempty_contextual_whatsapp_message():
    paths = public_news_paths()
    assert paths, "Nenhuma notícia pública encontrada"
    for path in paths:
        button = whatsapp_buttons(parse_html(path))[0]
        assert button.attrs.get("href", "").startswith("/whatsapp/?text="), path.relative_to(ROOT)
        decoded_whatsapp_message(path)


def test_four_corrected_news_keep_their_expected_whatsapp_context():
    for slug, (required, alternatives) in CONTEXTUAL_NEWS_EXPECTATIONS.items():
        message = decoded_whatsapp_message(NEWS_ROOT / slug / "index.html").casefold()
        assert all(term in message for term in required), slug
        assert any(term in message for term in alternatives), slug

        if slug == "canetas-emagrecedoras-glp1-anvisa-fiscalizacao-manipulacao":
            assert "plataforma de consultas" not in message
            assert "entrega de medicamentos" not in message


def test_news_messages_reject_known_generic_and_cross_topic_legacy_texts():
    for path in public_news_paths():
        slug = path.parent.name
        message = decoded_whatsapp_message(path).casefold()

        assert "vim pelo site" not in message, slug
        assert "prévia de notícia" not in message, slug

        if "plataforma de consultas" in message or "entrega de medicamentos" in message:
            assert slug == PLATFORM_NEWS_SLUG

        if "in 451/2026" in message:
            assert slug == IN_451_NEWS_SLUG
            assert "cbpf" in message


# ---------------------------------------------------------------------------
# Testes de política responsiva – M11.1
# ---------------------------------------------------------------------------

NEWS_PAGE = "noticias/index.html"
LEGACY_PAGE = "noticias/anvisa-alerta-soroterapia-promessas-sem-evidencia/index.html"
COMUNICADO_PAGE = "comunicado/index.html"

STATIC_CASES = [
    pytest.param(NEWS_PAGE, 390, 844, "footer", id="noticias-390"),
    pytest.param(NEWS_PAGE, 768, 1024, "footer", id="noticias-768"),
    pytest.param(NEWS_PAGE, 1375, 900, "footer", id="noticias-1375"),
    pytest.param(LEGACY_PAGE, 390, 844, "footer", id="legada-390"),
    pytest.param(LEGACY_PAGE, 1375, 900, "footer", id="legada-1375"),
    pytest.param(COMUNICADO_PAGE, 390, 844, "main", id="comunicado-390"),
]
DESKTOP_CASES = [
    pytest.param(NEWS_PAGE, 1376, 900, id="noticias-1376"),
    pytest.param(NEWS_PAGE, 1440, 900, id="noticias-1440"),
    pytest.param(LEGACY_PAGE, 1376, 900, id="legada-1376"),
    pytest.param(LEGACY_PAGE, 1440, 900, id="legada-1440"),
]


@pytest.fixture(scope="module")
def http_server():
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT.resolve()), **kwargs)

        def log_message(self, format, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _browser_probe(port, relative_path, width, height, back_to_top=False):
    assert (ROOT / relative_path).is_file(), f"Página obrigatória ausente: {relative_path}"
    script = r'''
import json
import sys
from playwright.sync_api import sync_playwright

url, width, height, back_to_top = sys.argv[1:]
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": int(width), "height": int(height)})
    page = context.new_page()
    response = page.goto(url, wait_until="domcontentloaded", timeout=15_000)
    assert response is not None and response.ok, url
    layout = page.evaluate(
        """() => {
            const group = document.querySelector('.floating-buttons');
            if (!group) return null;
            const rect = element => {
                if (!element) return null;
                const r = element.getBoundingClientRect();
                return {top:r.top, right:r.right, bottom:r.bottom, left:r.left,
                        width:r.width, height:r.height};
            };
            const intersects = (a, b) => Boolean(a && b && a.left < b.right &&
                a.right > b.left && a.top < b.bottom && a.bottom > b.top);
            const groupRect = rect(group);
            const mainRect = rect(document.querySelector('main'));
            const footerRect = rect(document.querySelector('footer'));
            const style = getComputedStyle(group);
            return {
                position: style.position,
                flexDirection: style.flexDirection,
                bottom: parseFloat(style.bottom),
                right: parseFloat(style.right),
                zIndex: style.zIndex,
                groupRect, mainRect, footerRect,
                intersectsMain: intersects(groupRect, mainRect),
                intersectsFooter: intersects(groupRect, footerRect),
                overflowX: document.documentElement.scrollWidth -
                           document.documentElement.clientWidth,
                buttons: Array.from(group.querySelectorAll('.floating-btn')).map(
                    button => {
                        const r = rect(button);
                        return {classes: button.className, width:r.width, height:r.height};
                    }
                ),
                hasWhatsapp: Boolean(group.querySelector('.floating-btn--whatsapp')),
                hasBackToTop: Boolean(group.querySelector('.floating-btn--top')),
            };
        }"""
    )
    if back_to_top == "1":
        page.evaluate(
            "() => window.scrollTo(0, Math.min(1200, "
            "document.documentElement.scrollHeight - innerHeight))"
        )
        page.wait_for_function("window.scrollY > 300")
        button = page.locator(".floating-btn--top")
        assert button.count() == 1
        page.wait_for_function(
            "document.querySelector('.floating-btn--top').classList.contains('is-visible')"
        )
        assert button.is_visible() and button.is_enabled()
        button.click()
        page.wait_for_function("window.scrollY <= 1", timeout=5_000)
        layout["backToTopWorked"] = True
    print(json.dumps(layout))
    context.close()
    browser.close()
'''
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            f"http://127.0.0.1:{port}/{relative_path}",
            str(width),
            str(height),
            "1" if back_to_top else "0",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _assert_controls(layout, size):
    assert layout["hasWhatsapp"] and layout["hasBackToTop"], layout
    assert len(layout["buttons"]) == 2, layout["buttons"]
    for button in layout["buttons"]:
        assert button["width"] == pytest.approx(size, abs=0.1), button
        assert button["height"] == pytest.approx(size, abs=0.1), button


@pytest.mark.parametrize("page_path,width,height,after", STATIC_CASES)
def test_static_floating_buttons_contract(
    http_server, page_path, width, height, after
):
    if page_path in {LEGACY_PAGE, COMUNICADO_PAGE}:
        assert "custom.min.css" in (ROOT / page_path).read_text(encoding="utf-8")

    layout = _browser_probe(http_server, page_path, width, height)
    assert layout is not None, ".floating-buttons obrigatório ausente"
    assert layout["position"] == "static", layout
    assert layout["flexDirection"] == "row", layout
    assert layout["overflowX"] <= 0, layout
    assert not layout["intersectsMain"] and not layout["intersectsFooter"], layout
    _assert_controls(layout, 44 if width <= 640 else 48)
    boundary = layout[f"{after}Rect"]
    assert boundary is not None, layout
    assert layout["groupRect"]["top"] >= boundary["bottom"], layout


@pytest.mark.parametrize("page_path,width,height", DESKTOP_CASES)
def test_desktop_floating_buttons_contract(
    http_server, page_path, width, height
):
    layout = _browser_probe(http_server, page_path, width, height)
    assert layout is not None, ".floating-buttons obrigatório ausente"
    assert layout["position"] == "fixed", layout
    assert layout["flexDirection"] == "column", layout
    assert layout["bottom"] == pytest.approx(24, abs=0.1), layout
    assert layout["right"] == pytest.approx(24, abs=0.1), layout
    assert layout["zIndex"] == "9999", layout
    _assert_controls(layout, 48)


def test_back_to_top_button_returns_to_page_start(http_server):
    layout = _browser_probe(http_server, NEWS_PAGE, 1376, 900, back_to_top=True)
    assert layout["backToTopWorked"]
