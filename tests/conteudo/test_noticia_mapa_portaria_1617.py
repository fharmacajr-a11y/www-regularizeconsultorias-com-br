import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit


ROOT = Path(__file__).resolve().parent.parent.parent
INDEX = ROOT / "noticias" / "index.html"
SITEMAP = ROOT / "sitemap.xml"
COMUNICADO = ROOT / "comunicado" / "index.html"
SLUG = "mapa-portaria-1617-2026-aditivos-antimicrobianos-alimentacao-animal"
ARTICLE = ROOT / "noticias" / SLUG / "index.html"
DRAFT = ROOT / "noticias" / "a-publicar" / SLUG / "index.html"
# 06/10/2026: "restringe" deu lugar a "proíbe", com o objeto limitado aos aditivos
# melhoradores de desempenho do Anexo (art. 1º da Portaria SDA/MAPA nº 1.617/2026).
TITLE = "MAPA proíbe aditivos melhoradores de desempenho com antimicrobianos do Anexo"
DESCRIPTION = (
    "A Portaria SDA/MAPA nº 1.617/2026 proíbe aditivos melhoradores de desempenho com os "
    "antimicrobianos do Anexo e cancela os registros. O tratamento dos estoques depende do caso."
)
PUBLIC_URL = f"https://www.regularizeconsultorias.com.br/noticias/{SLUG}/"
STAMP = "2026-10-03T00:33:00-03:00"
# 26/10/2026, 08h30: quadro "Atualização em 26/10/2026" (marco de 23/10 encerrado).
# 28/10/2026, 18h50 (hora do commit): quadro "Atualização em 28/10/2026" (Ofício-Circular
# nº 75/2026, datas a confirmar).
UPDATED = "2026-10-28T18:50:00-03:00"
SOURCES = (
    "https://www.in.gov.br/en/web/dou/-/portaria-sda/mapa-n-1.617-de-24-de-abril-de-2026-701457881",
    "https://www.gov.br/agricultura/pt-br/assuntos/insumos-agropecuarios/insumos-pecuarios/alimentacao-animal/copy_of_PORTARIASDA_MAPAN1.617DE24DEABRILDE2026PORTARIASDA_MAPAN1.617DE24DEABRILDE2026DOUImprensaNacional.pdf",
    "https://www.gov.br/agricultura/pt-br/assuntos/insumos-agropecuarios/insumos-pecuarios/alimentacao-animal/SEI_52249020_Oficio_Circular_29.pdf",
    "https://www.gov.br/agricultura/pt-br/assuntos/insumos-agropecuarios/insumos-pecuarios/alimentacao-animal/legislacao-alimentacao-animal",
)


class _JsonLd(HTMLParser):
    def __init__(self):
        super().__init__()
        self.blocks = []
        self._current = None

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "script" and dict(attrs).get("type") == "application/ld+json":
            self._current = []

    def handle_data(self, data):
        if self._current is not None:
            self._current.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self._current is not None:
            self.blocks.append("".join(self._current))
            self._current = None


def _jsonld(html):
    parser = _JsonLd()
    parser.feed(html)
    return [json.loads(block) for block in parser.blocks]


def _cards(html):
    return re.findall(
        r"(<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>)",
        html,
        re.DOTALL,
    )


