from pathlib import Path

from test_rodapes_globais import ROOT, TreeParser, parse_html, public_html_paths


TEMPLATE_PATH = ROOT / "noticias" / "template-noticia.html"
CANONICAL_PATH = ROOT / "index.html"


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
    assert button.attrs.get("href", "").startswith("/whatsapp/"), relative_path
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
    assert not [node for node in button.descendants() if node.tag == "img"], relative_path
    assert button.text_content().strip() == "", f"{relative_path}: W/WA ou outro texto visual encontrado"
    canonical_button = whatsapp_buttons(canonical_root)[0]
    assert svg_node(button).attrs.get("viewbox") == svg_node(canonical_button).attrs.get("viewbox"), relative_path
    assert svg_path(button) == svg_path(canonical_button), f"{relative_path}: SVG divergente do canônico"


def test_every_public_page_has_canonical_whatsapp_button():
    paths = public_html_paths()
    assert len(paths) == 82
    for path in paths:
        assert_whatsapp_contract(path, CANONICAL_PATH)


def test_news_template_has_canonical_whatsapp_button():
    assert_whatsapp_contract(TEMPLATE_PATH, CANONICAL_PATH)
