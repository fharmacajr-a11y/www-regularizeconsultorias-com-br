import functools
import re
import threading
from collections import Counter
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from support import SITE_DIR, new_context


ROOT = Path(__file__).parents[2]
COMUNICADO_PATH = ROOT / "comunicado" / "index.html"
MAIN_PATHS = (ROOT / "assets/js/main.js", ROOT / "assets/js/main.min.js")
CSS_PATHS = (
    ROOT / "assets/css/components.css",
    ROOT / "assets/css/custom.css",
    ROOT / "assets/css/custom.min.css",
)
CURRENT_STORAGE_VERSION = "2026-10-26-avisos-5"
AFE_ROUTE = "/noticias/anvisa-edital-6-2026-afe-manipulacao-preparacoes-estereis/"
CADASTRO_ROUTE = "/noticias/cadastro-anvisa-govbr-transicao-sistemas/"
CNES_ROUTE = "/noticias/cnes-competencia-09-2026-prazo-transmissao/"
PF_ROUTE = "/noticias/produtos-quimicos-controlados-siproquim2-assinador-pf/"
MAPA_ROUTE = "/noticias/mapa-portaria-1617-2026-aditivos-antimicrobianos-alimentacao-animal/"
PRODUTOS_ROUTE = "/noticias/anvisa-suspende-medicamento-proibe-produtos-irregulares/"
INSTABILIDADE_ID = "instabilidade-anvisa-2026-10-19"
ELEITORAL_ROUTE = "/noticias/farmacia-popular-adequacao-materiais-periodo-eleitoral/"
CNES_10_ROUTE = "/noticias/cnes-competencia-10-2026-prazo-transmissao/"
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
        and "a-publicar" not in path.relative_to(ROOT).parts
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
    handler = functools.partial(_QuietHandler, directory=str(SITE_DIR))
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


def test_comunicado_has_five_active_notices_thirteen_historical_and_two_static_badges():
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

    # 26/10/2026: os avisos do marco de 23/10 do MAPA e do período eleitoral do Farmácia Popular passaram ao histórico
    # (5 ativos, 13 no histórico).
    # 20/10/2026: o aviso da instabilidade na consulta de empresas da Anvisa passou ao histórico (7 ativos, 11 no histórico).
    # 19/10/2026, 15h40: aviso informativo sobre a instabilidade nos sistemas da Anvisa (8 ativos, 10 no histórico).
    # 17/10/2026, 09h50: aviso informativo do Farmácia Popular sobre lembretes pelo WhatsApp (7 ativos, 10 no histórico).
    # 16/10/2026, 20h06: aviso informativo do CNES 10/2026 (6 ativos, 10 no histórico).
    # 16/10/2026: o aviso dos mapas de setembro da PF passou ao histórico (5 ativos, 10 no histórico).
    # Antes, em 11/10/2026, o aviso do CNES 09/2026 já tinha passado (6 ativos, 9 no histórico).
    assert len(articles) == 18
    assert len(active) == 5
    assert Counter(article.attrs.get("data-status", "").casefold() for article in inactive) == {"resolved": 13}
    assert all("data-placeholder" not in article.attrs for article in articles)
    assert len(badges) == 2
    assert [badge.text() for badge in badges] == ["5", "5"]