def test_portaria_1617_is_published_at_the_public_url():
    html = ARTICLE.read_text(encoding="utf-8")

    assert ARTICLE.is_file()
    assert not DRAFT.exists()
    assert not (ROOT / "noticias" / "a-publicar").exists()
    assert "a-publicar" not in html
    assert "noindex" not in html.casefold()
    assert f"<title>{TITLE} | Regularize Consultoria</title>" in html
    assert "<h1 class=" in html and TITLE in html
    assert "article-hero-atualizacao" in html and "article-hero-informativo" not in html
    assert "article-badge-atualizacao" in html and "article-badge-informativo" not in html
    assert ">Atualização<" in html and ">Informativo<" not in html
    assert "category-chip--mapa" in html
    assert ">M.A.P.A<" in html
    assert f'<link rel="canonical" href="{PUBLIC_URL}" />' in html
    assert f'<meta property="og:url" content="{PUBLIC_URL}" />' in html
    assert f'<meta property="article:published_time" content="{STAMP}" />' in html
    assert f'<meta property="article:modified_time" content="{UPDATED}" />' in html
    assert f'<time datetime="{STAMP}">03/10/2026</time> às 00h33' in html
    assert f'Atualizado em:</span> <time datetime="{UPDATED}">28/10/2026</time> às 18h50' in html
    assert "restring" not in html.casefold()
    # O H1 tem hífens opcionais em "melhora&shy;dores" e "antimicro&shy;bianos" (layout comum, 10/10/2026); sem eles,
    # o título aparece nos mesmos cinco lugares.
    assert html.replace("&shy;", "").count(TITLE) == 5
    assert ">MAPA proíbe aditivos melhora&shy;dores de desempenho com antimicro&shy;bianos do Anexo</h1>" in html
    assert html.count(DESCRIPTION) == 4
    assert (
        "Ela proíbe a importação, a fabricação, a comercialização e o uso de aditivos melhoradores de "
        "desempenho que contenham os antimicrobianos do Anexo e cancela os registros desses produtos."
    ) in html
    assert html.count("pagead2.googlesyndication.com/pagead/js/adsbygoogle.js") == 1
    assert "adsbygoogle.push" not in html

    blocks = _jsonld(html)
    article = next(block for block in blocks if block["@type"] == "NewsArticle")
    assert article["headline"] == TITLE
    assert article["description"] == DESCRIPTION
    assert article["datePublished"] == STAMP
    assert article["dateModified"] == UPDATED
    assert article["url"] == PUBLIC_URL
    assert article["articleSection"] == "M.A.P.A"
    assert article["author"]["name"] == "Júnior Costa"
    assert article["publisher"]["name"] == "Regularize Consultoria"
    assert article["mainEntityOfPage"]["@id"] == PUBLIC_URL

    breadcrumb = next(block for block in blocks if block["@type"] == "BreadcrumbList")
    third = breadcrumb["itemListElement"][2]
    assert third["position"] == 3
    assert third["name"] == "Aditivos com antimicrobianos"
    assert third["item"] == PUBLIC_URL

    assert "<h2>Fontes oficiais</h2>" not in html
    for source in SOURCES:
        assert source not in html
    assert "Aviso institucional" in html
    assert "Precisa avaliar a situação regulatória no MAPA?" in html
    assert "análise regulatória" in html or "situação regulatória" in html
    assert "SIPEAGRO" in html
    for fact in (
        "24 de abril de 2026",
        "27/04/2026",
        "23/10/2026",
        "21/01/2027",
        "Ofício-Circular nº 29/2026",
        "Diário Oficial da União",
        "edição 77",
        "avoparcina",
        "bacitracina de zinco",
        "bacitracina metileno disalicilato",
        "virginiamicina",
    ):
        assert fact in html

    folded = html.casefold()
    for forbidden in (
        "todos os produtos",
        "prazo de transição vai até outubro",
        "prazo geral",
        "qualquer produto",
        "todas as empresas",
        "passo a passo",
        "como recolher",
        "como preencher",
        "como formular",
        "substituir o antimicrobiano",
        "como solicitar",
        "como inutilizar",
        "como reformular",
    ):
        assert forbidden not in folded
    assert "Sistema Eletrônico de Informações" not in html

    href = re.search(r'href="(/whatsapp/\?text=[^"]+)"', html).group(1)
    message = unquote(parse_qs(urlsplit(href).query)["text"][0])
    assert message.startswith("Olá!")
    assert "(19) 99627-5900" in html


