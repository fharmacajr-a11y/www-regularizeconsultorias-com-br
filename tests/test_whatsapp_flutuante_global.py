import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

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