def test_comunicado_instabilidade_anvisa_is_historical_with_direct_anchor():
    root = _parse_html(COMUNICADO_PATH)
    notice_list = next(node for node in root.descendants() if node.attrs.get("id") == "avisos-lista")
    articles = [node for node in notice_list.descendants() if node.tag == "article"]
    historical = [article for article in articles if article.attrs.get("data-status", "").casefold() == "resolved"]
    anchored = [node for node in root.descendants() if node.attrs.get("id") == INSTABILIDADE_ID]

    # 19/10/2026: verificações da Regularize às 15h40 e às 17h; às 17h45 a consulta de empresas voltou, mas podia oscilar.
    # 20/10/2026: a consulta segue funcionando e o aviso foi encerrado, no formato dos encerrados de 28/04/2026, com o
    # mesmo id. Link direto enviado aos clientes pelo WhatsApp:
    # https://www.regularizeconsultorias.com.br/comunicado/#instabilidade-anvisa-2026-10-19
    # 26/10/2026: os encerrados do período eleitoral e do MAPA entram acima dele; é o terceiro do histórico.
    assert len(anchored) == 1
    notice = anchored[0]
    assert notice is historical[2]
    assert notice.tag == "article"
    assert notice.attrs.get("data-status") == "resolved"
    assert notice.attrs.get("data-category") == "anvisa"
    assert "data-effective-at" not in notice.attrs
    assert notice.attrs.get("data-updated-at") == "19/10/2026 às 17h45"
    assert notice.attrs.get("data-resolved-at") == "20/10/2026 às 14h50"
    assert "data-aviso-history-card" in notice.attrs
    assert {"comunicado-historico", "border-slate-300", "bg-slate-50"} <= set(notice.attrs["class"].split())
    text = " ".join(notice.text().split())
    badge = next(node for node in notice.descendants() if node.has_class("comunicado-historico__badge"))
    assert badge.text() == "ENCERRADO"
    assert "INFORMATIVO" not in text and "URGENTE" not in text
    times = [node for node in notice.descendants() if node.tag == "time"]
    assert [(node.attrs.get("datetime"), node.text()) for node in times] == [("2026-10-20T14:50:00-03:00", "20/10/2026 • 14h50")]
    # Como no aviso ativo, em telas pequenas o selo e a data quebram em linhas diferentes; o "•" entre eles só aparece
    # a partir de 640 px.
    separators = [node for node in notice.descendants() if node.tag == "span" and node.text() == "•"]
    assert len(separators) == 1 and separators[0].attrs.get("class", "").split() == ["hidden", "sm:block"]
    assert next(node.text() for node in notice.descendants() if node.tag == "h3") == "Instabilidade na consulta de empresas da Anvisa (19/10/2026)"
    # Visíveis: título, atualização final e o botão; o texto do aviso fica atrás de "Ver histórico completo".
    final_update = next(node for node in notice.descendants() if node.tag == "p" and node.text().startswith("Atualização final"))
    assert not final_update.inside_id("aviso-historico-instabilidade-anvisa")
    # _Node.text() junta o texto próprio antes do dos filhos; a frase com o link é conferida na ordem do HTML.
    source = COMUNICADO_PATH.read_text(encoding="utf-8")
    final_html = re.findall(r"<p\b[^>]*>(Atualização final em 20/10/2026:.*?)</p>", source)
    assert len(final_html) == 1
    assert " ".join(re.sub(r"<[^>]+>", "", final_html[0]).split()) == (
        "Atualização final em 20/10/2026: a consulta de empresas (AFE/AE) segue funcionando desde o fim da tarde de 19/10, "
        "e o Painel de Disponibilidade de Sistemas da Anvisa indica os sistemas como disponíveis. Encerramos este comunicado."
    )
    toggle = next(node for node in notice.descendants() if node.tag == "button")
    assert "data-aviso-history-toggle" in toggle.attrs
    assert toggle.attrs.get("aria-expanded") == "false"
    assert toggle.attrs.get("aria-controls") == "aviso-historico-instabilidade-anvisa"
    assert "Ver histórico completo" in toggle.text()
    content = next(node for node in notice.descendants() if node.attrs.get("id") == "aviso-historico-instabilidade-anvisa")
    assert "data-aviso-history-content" in content.attrs and content.has_class("hidden")
    content_text = " ".join(content.text().split())
    for term in (
        "Prezados clientes,",
        "Nesta segunda-feira (19/10), a Consulta de Funcionamento de Empresas (AFE/AE) da Anvisa apresentou erro e não exibia resultados.",
        "Verificamos o problema por volta das 15h40 e novamente às 17h.",
        "Atualização às 17h45: a consulta voltou a funcionar, mas ainda pode oscilar.",
        "indica os sistemas como disponíveis.",
        "Até o momento, a Anvisa não publicou comunicado oficial sobre a instabilidade.",
        "Se a consulta apresentar erro:",
        "Tente novamente em alguns minutos.",
        "Se você usa bloqueador de anúncios ou navegador com proteção reforçada (como o Brave), desative a proteção para o site da Anvisa, pois ela pode bloquear a verificação de segurança da consulta.",
        "Atualizaremos este comunicado se a instabilidade continuar ou quando a situação se normalizar.",
        "Atenciosamente,",
        "Equipe Regularize Consultoria",
    ):
        assert term in content_text, term
    # O resumo do aviso ativo deu lugar à atualização final.
    assert "nesta segunda-feira. Ela voltou a funcionar no fim da tarde" not in text
    # Únicos links: o painel oficial, na atualização final e no texto guardado, no formato de link externo dos avisos
    # de 28/04/2026.
    links = [node for node in notice.descendants() if node.tag == "a"]
    assert [(link.attrs.get("href"), link.text()) for link in links] == [
        ("https://disponibilidade.anvisa.gov.br/", "Painel de Disponibilidade de Sistemas da Anvisa")
    ] * 2
    assert links[0].parent is final_update and links[1].inside_id("aviso-historico-instabilidade-anvisa")
    for link in links:
        assert link.attrs.get("target") == "_blank" and link.attrs.get("rel") == "noopener noreferrer"
        assert link.attrs.get("class", "").split() == ["font-medium", "text-brand", "hover:text-brand-dark", "transition-colors", "duration-200"]
    lowered = text.casefold()
    # Sem o portal do gov.br em manutenção (removido às 17h45), sem outros sistemas, previsão ou nota oficial.
    for claim in ("gov.br", "manutenção", "todos os sistemas", "solicita", "sngpc", "sncr", "previs", "nota oficial", "fora do ar"):
        assert claim not in lowered, claim


