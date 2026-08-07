from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).parents[1]
PAGE_PATH = ROOT / "farmacia-popular" / "index.html"
HTML = PAGE_PATH.read_text(encoding="utf-8")


class SectionParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.section_depth = 0
        self.sections = {}
        self.current_id = None
        self.current_text = []
        self.current_tags = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "section" and "fp-credited" in attributes.get("class", "").split():
            self.section_depth = 1
            self.current_id = "fp-credited"
            self.current_text = []
            self.current_tags = []
            return
        if self.section_depth:
            self.section_depth += tag == "section"
            self.current_tags.append((tag, attributes))

    def handle_endtag(self, tag):
        if not self.section_depth:
            return
        if tag == "section":
            self.section_depth -= 1
        if self.section_depth == 0:
            self.sections[self.current_id] = (" ".join(self.current_text), self.current_tags)
            self.current_id = None

    def handle_data(self, data):
        if self.section_depth:
            self.current_text.append(data)


def parse_page():
    parser = SectionParser()
    parser.feed(HTML)
    return parser


def test_secao_de_farmacias_credenciadas_contem_textos_aprovados():
    text, _ = parse_page().sections["fp-credited"]
    assert "Farmácias já credenciadas" in text
    assert "Esta área será destinada a informações sobre estabelecimentos que já participam do Programa Farmácia Popular. As informações serão apresentadas separadamente das oportunidades de credenciamento." in text
    assert "A consulta será organizada em uma etapa própria, com apresentação simples e objetiva." in text


def test_secao_secundaria_nao_contem_consulta_lista_ou_estilo_inline():
    text, tags = parse_page().sections["fp-credited"]
    assert not any(tag in {"table", "form", "input", "select", "iframe", "button"} for tag, _ in tags)
    assert not any("style" in attributes for _, attributes in tags)
    assert not any(word in text.lower() for word in ("buscar", "filtro", "paginação", "cnpj", "endereço"))


def test_pagina_remove_destinos_governamentais_e_preserva_referencias():
    lowered = HTML.lower()
    assert "gov.br" not in lowered
    assert "saude.gov.br" not in lowered
    assert "infoms.saude.gov.br" not in lowered
    assert "ministério da saúde" in lowered
    assert "farmacia-popular-municipios-vagas-28-07-2026.pdf" in HTML
    assert "id=\"fp-consultation-title\"" in HTML
    assert "id=\"fp-table\"" in HTML
    assert "id=\"fp-pagination\"" in HTML
    assert "/noticias/credenciamento-farmacia-popular-municipios-com-vagas/" in HTML
    assert "/whatsapp/" in HTML
    assert "instagram.com/regularizeconsultoriarc" in HTML
    assert "<iframe" not in lowered


def test_secao_fica_entre_consulta_e_cta():
    consultation_end = HTML.index("</section>", HTML.index('id="fp-consultation-title"'))
    credited_start = HTML.index('class="fp-credited"')
    cta_start = HTML.index('class="fp-cta"')
    assert consultation_end < credited_start < cta_start