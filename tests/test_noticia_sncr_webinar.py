import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit


ROOT = Path(__file__).parents[1]
NEWS_PATH = ROOT / "noticias" / "rdc-1000-2025-anvisa-prorroga-prazo-sncr" / "index.html"
NEWS_INDEX_PATH = ROOT / "noticias" / "index.html"
COMUNICADO_PATH = ROOT / "comunicado" / "index.html"
SERVICOS_PATH = ROOT / "servicos" / "index.html"
SITEMAP_PATH = ROOT / "sitemap.xml"
ROUTE = "/noticias/rdc-1000-2025-anvisa-prorroga-prazo-sncr/"
URL = f"https://www.regularizeconsultorias.com.br{ROUTE}"
PUBLISHED = "2026-05-28T20:36:00-03:00"
UPDATED = "2026-09-22T16:48:26-03:00"
TITLE = "SNCR: nova etapa começa em 30 de setembro; veja o que muda para farmácias e drogarias"
ADSENSE_SCRIPT_MARKER = "pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"
WHATSAPP_NEWS_TEXT = (
    "Olá! Vi a notícia da Regularize sobre o SNCR e gostaria de verificar "
    "a habilitação da minha farmácia."
)
WHATSAPP_SERVICO_TEXT = (
    "Olá! Gostaria de informações sobre o serviço de implantação e "
    "habilitação do SNCR para minha farmácia."
)
FORBIDDEN_CLAIMS = (
    "o sncr começa em 30",
    "o sncr começa em 30/09",
    "sncr começa em 30 de setembro de 2026",
    "prescrição eletrônica passa a ser obrigatória",
    "prescrição eletrônica se torna obrigatória",
    "substitui o sngpc",
    "29/10 invalida",
    "vence automaticamente",
    "garantimos acesso",
    "garantimos habilitação",
    "sua farmácia ficará irregular automaticamente",
    "obrigatório contratar",
    "prazo foi prorrogado novamente",
    "nova prorrogação foi anunciada",
    "prazo passa de 30/09/2026",
)


def _text(html):
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def _callout(html):
    start = html.index("<aside data-news-update-callout")
    return html[start:html.index("</aside>", start)]


def _news_cards(html):
    return re.findall(r"(<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>)", html, re.DOTALL)


def _active_notices(html):
    return [
        article
        for article in re.findall(r"(<article\b[^>]*>.*?</article>)", html, re.DOTALL)
        if 'data-status="resolved"' not in article.split(">", 1)[0]
    ]


def _jsonld_blocks(html):
    pattern = re.compile(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>', re.DOTALL
    )
    return [json.loads(match.group(1)) for match in pattern.finditer(html)]


def test_sncr_news_keeps_publication_and_updates_the_september_stage():
    html = NEWS_PATH.read_text(encoding="utf-8")
    callout = _callout(html)
    callout_text = _text(callout)

    assert f"<title>{TITLE} | Regularize Consultoria</title>" in html
    assert f'"datePublished": "{PUBLISHED}"' in html
    assert f'"dateModified": "{UPDATED}"' in html
    assert datetime.fromisoformat(UPDATED) > datetime.fromisoformat(PUBLISHED)
    assert f'<meta property="article:published_time" content="{PUBLISHED}" />' in html
    assert f'<meta property="article:modified_time" content="{UPDATED}" />' in html
    assert f'<time datetime="{PUBLISHED}">28/05/2026</time> às 20h36' in html
    assert f'<time datetime="{UPDATED}">22/09/2026</time> às 16h48' in html
    assert f'<link rel="canonical" href="{URL}" />' in html
    assert html.count(ADSENSE_SCRIPT_MARKER) == 1
    assert html.count("data-news-update-callout") - html.count("[data-news-update-callout]") == 1
    assert 'href="https://www.gov.br/anvisa/pt-br/assuntos/medicamentos/controlados/sncr"' in html

    news = next(block for block in _jsonld_blocks(html) if block.get("@type") == "NewsArticle")
    assert news["headline"] == TITLE
    assert news["datePublished"] == PUBLISHED
    assert news["dateModified"] == UPDATED
    assert news["url"] == URL

    assert "ATUALIZAÇÃO" in callout_text
    for term in (
        "Nova etapa do SNCR em 30/09/2026",
        "30/09/2026",
        "amplia o suporte ao fluxo eletrônico",
        "prescrição eletrônica continua facultativa",
        "não substitui a escrituração no SNGPC",
    ):
        assert term in callout_text
    assert "href=" not in callout


