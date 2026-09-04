import re
import json
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).parents[1]
PAGE_PATH = ROOT / "farmacia-popular" / "index.html"
HTML = PAGE_PATH.read_text(encoding="utf-8")
CONSULTATION_JS = (ROOT / "assets" / "js" / "pages" / "farmacia-popular.js").read_text(encoding="utf-8")
NEWS_URL = "/noticias/farmacia-popular-portaria-12091-2026-novas-regras/"
OG_IMAGE_URL = "https://www.regularizeconsultorias.com.br/assets/img/og/farmacia-popular.webp"
OG_IMAGE_PATH = ROOT / "assets" / "img" / "og" / "farmacia-popular.webp"


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


def test_secao_de_farmacias_credenciadas_contem_novas_regras_aprovadas():
    text, _ = parse_page().sections["fp-credited"]
    assert "Farmácias já credenciadas: pontos de atenção" in text
    assert "renovação a cada 2 anos" in text
    assert "15 dias" in text
    assert "30 dias" in text
    assert "5 anos" in text
    assert "180 dias" in text
    assert "365 dias" in text
    assert "prazo atual de guarda previsto pelo PFPB" in text
    assert "Foi mantida a regra geral" in text
    assert "Suspensão preventiva" in text
    assert "bloqueio como penalidade não são a mesma coisa" in text
    assert "renovação anual" not in text.casefold()
    assert "dois anos" not in text.casefold()
    assert "cinco anos" not in text.casefold()
    assert "Esta área será destinada" not in text
    assert "A consulta será organizada em uma etapa própria" not in text


def test_secao_secundaria_nao_contem_consulta_lista_ou_estilo_inline():
    text, tags = parse_page().sections["fp-credited"]
    assert not any(tag in {"table", "form", "input", "select", "iframe", "button"} for tag, _ in tags)
    assert not any("style" in attributes for _, attributes in tags)
    assert not any(word in text.lower() for word in ("buscar", "filtro", "paginação"))


def test_pagina_remove_destinos_governamentais_e_preserva_referencias():
    lowered = HTML.lower()
    assert "gov.br" not in lowered
    assert "saude.gov.br" not in lowered
    assert "infoms.saude.gov.br" not in lowered
    assert "ministério da saúde" in lowered
    assert "farmacia-popular-municipios-vagas-03-09-2026.pdf" in HTML
    assert "farmacia-popular-municipios-vagas-20-08-2026.pdf" not in HTML
    assert "id=\"fp-consultation-title\"" in HTML
    assert "id=\"fp-table\"" in HTML
    assert "id=\"fp-pagination\"" in HTML
    assert "/noticias/credenciamento-farmacia-popular-municipios-com-vagas/" in HTML
    assert NEWS_URL in HTML
    assert "/whatsapp/" in HTML
    assert "instagram.com/regularizeconsultoriarc" in HTML
    assert "<iframe" not in lowered


def test_card_de_proveniencia_preserva_orgao_e_links_sem_fonte_redundante():
    assert "Fonte de referência: Ministério da Saúde." not in HTML
    assert 'id="fp-official-link"' not in HTML
    assert "Órgão de origem" in HTML
    assert 'id="fp-source-org"' in HTML
    assert 'href="/noticias/credenciamento-farmacia-popular-municipios-com-vagas/farmacia-popular-municipios-vagas-03-09-2026.pdf" target="_blank" rel="noopener noreferrer">Ver lista em PDF</a>' in HTML
    assert 'href="/noticias/credenciamento-farmacia-popular-municipios-com-vagas/">Ler notícia relacionada</a>' in HTML


def test_arquivos_vinculados_pelos_links_auxiliares_existem():
    pdf_path = ROOT / "noticias" / "credenciamento-farmacia-popular-municipios-com-vagas" / "farmacia-popular-municipios-vagas-03-09-2026.pdf"
    news_path = ROOT / "noticias" / "credenciamento-farmacia-popular-municipios-com-vagas" / "index.html"
    assert pdf_path.is_file(), "Arquivo PDF 03/09 deve existir no caminho referenciado pelo link."
    assert pdf_path.stat().st_size > 0, "Arquivo PDF não deve ser vazio."
    assert pdf_path.read_bytes()[:5] == b"%PDF-", "Arquivo deve ser um PDF válido."
    assert news_path.is_file(), "Página da notícia relacionada deve existir."