def test_comunicado_mapa_and_electoral_period_notices_are_closed_on_top_of_history():
    root = _parse_html(COMUNICADO_PATH)
    source = COMUNICADO_PATH.read_text(encoding="utf-8")
    notice_list = next(node for node in root.descendants() if node.attrs.get("id") == "avisos-lista")
    articles = [node for node in notice_list.descendants() if node.tag == "article"]
    historical = [article for article in articles if article.attrs.get("data-status", "").casefold() == "resolved"]
    active = [article for article in articles if article not in historical]

    # 26/10/2026: o marco de 23/10/2026 do MAPA e o período eleitoral (até 25/10/2026, havendo segundo turno) passaram.
    # Os dois avisos foram encerrados no formato do encerrado da instabilidade na Anvisa (20/10/2026), com os mesmos
    # atributos que tinham (os dois não tinham id), e abrem o histórico, o mais recente primeiro.
    cases = (
        (
            historical[0],
            ELEITORAL_ROUTE,
            "farmacia-popular",
            None,
            "Farmácia Popular: atenção aos materiais no período eleitoral",
            "aviso-historico-farmacia-popular-periodo-eleitoral",
            "Atualização final em 26/10/2026: terminou em 25/10/2026 o prazo máximo de vigência das disposições do Manual de "
            "Comunicação do Período de Defeso Eleitoral 2026 do Ministério da Saúde, previsto para o caso de segundo turno. "
            "Antes de manter, retirar ou alterar materiais do Farmácia Popular, confirme a orientação nos canais oficiais do "
            "programa ou com o suporte técnico responsável. Encerramos este comunicado.",
            "Ver orientação completa",
            (
                "Farmácias e drogarias credenciadas devem revisar materiais de divulgação, identificação visual e peças expostas "
                "ao público durante o período eleitoral.",
                "indica o período de 4 de julho a 4 de outubro de 2026 e, havendo segundo turno, a vigência das disposições até "
                "25 de outubro de 2026.",
            ),
        ),
        (
            historical[1],
            MAPA_ROUTE,
            "mapa",
            "06/10/2026 às 08h00",
            "MAPA: estoques de aditivos com antimicrobianos do Anexo têm marco em 23/10",
            "aviso-historico-mapa-portaria-1617",
            "Atualização final em 26/10/2026: o marco de 23/10/2026 passou. Segundo o Ofício-Circular nº 29/2026, encerrado "
            "esse prazo, ficam proibidas a comercialização e a utilização dos produtos abrangidos pela Portaria SDA/MAPA nº "
            "1.617/2026, e novos lotes do aditivo e novas importações seguem proibidos. Continua o prazo de recolhimento: o "
            "detentor do registro deve recolher os estoques remanescentes do aditivo até 21/01/2027. Encerramos este comunicado.",
            "Leia a notícia sobre a Portaria 1.617/2026",
            (
                "A Portaria SDA/MAPA nº 1.617/2026 proíbe a importação, a fabricação, a comercialização e o uso de aditivos "
                "melhoradores de desempenho que contenham os antimicrobianos do Anexo.",
                "podem ser comercializados e utilizados até 23/10/2026.",
                "Novos lotes do aditivo e novas importações, inclusive desses produtos, seguem proibidos.",
                "Após 23/10/2026, o detentor do registro deve recolher os estoques remanescentes do aditivo até 21/01/2027; esse "
                "prazo é de recolhimento, não de comercialização ou uso.",
                "A medida não alcança o conjunto dos medicamentos veterinários.",
            ),
        ),
    )
    for notice, route, category, updated_at, title, content_id, final, link_label, kept in cases:
        assert "id" not in notice.attrs, title
        assert notice.attrs.get("data-status") == "resolved"
        assert notice.attrs.get("data-category") == category
        assert notice.attrs.get("data-updated-at") == updated_at
        assert notice.attrs.get("data-resolved-at") == "26/10/2026 às 08h30"
        assert "data-effective-at" not in notice.attrs
        assert "data-aviso-history-card" in notice.attrs
        assert {"comunicado-historico", "border-slate-300", "bg-slate-50"} <= set(notice.attrs["class"].split())
        badge = next(node for node in notice.descendants() if node.has_class("comunicado-historico__badge"))
        assert badge.text() == "ENCERRADO"
        times = [node for node in notice.descendants() if node.tag == "time"]
        assert [(node.attrs.get("datetime"), node.text()) for node in times] == [("2026-10-26T08:30:00-03:00", "26/10/2026 • 08h30")]
        assert next(node.text() for node in notice.descendants() if node.tag == "h3") == title
        text = " ".join(notice.text().split())
        assert "INFORMATIVO" not in text and "URGENTE" not in text
        # Visíveis: título, atualização final, o botão e o link da notícia; o texto do aviso fica atrás do botão.
        final_node = next(node for node in notice.descendants() if node.tag == "p" and node.text().startswith("Atualização final"))
        assert not final_node.inside_id(content_id)
        final_html = re.findall(rf"<p\b[^>]*>(Atualização final em 26/10/2026: {re.escape(final[33:60])}.*?)</p>", source)
        assert len(final_html) == 1
        assert " ".join(re.sub(r"<[^>]+>", "", final_html[0]).split()) == final
        toggle = next(node for node in notice.descendants() if node.tag == "button")
        assert "data-aviso-history-toggle" in toggle.attrs and toggle.attrs.get("aria-expanded") == "false"
        assert toggle.attrs.get("aria-controls") == content_id
        assert "Ver histórico completo" in toggle.text()
        content = next(node for node in notice.descendants() if node.attrs.get("id") == content_id)
        assert "data-aviso-history-content" in content.attrs and content.has_class("hidden")
        # _Node.text() junta o texto próprio antes do dos filhos (<strong>); o texto guardado é conferido na ordem do HTML.
        content_html = re.search(rf'<div id="{content_id}"[^>]*>(.*?)</div>\s*</div>', source, re.DOTALL).group(1)
        content_text = " ".join(re.sub(r"<[^>]+>", "", content_html).split())
        for term in kept:
            assert term in content_text, term
        links = [node for node in notice.descendants() if node.tag == "a"]
        assert [node.attrs.get("href") for node in links] == [route]
        assert not links[0].inside_id(content_id)
        assert link_label in links[0].text()
        assert "comunicado-historico__control" in links[0].attrs["class"].split()
        assert not any(node.attrs.get("href") == route for article in active for node in article.descendants())
    assert source.count("aviso-historico-farmacia-popular-periodo-eleitoral") == 2
    assert source.count("aviso-historico-mapa-portaria-1617") == 2