def test_portaria_1617_enters_the_public_listing_itemlist_and_sitemap():
    index = INDEX.read_text(encoding="utf-8")
    sitemap = SITEMAP.read_text(encoding="utf-8")
    comunicado = COMUNICADO.read_text(encoding="utf-8")
    cards = _cards(index)

    assert "a-publicar" not in index
    assert "a-publicar" not in sitemap
    # O aviso do Comunicado de 06/10/2026 (marco de 23/10) é o único que leva à matéria.
    assert comunicado.count(f'href="/noticias/{SLUG}/"') == 1
    assert len(cards) == 85
    assert index.count("data-news-card") == 85
    assert "85 notícias encontradas" in index
    assert '>Todos</span><span class="text-xs text-slate-400">85<' in index
    assert '>ANVISA</span><span class="text-xs text-slate-400">54<' in index
    assert '>M.A.P.A</span><span class="text-xs text-slate-400">3<' in index
    assert len(re.findall(r'\bdata-category="mapa"', index)) == 3

    # Lote de 09/10/2026: as 13 matérias atualizadas no lote sobem pelo carimbo; as demais descem.
    # 11/10/2026, 06h07: a atualização do CNES 09/2026 (prazo encerrado, item 48) leva aquele card ao 1º lugar; os cards das posições 1 a 31 descem uma.
    # 16/10/2026, 20h06: o card do CNES 10/2026 entra na 1ª posição da listagem; os demais descem uma.
    # 17/10/2026, 09h50: o card do esclarecimento do Farmácia Popular entra na 1ª posição da listagem; os demais descem uma.
    # 20/10/2026, 10h12: os cards do consolidado de produtos irregulares e do SISPA sobem para a 1ª e a 2ª posições; os que ficavam entre eles descem uma.
    # 26/10/2026, 08h30: as matérias do MAPA 1.617 e do período eleitoral, atualizadas, sobem para a 1ª e a 2ª posições; as que ficavam acima delas descem duas (até a 6ª) ou uma (da 8ª à 35ª).
    # 28/10/2026, 18h50 (hora do commit): a matéria do MAPA 1.617 (Ofício-Circular nº 75/2026) e o consolidado de irregulares (RE nº 4.160, 4.228, 4.231 e 4.232/2026) recebem o mesmo carimbo; o MAPA segue em 1º, o consolidado sobe para o 2º e o período eleitoral e o SNCR descem para o 3º e o 4º.
    card = cards[0]
    opening = card.split(">", 1)[0]
    assert f'href="/noticias/{SLUG}/"' in card
    assert index.count(f'href="/noticias/{SLUG}/"') == 1
    assert "news-card-compact" in opening
    assert 'data-category="mapa"' in opening
    assert f'data-updated="{UPDATED}"' in opening
    assert "news-amber-card" in opening and "orange" not in card
    assert f'data-title="{TITLE}"' in opening
    assert f'data-summary="{DESCRIPTION}"' in opening
    assert ">Atualização<" in card and ">Informativo<" not in card
    assert "Ler atualização" in card
    assert ">M.A.P.A<" in card
    assert f'<time datetime="{UPDATED}" class="leading-none">28/10/2026 • 18h50</time>' in card
    # Modelo único (12/10/2026, R1): todos os cards levam news-card-compact; a posição não troca o formato.
    assert all("news-card-compact" in item.split(">", 1)[0] for item in cards)
    assert "cadastro-anvisa-govbr-transicao-sistemas" in cards[32]

    collection = next(block for block in _jsonld(index) if block.get("@type") == "CollectionPage")
    items = collection["mainEntity"]["itemListElement"]
    assert len(items) == 85
    assert items[0]["position"] == 1
    assert items[0]["url"] == PUBLIC_URL
    assert [item["position"] for item in items] == list(range(1, 86))
    assert sitemap.count(f"<loc>{PUBLIC_URL}</loc>") == 1
    assert f"<loc>{PUBLIC_URL}</loc>\n    <lastmod>2026-10-28</lastmod>" in sitemap
    # 13/10/2026: a listagem reordenou produtos irregulares, SNCR e DCB. 20/10/2026: reordenou produtos irregulares e SISPA.
    # 21/10/2026: reordenou produtos irregulares.
    assert (
        # 22/10/2026: a listagem reordenou produtos irregulares e SNCR.
        # 26/10/2026: a listagem reordenou os cards do MAPA 1.617 e do período eleitoral, atualizados no mesmo lote.
        # 28/10/2026: a listagem reordenou os cards do MAPA 1.617 e de produtos irregulares, atualizados no mesmo lote.
        "<loc>https://www.regularizeconsultorias.com.br/noticias/</loc>\n"
        "    <lastmod>2026-10-28</lastmod>"
    ) in sitemap


def _text(html):
    # O negrito das datas e o <wbr> do número do ofício não separam palavras: "<strong>24/10/2026</strong>." vira
    # "24/10/2026.".
    html = re.sub(r"</?strong>|<wbr>", "", html)
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def _callout(html, label):
    start = html.index(f'data-news-update-callout aria-labelledby="{label}"')
    return html[start:html.index("</aside>", start)]


def _blocks(html):
    """Parágrafos, títulos e o subtítulo do herói da matéria, em texto corrido."""
    main = html[html.index("<main>"):html.index('<section class="article-important-notice')]
    return [_text(block) for block in re.findall(r"<(?:p|h1|h2)\b[^>]*>(.*?)</(?:p|h1|h2)>", main, re.DOTALL)]