def test_pagina_farmacia_popular_usa_og_especifica():
    assert OG_IMAGE_PATH.is_file()
    assert HTML.count(f'property="og:image" content="{OG_IMAGE_URL}"') == 1
    assert HTML.count(f'name="twitter:image" content="{OG_IMAGE_URL}"') == 1


def test_atualizacao_e_secao_ficam_entre_consulta_e_cta():
    consultation_end = HTML.index("</section>", HTML.index('id="fp-consultation-title"'))
    update_start = HTML.index('class="fp-regulatory-update"')
    credited_start = HTML.index('class="fp-credited"')
    cta_start = HTML.index('class="fp-cta"')
    assert consultation_end < update_start < credited_start < cta_start


def test_bloco_normativo_compacto_aponta_para_nova_noticia():
    assert "Atualização normativa • 12/08/2026" in HTML
    assert "Farmácia Popular tem novas regras para participação e acompanhamento" in HTML
    assert "Entender o que mudou" in HTML
    banner_end = HTML.index("</aside>", HTML.index('<aside class="site-regulatory-banner"')) + len("</aside>")
    editorial_html = HTML[:HTML.index('<aside class="site-regulatory-banner"')] + HTML[banner_end:]
    assert editorial_html.count(f'href="{NEWS_URL}"') == 2


def test_consulta_continua_apontando_para_as_mesmas_bases():
    assert "'/data/farmacia-popular/vagas-2026-09-03.json'" in CONSULTATION_JS
    assert "'/data/farmacia-popular/vagas-2026-08-20.json'" not in CONSULTATION_JS
    assert "'/data/farmacia-popular/metadados.json'" in CONSULTATION_JS


def test_pdf_historico_20_08_permanece_no_repositorio():
    """O PDF de 20/08 deixa de ser o link vigente, mas segue versionado."""
    historico = ROOT / "noticias" / "credenciamento-farmacia-popular-municipios-com-vagas" / "farmacia-popular-municipios-vagas-20-08-2026.pdf"
    assert historico.is_file()
    assert historico.read_bytes()[:5] == b"%PDF-"


def test_metadados_expostos_pela_consulta_apontam_para_03_09():
    metadata = json.loads((ROOT / "data" / "farmacia-popular" / "metadados.json").read_text(encoding="utf-8"))
    assert metadata["data_oficial"] == "2026-09-03"
    assert "03/09/2026" in metadata["titulo_oficial"]
    assert metadata["quantidade_registros"] == 1541
    assert metadata["totais_vagas"] == {
        "vagas_totais": 3082,
        "vagas_preenchidas": 963,
        "vagas_disponiveis": 2119,
    }


def test_script_da_consulta_tem_cache_busting_alinhado_ao_dataset():
    """O script da consulta precisa de query-string de versão.

    Sem ela, um navegador com o JS antigo em cache continua buscando o dataset
    anterior enquanto metadados.json já descreve a base nova; a validação de
    consistência falha e a página cai em "Consulta indisponível". A versão é
    derivada da data do dataset vigente, de modo que trocar a base sem bumpar
    o script quebra este teste.
    """
    dataset = re.search(r"/data/farmacia-popular/vagas-(\d{4})-(\d{2})-(\d{2})\.json", CONSULTATION_JS)
    assert dataset is not None, "dataset vigente não localizado no JS da consulta"
    versao_esperada = "".join(dataset.groups())

    tags = re.findall(r'<script[^>]+src="(/assets/js/pages/farmacia-popular\.js[^"]*)"', HTML)
    assert len(tags) == 1, f"esperado exatamente um script da consulta, achei {tags}"
    src = tags[0]

    assert src == f"/assets/js/pages/farmacia-popular.js?v={versao_esperada}-1", src
    assert '<script src="/assets/js/pages/farmacia-popular.js" defer>' not in HTML
    assert "?v=" in src, "script da consulta deve ter cache-busting"

    # O bump não pode ter afetado o versionamento global resolvido antes.
    assert '/assets/js/main.min.js?v=20260903-1' in HTML