def test_comunicado_editorial_organization_and_active_notice_content():
    source = COMUNICADO_PATH.read_text(encoding="utf-8")
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
    historical = [article for article in articles if article not in active]
    afe_active = [
        article
        for article in active
        if any(node.tag == "a" and node.attrs.get("href") == AFE_ROUTE for node in article.descendants())
    ]
    afe_historical = [
        article
        for article in historical
        if any(node.tag == "a" and node.attrs.get("href") == AFE_ROUTE for node in article.descendants())
    ]
    cadastro_active = [
        article
        for article in active
        if any(node.tag == "a" and node.attrs.get("href") == CADASTRO_ROUTE for node in article.descendants())
    ]
    cadastro_historical = [
        article
        for article in historical
        if any(node.tag == "a" and node.attrs.get("href") == CADASTRO_ROUTE for node in article.descendants())
    ]
    produtos = historical[7]
    produtos_links = [node.attrs.get("href") for node in produtos.descendants() if node.tag == "a"]
    renewal = historical[8]
    renewal_links = [node.attrs.get("href") for node in renewal.descendants() if node.tag == "a"]
    cnes_active = [
        article
        for article in active
        if any(node.tag == "a" and node.attrs.get("href") == CNES_ROUTE for node in article.descendants())
    ]
    cnes_historical = [
        article
        for article in historical
        if any(node.tag == "a" and node.attrs.get("href") == CNES_ROUTE for node in article.descendants())
    ]

    assert len(active) == 5
    assert len(historical) == 13
    assert len(articles) == 18
    # Edital 6/2026: a ficha do AnvisaLegis apresenta o chamamento como encerrado (consulta de 09/10/2026).
    assert not afe_active
    assert len(afe_historical) == 1
    assert not cadastro_active
    assert len(cadastro_historical) == 1
    assert "Histórico / encerrados" in headings
    afe = afe_historical[0]
    afe_text = afe.text()
    afe_links = [node for node in afe.descendants() if node.tag == "a"]
    assert afe is historical[5]
    assert afe.attrs.get("data-status") == "resolved"
    assert afe.attrs.get("data-category") == "anvisa"
    assert "ENCERRADO" in afe_text and "09/10/2026 • 20h25" in afe_text
    assert "comunicado-historico__control" in afe_links[0].attrs.get("class", "").split()
    assert len(afe_links) == 1
    assert afe_links[0].attrs.get("href") == AFE_ROUTE
    assert "Ver notícia sobre o Edital 6/2026" in afe_links[0].text()
    for term in (
        "estabelecimentos com AFE vigente para manipulação de preparações estéreis",
        "atividades constantes da AFE correspondiam às efetivamente exercidas",
        "08/09/2026",
        "07/10/2026",
        "ficha do AnvisaLegis",
        "apresenta o chamamento como encerrado em consulta de 09/10/2026",
        "30 dias corridos a partir de um dia útil após a publicação",
        "Comunicado mantido como registro do chamamento, sem caráter de aviso atual",
    ):
        assert term in afe_text
    assert "Edital 6/2026" not in active_text
    assert "7112" not in source
    assert "o edital indica o assunto" not in source
    assert "como preparar o estabelecimento" not in source
    assert "todo estabelecimento" not in afe_text.casefold()
    assert "deferimento" not in afe_text.casefold()
    # 07/10 é o registro da ficha do AnvisaLegis; a íntegra do edital fixa a regra dos 30 dias.
    assert "prazo informado no edital permanece" not in afe_text
    assert "08/10" not in afe_text
    # Informe do CNES de 05/10/2026: prazo do transmissor da competência 09/2026 prorrogado até 09/10/2026. Em 11/10/2026
    # o prazo tinha passado e a página de informes do CNES (consulta de 11/10/2026) não trazia nova prorrogação: o aviso
    # saiu dos ativos e entrou no histórico, como ENCERRADO, com a hora da mudança (11/10/2026 • 06h07). Desde 16/10/2026
    # vem logo depois do aviso PF; desde 20/10/2026, o da instabilidade na Anvisa vem antes dele; desde 26/10/2026, os do
    # período eleitoral e do MAPA abrem o histórico e ele é o quinto.
    assert not cnes_active
    assert len(cnes_historical) == 1
    cnes = cnes_historical[0]
    cnes_text = cnes.text()
    cnes_links = [node for node in cnes.descendants() if node.tag == "a"]
    assert cnes is historical[4]
    assert cnes.attrs.get("data-status") == "resolved"
    assert cnes.attrs.get("data-category") == "cnes"
    assert "ENCERRADO" in cnes_text and "11/10/2026 • 06h07" in cnes_text
    assert "INFORMATIVO" not in cnes_text and "URGENTE" not in cnes_text
    assert "CNES: envio da competência 09/2026 foi prorrogado até 9 de outubro" in cnes_text
    assert "Em informe de 05/10/2026" in cnes_text
    assert "09/10/2026" in cnes_text and "antes informado para 07/10/2026" in cnes_text
    assert "Em consulta de 11/10/2026, a página de informes do CNES não trazia nova prorrogação além de 09/10/2026" in cnes_text
    assert "Comunicado mantido como registro do prazo, sem caráter de aviso atual" in cnes_text
    assert "segue aberta até 7 de outubro" not in cnes_text
    assert "SIA" not in cnes_text and "SIH" not in cnes_text
    assert "toda farmácia" not in cnes_text.casefold()
    assert "competência 09/2026" not in active_text
    assert len(cnes_links) == 1
    assert cnes_links[0].attrs.get("href") == CNES_ROUTE
    assert "comunicado-historico__control" in cnes_links[0].attrs.get("class", "").split()
    assert "Ver notícia sobre a competência 09/2026" in cnes_links[0].text()
    # IN DG/PF nº 338/2026, art. 8º, § 1º: mapa mensal até o 15º dia do mês seguinte; setembro/2026 venceu em
    # 15/10/2026. Em consulta de 16/10/2026, as páginas da PF sobre produtos químicos e a busca no DOU não traziam
    # prorrogação: o aviso saiu dos ativos e entrou no topo do histórico, como ENCERRADO, com a hora da mudança
    # (16/10/2026 • 15h55); desde 26/10/2026 é o quarto. Público restrito às atividades com químicos controlados.
    pf_active = [
        article
        for article in active
        if any(node.tag == "a" and node.attrs.get("href") == PF_ROUTE for node in article.descendants())
    ]
    pf_historical = [
        article
        for article in historical
        if any(node.tag == "a" and node.attrs.get("href") == PF_ROUTE for node in article.descendants())
    ]
    assert not pf_active
    assert len(pf_historical) == 1
    pf = pf_historical[0]
    pf_text = pf.text()
    pf_links = [node for node in pf.descendants() if node.tag == "a"]
    assert pf is historical[3]
    assert pf.attrs.get("data-status") == "resolved"
    assert pf.attrs.get("data-category") == "pf"
    assert "ENCERRADO" in pf_text and "16/10/2026 • 15h55" in pf_text
    assert [node.attrs.get("href") for node in pf_links] == [PF_ROUTE]
    assert "comunicado-historico__control" in pf_links[0].attrs.get("class", "").split()
    assert "Ver notícia sobre a IN 338/2026" in pf_links[0].text()
    for term in (
        "Polícia Federal: prazo dos mapas de setembro dos produtos químicos controlados terminou em 15/10",
        "Instrução Normativa DG/PF nº 338/2026",
        "atividades sujeitas ao controle e à fiscalização da Polícia Federal",
        "Mapas Mensais de Controle",
        "até o 15º dia do mês seguinte, mesmo sem movimentação no período",
        "o prazo terminou em",
        "15/10/2026",
        "Em consulta de 16/10/2026, as páginas da Polícia Federal sobre produtos químicos e a busca no Diário Oficial da União não traziam prorrogação desse prazo",
        "Portaria MJSP nº 204/2022",
        "não se estende a todas as farmácias nem aos medicamentos controlados em geral",
        "Comunicado mantido como registro do prazo, sem caráter de aviso atual",
        "A obrigação mensal prevista na IN DG/PF nº 338/2026 continua nos meses seguintes",
    ):
        assert term in pf_text
    assert "o prazo vai até" not in pf_text
    assert "INFORMATIVO" not in pf_text and "URGENTE" not in pf_text
    assert "Mapas Mensais de Controle" not in active_text and "15/10/2026" not in active_text
    assert "passo a passo" not in pf_text.casefold()
    assert "deferimento" not in pf_text.casefold()
    # Portaria SDA/MAPA nº 1.617/2026 e Ofício-Circular nº 29/2026: 23/10/2026 para os estoques e produtos de alimentação
    # animal abrangidos; 21/01/2027 só para o recolhimento. Em 26/10/2026 o aviso passou ao histórico (ver o teste dos
    # encerrados do MAPA e do período eleitoral).
    mapa_active = [
        article
        for article in active
        if any(node.tag == "a" and node.attrs.get("href") == MAPA_ROUTE for node in article.descendants())
    ]
    assert not mapa_active
    assert "23/10/2026" not in active_text and "21/01/2027" not in active_text
    assert "Anvisa suspende medicamento e proíbe produtos irregulares" in produtos.text()
    assert "HISTÓRICO" in produtos.text()
    assert "06/10/2026 • 14h27" in produtos.text()
    # RE nº 3.738/2026 (DOU de 23/09) entra no recorte de 21 a 28/09; os atos de 01, 08 e 11/09 ficam fora.
    assert "apreensão e proibições sobre três lotes falsificados de Enhertu e sobre o produto Mounjcaps" in produtos.text()
    for term in ("United Labz", "TYG", "Hytamicina", "Pangastri", "Gripinew", "Anagalis", "Lipo Top"):
        assert term not in produtos.text()
    # RE nº 3.751/2026: 31/08 a 02/09/2026 é a inspeção da ICT, não o período de produção.
    assert "todos os manipulados estéreis da ICT Farmacêutica, em todos os lotes" in produtos.text()
    assert "após inspeção realizada de 31/08 a 02/09/2026" in produtos.text()
    assert "produzidos de 31/08" not in produtos.text()
    assert "distribuidora LAF MED" in produtos.text() and "quaisquer medicamentos" in produtos.text()
    assert "reúnem medidas pontuais" in produtos.text()
    assert "Comunicado mantido como registro das medidas sanitárias divulgadas no período" in produtos.text()
    # RE nº 3.764/2026 (Reach Latam) e as revogações das RE nº 3.743/2026 (Higia) e 3.718/2026 (Tha & Thi),
    # publicadas entre 21 e 28/09, acompanham a síntese. A RE nº 3.436/2026 (01/09) fica fora desse recorte.
    assert "insumos sujeitos a controle especial da Reach Latam, incluindo tirzepatida" in produtos.text()
    assert "a RE nº 3.743/2026 revogou a medida preventiva referente à Higia Pharmaceutical, com restrições registradas na motivação" in produtos.text()
    assert "a RE nº 3.718/2026 revogou a medida preventiva referente à Tha & Thi Farmácia de Manipulação" in produtos.text()
    assert "o arquivamento deste aviso não significa revogação das medidas" in produtos.text()
    assert "Terapêutica" not in produtos.text() and "3.436" not in produtos.text()
    # Fora dessas três frases, nenhuma menção a revogação.
    produtos_resto = produtos.text().replace(
        "a RE nº 3.743/2026 revogou a medida preventiva referente à Higia Pharmaceutical", ""
    ).replace(
        "a RE nº 3.718/2026 revogou a medida preventiva referente à Tha & Thi Farmácia de Manipulação", ""
    ).replace("o arquivamento deste aviso não significa revogação das medidas", "")
    assert "revog" not in produtos_resto.casefold()
    assert produtos_links == [PRODUTOS_ROUTE]
    cadastro = cadastro_historical[0]
    assert "Cadastro Anvisa/Gov.br: atenção a empresas, usuários e perfis de acesso" in cadastro.text()
    assert "19/05/2026 • 09h00" in cadastro.text()
    assert [node.attrs.get("href") for node in cadastro.descendants() if node.tag == "a"] == [CADASTRO_ROUTE]
    # O ciclo encerrado em 31/08/2026 deixou de ser aviso ativo e virou registro histórico.
    assert "ciclo de renovação foi encerrado em 31 de agosto" in renewal.text()
    assert "31/08/2026" in renewal.text()
    assert "ciclo bienal de 2027" in renewal.text()
    assert "ainda a ser definida" in renewal.text()
    assert renewal_links == ["/noticias/farmacia-popular-portaria-12091-2026-novas-regras/"]
    assert "suspensao-temporaria-recadastramento-sifap" not in " ".join(renewal_links)
    assert "ciclo atual de renovação termina" not in active_text
    assert "31/08/2026" not in active_text
    assert "período eleitoral" not in active_text and "período eleitoral" in historical_text
    assert "30/09/2026" in active_text
    assert "nota da API" in active_text
    assert "01/10/2026" in active_text
    assert "não comprova operação uniforme" in active_text
    # Lista oficial de municípios com vagas de 09/10/2026, que substitui a de 03/09/2026.
    assert "09/10/2026" in active_text
    assert "1.500 municípios" in active_text
    assert "3.000 vagas totais" in active_text
    assert "926 preenchidas" in active_text
    assert "2.074 disponíveis" in active_text
    assert "lista vigente" not in active_text.casefold()
    assert "instabilidade observada" not in active_text
    assert "junho de 2026" in active_text
    assert "ciclo de maio de 2026" in historical_text
    assert "13/05/2026" not in historical_text
    assert "ciclo de regularização cadastral de maio de 2026" in historical_text
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

    # 26/10/2026: os avisos do MAPA e do período eleitoral do Farmácia Popular passaram ao histórico.
    # 20/10/2026: o aviso da instabilidade na consulta de empresas da Anvisa passou ao histórico; os demais sobem uma posição.
    # 19/10/2026, 15h40: o aviso da instabilidade nos sistemas da Anvisa é o ativo mais recente; os demais descem uma posição.
    # 17/10/2026, 09h50: o aviso do Farmácia Popular sobre lembretes é o ativo mais recente; os demais descem uma posição.
    # 16/10/2026, 20h06: o aviso do CNES 10/2026 é o ativo mais recente; os demais descem uma posição.
    assert titles == [
        "Farmácia Popular: confira a origem de mensagens pelo WhatsApp",
        "CNES: envio da competência 10/2026 aberto até 9 de novembro",
        "SNCR: cronograma anunciado e nota da API",
        "Farmácia Popular: confira municípios com vagas para credenciamento",
        "Farmácia Popular: confira as listas EAN vigentes e os controles de prescrição",
    ]
    assert all(timestamp for timestamp in timestamps)
    assert all(len([node for node in article.descendants() if node.tag == "time"]) == 1 for article in active)
    assert timestamps == sorted(timestamps, reverse=True)
    # Desde 26/10/2026 não há aviso URGENTE ativo (o do período eleitoral passou ao histórico).
    assert not any("URGENTE" in article.text() for article in active)

    # O CTA informativo de referência passa a ser o do CNES 10/2026 (o do MAPA saiu com o aviso, em 26/10/2026; antes, o da
    # Polícia Federal, em 16/10/2026).
    useful_badge = next(node for node in active[4].descendants() if node.tag == "span" and node.text() == "ÚTIL")
    useful_cta = next(node for node in active[4].descendants() if node.tag == "a" and "Conferir orientações" in node.text())
    informative_cta = next(node for node in active[1].descendants() if node.tag == "a" and "Leia a notícia sobre a competência 10/2026" in node.text())
    assert {"border-emerald-200", "bg-emerald-50", "text-emerald-700"} <= set(useful_badge.attrs["class"].split())
    assert {"border-emerald-200", "bg-emerald-50"} <= set(active[4].attrs["class"].split())
    # Desde 23/10/2026 os botões dos avisos são o secundário do site (assets/css/botoes.css), iguais nos
    # quatro tipos: a cor do tipo fica no card e no selo, não no botão.
    assert useful_cta.attrs["class"].split() == informative_cta.attrs["class"].split() == ["botao", "botao--secundario"]
    assert "comunicado-util__cta" not in useful_cta.attrs["class"].split()
    assert "bg-white" not in useful_cta.attrs["class"].split()
    assert "bg-emerald-50" not in useful_cta.attrs["class"].split()
    assert ".comunicado-util__cta" not in source
    assert "comunicado-cta" not in source

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
    # 26/10/2026: os avisos do período eleitoral do Farmácia Popular (25/10) e do marco de 23/10 do MAPA (ENCERRADO)
    # entram no topo do histórico, o mais recente primeiro; os demais descem duas posições. Em 20/10/2026 o da
    # instabilidade na Anvisa, em 16/10/2026 o dos mapas de setembro da PF e em 11/10/2026 o do CNES 09/2026 tinham
    # entrado do mesmo modo.
    assert "ENCERRADO" in historical[0].text() and "26/10/2026 • 08h30" in historical[0].text()
    assert "Farmácia Popular: atenção aos materiais no período eleitoral" in historical[0].text()
    assert "ENCERRADO" in historical[1].text() and "26/10/2026 • 08h30" in historical[1].text()
    assert "MAPA: estoques de aditivos com antimicrobianos do Anexo têm marco em 23/10" in historical[1].text()
    assert all("Ver histórico completo" in article.text() for article in historical[:3])
    assert "ENCERRADO" in historical[2].text() and "20/10/2026 • 14h50" in historical[2].text()
    assert "Instabilidade na consulta de empresas da Anvisa (19/10/2026)" in historical[2].text()
    assert "Ver histórico completo" in historical[2].text()
    assert "ENCERRADO" in historical[3].text() and "16/10/2026 • 15h55" in historical[3].text()
    assert "Polícia Federal: prazo dos mapas de setembro dos produtos químicos controlados terminou em 15/10" in historical[3].text()
    assert "ENCERRADO" in historical[4].text() and "11/10/2026 • 06h07" in historical[4].text()
    assert "CNES: envio da competência 09/2026 foi prorrogado até 9 de outubro" in historical[4].text()
    assert "ENCERRADO" in historical[5].text() and "09/10/2026 • 20h25" in historical[5].text()
    assert "Edital 6/2026: AFE para manipulação de preparações estéreis" in historical[5].text()
    assert "ENCERRADO" in historical[6].text() and "07/10/2026 • 10h53" in historical[6].text()
    assert "ciclo de regularização cadastral de maio de 2026" in historical[6].text()
    assert "Ver registro do ciclo" in historical[6].text()
    assert "O que fazer agora" not in historical[6].text()
    assert not any(node.tag == "strong" and (node.text() or "") == "Atenção:" for node in historical[6].descendants())
    assert "HISTÓRICO" in historical[7].text() and "06/10/2026 • 14h27" in historical[7].text()
    assert "Anvisa suspende medicamento e proíbe produtos irregulares" in historical[7].text()
    assert "ENCERRADO" in historical[8].text() and "03/09/2026 • 22h49" in historical[8].text()
    assert "ciclo de renovação foi encerrado em 31 de agosto" in historical[8].text()
    assert "HISTÓRICO" in historical[9].text() and "20/05/2026 • 13h00" in historical[9].text()
    assert "HISTÓRICO • maio de 2026" not in historical[9].text()
    assert "HISTÓRICO" in historical[10].text() and "19/05/2026 • 09h00" in historical[10].text()
    assert "Cadastro Anvisa/Gov.br" in historical[10].text()
    assert [next(node.text() for node in article.descendants() if node.has_class("comunicado-historico__badge")) for article in historical] == ["ENCERRADO", "ENCERRADO", "ENCERRADO", "ENCERRADO", "ENCERRADO", "ENCERRADO", "ENCERRADO", "HISTÓRICO", "ENCERRADO", "HISTÓRICO", "HISTÓRICO", "ENCERRADO", "ENCERRADO"]
    assert all("NORMALIZADO" not in article.text() for article in historical)
    assert all("28/04/2026" in article.text() and "12h57" in article.text() for article in historical[11:])
    historical_icons = [
        node
        for article in historical
        for node in article.descendants()
        if node.has_class("comunicado-historico__icon")
    ]
    assert len(historical_icons) == 13
    assert all({"bg-slate-100", "w-9", "h-9"} <= set(node.attrs["class"].split()) for node in historical_icons)
    assert all(
        "text-slate-600" in next(node for node in icon.descendants() if node.tag == "svg").attrs["class"].split()
        for icon in historical_icons
    )
    historical_controls = [node for article in historical for node in article.descendants() if node.tag in {"a", "button"} and "comunicado-historico__control" in node.attrs.get("class", "").split()]
    assert len(historical_controls) == 16
    assert all({"botao", "botao--secundario"} <= set(node.attrs["class"].split()) for node in historical_controls)
    assert all(not any("blue" in class_name for class_name in node.attrs["class"].split()) for node in historical_controls)
    # O foco e o estado pressionado são os do botão secundário (sem regras próprias desde 23/10/2026).
    assert "#avisos-lista .comunicado-historico__control:" not in source
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
    context = new_context(browser, viewport={"width": 1280, "height": 900})
    page = context.new_page()
    try:
        page.goto(f"{site_url}/comunicado/", wait_until="networkidle")
        useful_cta = page.locator('a[href="/noticias/farmacia-popular-listas-ean-junho-2026/"]')
        # O CTA informativo de referência é o do CNES 10/2026 (o do MAPA saiu com o aviso, em 26/10/2026).
        informative_cta = page.locator(f'#avisos-lista a.botao--secundario[href="{CNES_10_ROUTE}"]')

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
        # Os dois são o botão secundário: o mesmo fundo branco, a mesma cor e a mesma borda.
        assert useful_normal["backgroundColor"] == informative_normal["backgroundColor"] == "rgb(255, 255, 255)"
        assert useful_normal["color"] == informative_normal["color"]
        assert useful_normal["borderColor"] == informative_normal["borderColor"]

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
        # Fora do mouse, os dois voltam ao fundo do secundário.
        assert computed_state(useful_cta)["backgroundColor"] == useful_normal["backgroundColor"]
        assert computed_state(informative_cta)["backgroundColor"] == informative_normal["backgroundColor"]
        useful_cta.focus()
        page.wait_for_timeout(250)
        useful_focus = computed_state(useful_cta)
        assert useful_focus["focusVisible"]
        assert useful_focus["backgroundColor"] == useful_normal["backgroundColor"]
    finally:
        context.close()