def test_portaria_1617_registers_oficio_circular_75_and_the_divergence_as_a_confirmar():
    # Rodada de 28/10/2026 (item A1): Ofício-Circular nº 75/2026/CGIPE/DSA/SDA/MAPA, assinado em 19/10/2026, conferido no
    # PDF publicado pelo MAPA. Do OC 75 a matéria cita só o que o PDF diz: número, assinatura, datas e uso terapêutico.
    html = ARTICLE.read_text(encoding="utf-8")
    callout = _callout(html, "mapa-atualizacao-28-outubro-title")
    text = _text(callout)

    # O quadro novo fica no topo do corpo, acima do de 26/10/2026; datePublished e slug não mudam.
    assert html.index("data-news-update-callout") == html.index(
        'data-news-update-callout aria-labelledby="mapa-atualizacao-28-outubro-title"')
    assert html.index('aria-labelledby="mapa-atualizacao-28-outubro-title"') < html.index(
        'aria-labelledby="mapa-atualizacao-26-outubro-title"')
    assert html.count("data-news-update-callout") == 2
    assert ">Atualização em 28/10/2026</h2>" in callout and "ATUALIZAÇÃO" in callout
    assert f'"datePublished": "{STAMP}"' in html and f'<link rel="canonical" href="{PUBLIC_URL}" />' in html

    assert text.endswith(
        "O Ofício-Circular nº 75/2026/CGIPE/DSA/SDA/MAPA, assinado em 19/10/2026, trata da Portaria SDA/MAPA nº 1.617/2026. "
        "Segundo esse ofício, o prazo final para comercialização e utilização dos produtos fabricados ou importados antes da "
        "entrada em vigor da Portaria é 24/10/2026. A partir de 25/10/2026, os produtos à base desses antimicrobianos, quando "
        "registrados como aditivos melhoradores de desempenho, não podem mais ser comercializados nem utilizados, exceto nas "
        "situações autorizadas para uso terapêutico. Os estabelecimentos fabricantes ou importadores têm até 23/01/2027 para "
        "recolher os estoques remanescentes nos estabelecimentos comerciais e nos fabricantes de produtos destinados à "
        "alimentação animal. O ofício também diz que “permanece autorizado o uso terapêutico de produtos que contenham essas "
        "substâncias”. Essas datas diferem das do Ofício-Circular nº 29/2026, que traz 23/10/2026 e 21/01/2027. Até "
        "28/10/2026, o MAPA não publicou esclarecimento sobre qual delas prevalece. Quem tem estoque ou recolhimento a fazer "
        "deve confirmar diretamente com o MAPA.")
    assert "href=" not in callout and "http" not in callout and "gov.br" not in callout
    # Nada que o PDF não diga: sem página do MAPA, destinatário ou hora de consulta no quadro.
    for absent in ("Memorandos", "11h46", "SISAs", "14h53", "página"):
        assert absent not in text, absent

    # Nenhuma data é escolhida: "prevalece" só aparece em "qual ... prevalece", e o uso terapêutico não é ampliado.
    page_text = _text(html)
    assert page_text.count("prevalece") == len(re.findall(r"qual (?:delas|das datas) prevalece", page_text)) == 5
    folded = page_text.casefold()
    for wrong in ("data correta", "data válida", "data que vale", "passa a valer", "substitui o ofício",
                  "revoga o ofício", "retifica o ofício", "uso terapêutico liberado", "liberad", "datas oficiais",
                  "prazos informados pelo ministério", "fixado pelo ministério", "informado pelo ministério"):
        assert wrong not in folded, wrong
    assert html.count("uso terapêutico") == 2

    # Toda frase com 23/10/2026 ou 21/01/2027 diz que a data vem do OC 29, pelo número ou por "esse ofício" e "o mesmo
    # ofício" logo depois dele. No quadro "Prazos do Ofício-Circular nº 29/2026", a atribuição fecha o próprio quadro.
    for block in _blocks(html):
        if "constam do Ofício-Circular nº 29/2026" in block:
            continue
        for sentence in re.split(r"(?<=[.;])\s+(?=[A-ZÀ-Ý0-9])", block):
            if "23/10/2026" in sentence or "21/01/2027" in sentence:
                assert re.search(r"Ofício-Circular nº 29/2026|esse ofício|mesmo ofício", sentence), sentence

    for after in (
        "O Ofício-Circular nº 29/2026 fixou o marco de 23/10/2026 para situações específicas de estoque e o recolhimento dos "
        "estoques remanescentes até 21/01/2027; o Ofício-Circular nº 75/2026 traz 24/10/2026 e 23/01/2027, e o MAPA não "
        "esclareceu, até 28/10/2026, qual das datas prevalece.",
        "O marco de 23/10/2026, do Ofício-Circular nº 29/2026/CGIPE/DSA/SDA/MAPA, passou.",
        "Pelo mesmo ofício, continua o prazo de recolhimento: o detentor do registro deve recolher os estoques remanescentes "
        "do aditivo até 21/01/2027. O Ofício-Circular nº 75/2026 traz outras datas (veja a atualização de 28/10/2026, acima).",
        "Pelo mesmo ofício, o recolhimento dos estoques remanescentes desses aditivos, nas hipóteses aplicáveis, vai até "
        "21/01/2027. O Ofício-Circular nº 75/2026 indica 24/10/2026 como prazo final de comercialização e utilização e "
        "23/01/2027 para o recolhimento; até 28/10/2026, o MAPA não esclareceu qual das datas prevalece.",
        "O marco de 23/10/2026 no Ofício-Circular nº 29/2026 e o que vem depois",
        "Prazos do Ofício-Circular nº 29/2026",
        "As datas de 23/10/2026 e 21/01/2027 são as do Ofício-Circular nº 29/2026; o Ofício-Circular nº 75/2026 traz "
        "24/10/2026 e 23/01/2027, e qual delas prevalece está a confirmar com o MAPA.",
    ):
        assert after in page_text, after[:70]
    for before in (
        "O marco de 23/10/2026, fixado pelo Ministério",
        "O marco de 23/10/2026 passou.",
        "Continua o prazo de recolhimento",
        "<h2>O marco de 23/10/2026 e o que vem depois</h2>",
        "O Ofício-Circular expressa",
        "O Ofício-Circular fixa",
        "O Ofício-Circular é dirigido",
    ):
        assert before not in html, before