def test_sncr_news_explains_the_stage_without_false_claims():
    html = NEWS_PATH.read_text(encoding="utf-8")
    body = _text(re.search(r'<section class="article-body">(.*?)</section>', html, re.DOTALL).group(1))

    for term in (
        "SNCR já está em funcionamento",
        "30 de setembro de 2026",
        "Notificações de Receita",
        "Receitas de Controle Especial",
        "receitas sujeitas à retenção",
        "30/09/2026 e 29/10/2026",
        "30/10/2026",
        "Gov.br",
        "Cadastro Anvisa",
        "análise cadastral do estabelecimento",
        "cartilha oficial da Anvisa",
        "Fonte",
    ):
        assert term in body or term in html

    assert "passam a poder ser emitidas eletronicamente" in html
    assert "já podem ser emitidas eletronicamente" in html
    assert "recebem numeração do sistema" in html or "recebem numeração do SNCR" in html
    assert "prazo de validade da prescrição" in html
    assert "e-CNPJ" not in html

    for path in (NEWS_PATH, NEWS_INDEX_PATH, COMUNICADO_PATH, SERVICOS_PATH):
        text = _text(path.read_text(encoding="utf-8")).casefold()
        for claim in FORBIDDEN_CLAIMS:
            assert claim not in text, (path.relative_to(ROOT), claim)


def test_sncr_card_is_unique_current_and_featured_in_the_news_listing():
    html = NEWS_INDEX_PATH.read_text(encoding="utf-8")
    cards = _news_cards(html)
    sncr_cards = [card for card in cards if f'href="{ROUTE}"' in card]

    assert html.count(f'href="{ROUTE}"') == 1
    assert len(sncr_cards) == 1
    card = sncr_cards[0]
    assert cards.index(card) == 0
    assert "news-card-compact" not in card.split(">", 1)[0]
    assert f'data-updated="{UPDATED}"' in card
    assert f'<time datetime="{UPDATED}" class="leading-none">22/09/2026 • 16h48</time>' in card
    for term in (
        "SNCR: nova etapa começa em 30 de setembro",
        "farmácias e drogarias",
        "30/09/2026",
        "já existe",
        "SNGPC",
    ):
        assert term in card


def test_comunicado_keeps_one_sncr_card_and_six_active_notices():
    html = COMUNICADO_PATH.read_text(encoding="utf-8")
    active = _active_notices(html)
    sncr_cards = [article for article in active if 'data-category="sncr"' in article]

    assert html.count('data-category="sncr"') == 1
    assert html.count(f'href="{ROUTE}"') == 1
    assert len(active) == 6
    assert re.findall(r'class="aviso-badge[^"]*">(\d+)</span>', html) == ["6", "6"]
    assert len(sncr_cards) == 1
    card_text = _text(sncr_cards[0])
    for term in (
        "SNCR: nova etapa começa em 30/09",
        "Farmácias e drogarias",
        "receituários eletrônicos",
        "SNCR já existe",
        "30/09/2026",
        "Leia a orientação completa",
    ):
        assert term in card_text
    assert active[0] is sncr_cards[0]


def test_sncr_news_has_current_sitemap_lastmod():
    sitemap = SITEMAP_PATH.read_text(encoding="utf-8")

    assert sitemap.count(f"<loc>{URL}</loc>") == 1
    assert f"<loc>{URL}</loc>\n    <lastmod>2026-09-22</lastmod>" in sitemap
    assert (
        "<loc>https://www.regularizeconsultorias.com.br/servicos/</loc>\n"
        "    <lastmod>2026-09-22</lastmod>"
    ) in sitemap


def test_sncr_news_cta_and_floating_whatsapp_use_the_service_message():
    html = NEWS_PATH.read_text(encoding="utf-8")
    assert "Solicitar análise para o SNCR" in html
    assert 'href="/servicos/#servico-sncr"' in html

    floating = re.search(
        r'<a href="(/whatsapp/\?text=[^"]+)"[^>]*class="[^"]*floating-btn--whatsapp',
        html,
    )
    assert floating is not None
    query = parse_qs(urlsplit(floating.group(1)).query)
    assert unquote(query["text"][0]) == WHATSAPP_NEWS_TEXT

    cta = re.search(
        r'article-final-cta__link--primary" href="(/whatsapp/\?text=[^"]+)"',
        html,
    )
    assert cta is not None
    cta_query = parse_qs(urlsplit(cta.group(1)).query)
    assert unquote(cta_query["text"][0]) == WHATSAPP_NEWS_TEXT


def test_servicos_sncr_card_describes_the_access_service():
    html = SERVICOS_PATH.read_text(encoding="utf-8")
    start = html.index('id="servico-sncr"')
    card = html[start:html.index("</article>", start)]
    text = _text(card)

    assert "Implantação e habilitação de acesso ao SNCR" in text
    for term in (
        "análise cadastral",
        "Cadastro Anvisa",
        "usuários e perfis",
        "não concede acesso",
        "Solicitar análise para o SNCR",
    ):
        assert term.casefold() in text.casefold()

    href = re.search(r'href="(/whatsapp/\?text=[^"]+)"', card).group(1)
    query = parse_qs(urlsplit(href).query)
    assert unquote(query["text"][0]) == WHATSAPP_SERVICO_TEXT
    assert "e-CNPJ" not in card
    assert "Implanta\\u00e7\\u00e3o e habilita\\u00e7\\u00e3o de acesso ao SNCR" in html