def test_javascript_constants_and_files_are_exactly_equivalent():
    expected_fallback = re.compile(r"^\s*var AVISOS_FALLBACK_COUNT = 5;$", re.MULTILINE)
    expected_version = re.compile(r"^\s*var AVISOS_STORAGE_VERSION = '2026-10-26-avisos-5';$", re.MULTILINE)
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
            assert badges[0].text() == "5", relative_path
            assert badges[0].text() != "3", relative_path
            svgs = [node for node in link.descendants() if node.tag == "svg"]
            assert len(svgs) == 1, relative_path
            assert svgs[0].attrs.get("aria-hidden") == "true", relative_path
            assert "AVISOS!" in link.text(), relative_path
        mobile_classes = mobile_links[0].attrs.get("class", "").split()
        assert "relative" in mobile_classes, relative_path
        assert "gap-2" in mobile_classes, relative_path
    assert pages_with_navbar == 106


def test_tablet_hide_regression_is_absent_and_navbar_rules_remain():
    forbidden = re.compile(
        r'@media\(min-width:768px\)and\(max-width:899px\)\{'
        r'#navbar#mobile-menua\[href="/comunicado/"\]\{display:none!important;?\}\}'
    )
    # O menu aberto também tem altura máxima e rolagem própria (telas baixas),
    # com a altura da faixa e da linha principal de cada faixa de largura, e a
    # coluna flutuante ancorada passa sob o cabeçalho fixo.
    required = (
        re.compile(r'#navbar>div:first-child>div>nav\{display:none!important;?\}'),
        re.compile(r'#navbar#mobile-menu:not\(\.hidden\)\{display:block!important;max-height:calc\(100vh-9\.8rem\);'
                   r'max-height:calc\(100dvh-9\.8rem\);overflow-y:auto;overscroll-behavior:contain;?\}'),
        re.compile(r'body:has\(#mobile-menu:not\(\.hidden\)\)\.floating-buttons\.floating-btn\{opacity:0;visibility:hidden;'
                   r'pointer-events:none;?\}'),
        re.compile(r'@media\(min-width:768px\)and\(max-width:899px\)\{#navbar#mobile-menu:not\(\.hidden\)\{'
                   r'max-height:calc\(100vh-8\.75rem\);max-height:calc\(100dvh-8\.75rem\);?\}\}'),
        re.compile(r'\.floating-buttons\.is-docked\{position:absolute;bottom:auto;z-index:40;?\}'),
        re.compile(r'@media\(min-width:900px\)and\(max-width:1180px\)\{'),
    )
    for path in CSS_PATHS:
        compact = re.sub(r"\s+", "", path.read_text(encoding="utf-8-sig"))
        assert not forbidden.search(compact), path
        assert "@media(max-width:899px){" in compact, path
        for rule in required:
            assert rule.search(compact), f"{path}: {rule.pattern}"


