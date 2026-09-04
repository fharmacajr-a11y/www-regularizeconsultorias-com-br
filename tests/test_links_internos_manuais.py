from html.parser import HTMLParser
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).parents[1]
ORIGIN_PATH = ROOT / "manuais-e-pops/manual-boas-praticas-drogaria/index.html"
DESTINATION_PATH = ROOT / "manuais-e-pops/pops-drogaria/index.html"
ROUTE = "/manuais-e-pops/pops-drogaria/"
PUBLIC_URL = f"https://www.regularizeconsultorias.com.br{ROUTE}"
SITEMAP_PATH = ROOT / "sitemap.xml"
NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"
NS = {"s": NAMESPACE}


class _InternalLinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.canonicals = []
        self.robots = []
        self._link_text = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag.casefold() == "a" and attributes.get("href") == ROUTE:
            self._link_text = []
            self.links.append(self._link_text)
        if tag.casefold() == "link" and "canonical" in attributes.get("rel", "").casefold().split():
            self.canonicals.append(attributes.get("href", ""))
        if tag.casefold() == "meta" and attributes.get("name", "").casefold() == "robots":
            self.robots.append(attributes.get("content", ""))

    def handle_data(self, data):
        if self._link_text is not None:
            self._link_text.append(data)

    def handle_endtag(self, tag):
        if tag.casefold() == "a" and self._link_text is not None:
            self._link_text = None


def _parse(path):
    parser = _InternalLinkParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def test_pops_drogaria_has_one_contextual_internal_link():
    origin_relative = ORIGIN_PATH.relative_to(ROOT).as_posix()
    destination_relative = DESTINATION_PATH.relative_to(ROOT).as_posix()
    origin = _parse(ORIGIN_PATH)
    destination = _parse(DESTINATION_PATH)

    assert ORIGIN_PATH.is_file(), f"Arquivo de origem ausente: {origin_relative}"
    assert len(origin.links) == 1, f"Quantidade de links incorreta em {origin_relative}"
    assert "".join(origin.links[0]).strip() == "Conheça também os POPs para Drogarias"

    assert DESTINATION_PATH.is_file(), f"Destino local ausente: {destination_relative}"
    assert destination.canonicals == [PUBLIC_URL], f"Canonical incorreto em {destination_relative}"
    assert all("noindex" not in content.casefold() for content in destination.robots), (
        f"noindex encontrado em {destination_relative}"
    )

    root = ET.parse(SITEMAP_PATH).getroot()
    locations = [node.findtext("s:loc", namespaces=NS) for node in root.findall("s:url", NS)]
    assert locations.count(PUBLIC_URL) == 1, "Rota dos POPs deve aparecer uma vez no sitemap.xml"


class _PageStructureParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.h1_texts = []
        self.hrefs = []
        self.scripts = []
        self.images = []
        self._h1 = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        name = tag.casefold()
        if name == "h1":
            self._h1 = []
            self.h1_texts.append(self._h1)
        elif name == "a" and "href" in attributes:
            self.hrefs.append(attributes["href"])
        elif name == "script" and "src" in attributes:
            self.scripts.append(attributes["src"])
        elif name == "img" and "src" in attributes:
            self.images.append(attributes["src"])

    def handle_data(self, data):
        if self._h1 is not None:
            self._h1.append(data)

    def handle_endtag(self, tag):
        if tag.casefold() == "h1":
            self._h1 = None


def test_pops_drogaria_segue_o_padrao_das_paginas_internas():
    relative = DESTINATION_PATH.relative_to(ROOT).as_posix()
    content = DESTINATION_PATH.read_text(encoding="utf-8")
    parser = _PageStructureParser()
    parser.feed(content)

    assert len(parser.h1_texts) == 1, f"H1 deve ser único em {relative}"
    assert "".join(parser.h1_texts[0]).strip() == "POPs para Drogarias"

    for marker in (
        "manuals-page-detail",
        "manuals-hero-section",
        "manuals-hero-actions",
        "manuals-intro-section",
        "manuals-type-section",
        "manuals-flow-section",
        "manuals-farmacia-popular-advisory-section",
        "institutional-cta-section",
    ):
        assert marker in content, f"Bloco padrão ausente em {relative}: {marker}"

    assert "manuals-detail-layout" not in content, (
        f"Layout antigo ainda presente em {relative}"
    )

    assert "/assets/js/main.min.js?v=20260903-1" in parser.scripts

    hero_image = "/assets/img/manuais-e-pops/internas/manual-drogarias-interna.webp"
    assert hero_image in parser.images
    assert (ROOT / hero_image.lstrip("/")).is_file()

    assert "/manuais-e-pops/manual-boas-praticas-drogaria/" in parser.hrefs, (
        f"Link de retorno para o Manual de Drogarias ausente em {relative}"
    )
    assert parser.hrefs.count("/manuais-e-pops/") >= 3, (
        f"Faltam retornos para o catálogo em {relative}"
    )
    assert any(
        href.startswith("/whatsapp/?text=") and "POPs" in href for href in parser.hrefs
    ), f"CTA de orçamento por WhatsApp ausente em {relative}"

    for href in parser.hrefs:
        if href.startswith("/") and href.endswith("/"):
            assert (ROOT / href.strip("/") / "index.html").is_file(), (
                f"Link interno quebrado em {relative}: {href}"
            )
