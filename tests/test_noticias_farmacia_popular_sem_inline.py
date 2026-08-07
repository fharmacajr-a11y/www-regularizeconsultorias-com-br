from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).parents[1]
NEWS_PATHS = (
    Path("noticias/credenciamento-farmacia-popular-municipios-com-vagas/index.html"),
    Path("noticias/farmacia-popular-adequacao-materiais-periodo-eleitoral/index.html"),
    Path("noticias/farmacia-popular-listas-ean-junho-2026/index.html"),
)


class Element:
    def __init__(self, tag, attrs):
        self.tag = tag
        self.attrs = dict(attrs)
        self.text = ""


class NewsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []
        self.stack = []

    def handle_starttag(self, tag, attrs):
        element = Element(tag, attrs)
        self.elements.append(element)
        self.stack.append(element)

    def handle_startendtag(self, tag, attrs):
        self.elements.append(Element(tag, attrs))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        if self.stack:
            self.stack[-1].text += data


EXPECTED = {
    NEWS_PATHS[0]: {
        "top_heading": "Lista de munic\u00edpios com vagas atualizada",
        "bottom_text": "A consulta \u00e9 informativa e n\u00e3o substitui",
        "button": ("Baixar lista em PDF", "./farmacia-popular-municipios-vagas-28-07-2026.pdf"),
    },
    NEWS_PATHS[1]: {
        "top_heading": "Anexo de confer\u00eancia",
        "button": ("Abrir anexo em PDF", "./modelos-marca-defeso-sus-ms.pdf"),
        "image": "/noticias/farmacia-popular-adequacao-materiais-periodo-eleitoral/farmacia-popular-modelos-marca-defeso-eleitoral.webp?v=20260707-1",
    },
    NEWS_PATHS[2]: {
        "top_heading": "Material de apoio Regularize",
        "bottom_text": "O material tem car\u00e1ter informativo",
        "button": ("Baixar listas EAN em PDF", "./farmacia-popular-listas-ean-junho-2026-regularize.pdf"),
    },
}


def parse_news(path):
    parser = NewsParser()
    parser.feed((ROOT / path).read_text(encoding="utf-8"))
    return parser.elements


def test_noticias_farmacia_popular_nao_contem_estilos_inline():
    for path in NEWS_PATHS:
        elements = parse_news(path)
        inline = [
            f"{path}: <{element.tag}> style={element.attrs['style']!r}"
            for element in elements
            if "style" in element.attrs
        ]
        assert not inline, "Estilos inline encontrados: " + "; ".join(inline)


def test_noticias_farmacia_popular_preservam_substituicoes_de_estilo():
    for path in NEWS_PATHS:
        elements = parse_news(path)
        expected = EXPECTED[path]

        heading = next(
            element
            for element in elements
            if element.tag == "h2" and expected["top_heading"] in element.text
        )
        assert "article-spacing-flush-top" in heading.attrs.get("class", "").split()

        if "bottom_text" in expected:
            paragraph = next(
                element
                for element in elements
                if element.tag == "p" and expected["bottom_text"] in element.text
            )
            assert "article-spacing-flush-bottom" in paragraph.attrs.get("class", "").split()

        button_text, button_href = expected["button"]
        button = next(
            element
            for element in elements
            if element.tag == "a" and button_text in element.text
        )
        button_classes = button.attrs.get("class", "").split()
        assert "text-white" in button_classes
        assert "no-underline" in button_classes
        assert button.attrs.get("href") == button_href

        if "image" in expected:
            image = next(
                element
                for element in elements
                if element.tag == "img" and element.attrs.get("src") == expected["image"]
            )
            assert "style" not in image.attrs