def test_fallback_is_five_before_delayed_sync(browser, site_url):
    context = new_context(browser)
    context.add_init_script(
        "const originalFetch = window.fetch.bind(window);"
        "window.fetch = (...args) => String(args[0]).endsWith('/comunicado/') ? new Promise(() => {}) : originalFetch(...args);"
    )
    page = context.new_page()
    try:
        page.goto(f"{site_url}/", wait_until="domcontentloaded")
        page.wait_for_function("[...document.querySelectorAll('.aviso-badge')].every(b => b.textContent.trim() === '5')")
        assert _badge_texts(page) == ["5", "5"]
        assert "3" not in _badge_texts(page)
    finally:
        context.close()


def test_old_storage_is_ignored_when_sync_fails(browser, site_url):
    context = new_context(browser)
    context.add_init_script("localStorage.setItem('avisos_count', '3'); localStorage.setItem('avisos_count_version', '2026-05-21-sncr');")
    page = context.new_page()
    page_errors = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    try:
        page.route("**/comunicado/", lambda route: route.abort("failed"))
        page.goto(f"{site_url}/", wait_until="domcontentloaded")
        page.wait_for_function("[...document.querySelectorAll('.aviso-badge')].every(b => b.textContent.trim() === '5')")
        assert _badge_texts(page) == ["5", "5"]
        assert "3" not in _badge_texts(page)
        assert not page_errors
    finally:
        context.close()