def test_comunicado_mapa_card_stays_closed_with_the_oficio_75_in_its_history():
    html = COMUNICADO.read_text(encoding="utf-8")
    cards = re.findall(r'(<article\b[^>]*data-category="mapa"[^>]*>.*?</article>)', html, re.DOTALL)
    assert len(cards) == 1
    card = cards[0]
    opening = card.split(">", 1)[0]

    # Continua encerrado, sem id próprio (como desde 26/10/2026), com o selo e a data do encerramento.
    assert opening == ('<article data-status="resolved" data-category="mapa" data-updated-at="06/10/2026 às 08h00" '
                       'data-resolved-at="26/10/2026 às 08h30" data-aviso-history-card class="comunicado-historico '
                       'rounded-2xl border border-slate-300 bg-slate-50 p-5 shadow-sm md:p-6"')
    assert ">ENCERRADO</span>" in card
    assert '<time datetime="2026-10-26T08:30:00-03:00">26/10/2026 • 08h30</time>' in card
    # O contador AVISOS não muda: cinco avisos ativos, treze no histórico.
    assert len(re.findall(r'data-status="resolved"', html)) == 13
    assert len(re.findall(r'<article\b[^>]*data-status="(?!resolved)[^"]+"', html)) == 5
    assert html.count('text-xs font-bold flex items-center justify-center shadow border border-red-200">5</span>') == 2

    # Texto final: o recolhimento até 21/01/2027 é o do OC 29; o OC 75 não aparece fora do histórico.
    history_start = card.index('<div id="aviso-historico-mapa-portaria-1617"')
    visible, history = card[:history_start], card[history_start:]
    assert ("Pelo Ofício-Circular nº 29/2026, continua o prazo de recolhimento: o detentor do registro deve recolher os "
            "estoques remanescentes do aditivo até 21/01/2027. Encerramos este comunicado.") in _text(visible)
    assert "75/2026" not in visible and "28/10/2026" not in visible

    # Histórico: o OC 75 e a divergência, com data de 28/10/2026, depois do texto de 06/10/2026.
    paragraphs = [_text(p) for p in re.findall(r"<p>(.*?)</p>", history, re.DOTALL)]
    assert paragraphs[-1] == (
        "Atualização em 28/10/2026: o Ofício-Circular nº 75/2026/CGIPE/DSA/SDA/MAPA, assinado em 19/10/2026, indica "
        "24/10/2026 como prazo final de comercialização e utilização dos produtos fabricados ou importados antes da entrada "
        "em vigor da Portaria. A partir de 25/10/2026, os produtos à base desses antimicrobianos, quando registrados como "
        "aditivos melhoradores de desempenho, não podem mais ser comercializados nem utilizados, exceto nas situações "
        "autorizadas para uso terapêutico. Os fabricantes ou importadores têm até 23/01/2027 para o recolhimento dos "
        "estoques remanescentes. Essas datas diferem das do Ofício-Circular nº 29/2026 (23/10/2026 e 21/01/2027). Até "
        "28/10/2026, o MAPA não publicou esclarecimento sobre qual delas prevalece. Quem tem estoque ou recolhimento a "
        "fazer deve confirmar diretamente com o MAPA.")
    assert len(paragraphs) == 3
    assert "href=" not in history
    # Em 320 px o número inteiro do ofício passava da borda da coluna dos botões flutuantes; o <wbr> deixa quebrar depois
    # de "75/2026/".
    assert history.count("nº 75/2026/<wbr>CGIPE/DSA/SDA/MAPA") == 1