def test_successful_sync_persists_five_and_hides_zero(browser, site_url):
    for count in (5, 0):
        context = new_context(browser)
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
                assert _badge_texts(page) == ["5", "5"]
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
            context = new_context(browser, viewport={"width": width, "height": 900})
            page = context.new_page()
            try:
                if route != "/comunicado/":
                    page.route(
                        "**/comunicado/",
                        _notice_response(5),
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
                    assert mobile.locator(".aviso-badge").text_content().strip() == "5"
                elif width < 900:
                    assert top.is_visible(), (route, width)
                    assert toggle.is_visible(), (route, width)
                    toggle.click()
                    assert mobile.is_visible(), (route, width)
                    assert top.locator(".aviso-badge").is_visible(), (route, width)
                    assert mobile.locator(".aviso-badge").is_visible(), (route, width)
                    assert top.evaluate("element => getComputedStyle(element).display") != "none"
                    assert mobile.evaluate("element => getComputedStyle(element).display") != "none"
                    assert top.locator(".aviso-badge").text_content().strip() == "5"
                    assert mobile.locator(".aviso-badge").text_content().strip() == "5"
                else:
                    assert top.is_visible(), (route, width)
                    assert not toggle.is_visible(), (route, width)
                    assert not mobile_menu.is_visible(), (route, width)
                    assert top.locator(".aviso-badge").is_visible(), (route, width)
                    assert top.locator(".aviso-badge").text_content().strip() == "5"
            finally:
                context.close()
