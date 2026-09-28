import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
SLUG = "anvisa-proibe-propaganda-semavy-consumidor"
PAGE_PATH = ROOT / "noticias" / SLUG / "index.html"
INDEX_PATH = ROOT / "noticias" / "index.html"
SITEMAP_PATH = ROOT / "sitemap.xml"
OG_PATH = ROOT / "assets" / "img" / "og" / "noticias" / f"{SLUG}.webp"
PUBLIC_URL = f"https://www.regularizeconsultorias.com.br/noticias/{SLUG}/"
OG_URL = f"https://www.regularizeconsultorias.com.br/assets/img/og/noticias/{SLUG}.webp"
TIMESTAMP = "2026-09-28T08:58:47-03:00"
TITLE = "Anvisa proíbe propaganda do Semavy dirigida ao consumidor"
# Matérias que não devem receber o assunto nesta etapa.
UNTOUCHED_PAGES = (
    ROOT / "noticias" / "anvisa-suspende-medicamento-proibe-produtos-irregulares" / "index.html",
    ROOT / "noticias" / "rdc-1000-2025-anvisa-prorroga-prazo-sncr" / "index.html",
    ROOT / "noticias" / "cnes-continua-obrigatorio-sncr-afe-farmacias" / "index.html",
    ROOT / "comunicado" / "index.html",
)


def _page_html():
    return PAGE_PATH.read_text(encoding="utf-8")


def _index_html():
    return INDEX_PATH.read_text(encoding="utf-8")


def _jsonld_blocks(html):
    pattern = re.compile(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>', re.DOTALL
    )
    return [json.loads(match.group(1)) for match in pattern.finditer(html)]


def _article_body(html):
    match = re.search(
        r'<section class="article-body">(.*?)</section>', html, re.DOTALL
    )
    assert match is not None
    return match.group(1)


def _text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def _cards(html):
    return re.findall(
        r'(<article class="[^"]*"[^>]*data-news-card.*?</article>)', html, re.DOTALL
    )


def test_page_title_canonical_and_single_h1():
    html = _page_html()
    assert f"<title>{TITLE} | Regularize Consultoria</title>" in html
    assert f'<link rel="canonical" href="{PUBLIC_URL}"' in html
    assert f'<meta property="og:url" content="{PUBLIC_URL}"' in html
    assert re.findall(r"<h1\b[^>]*>(.*?)</h1>", html, re.DOTALL) == [TITLE]


def test_newsarticle_and_breadcrumb_are_consistent():
    blocks = _jsonld_blocks(_page_html())
    news = next(block for block in blocks if block.get("@type") == "NewsArticle")
    breadcrumb = next(
        block for block in blocks if block.get("@type") == "BreadcrumbList"
    )

    assert news["headline"] == TITLE
    assert news["url"] == PUBLIC_URL
    assert news["mainEntityOfPage"]["@id"] == PUBLIC_URL
    assert news["articleSection"] == "ANVISA"
    assert news["image"] == OG_URL
    assert "RE 3.750/2026" in news["keywords"]
    assert breadcrumb["itemListElement"][-1]["item"] == PUBLIC_URL
    assert breadcrumb["itemListElement"][-1]["name"] == "Propaganda do Semavy"


def test_publication_date_is_editorial_and_not_an_update():
    html = _page_html()
    news = next(
        block for block in _jsonld_blocks(html) if block.get("@type") == "NewsArticle"
    )
    # A data do site é a da publicação editorial; 25/09 é apenas a data do fato.
    assert news["datePublished"] == TIMESTAMP
    assert news["dateModified"] == TIMESTAMP
    assert f'<meta property="article:published_time" content="{TIMESTAMP}"' in html
    assert f'<meta property="article:modified_time" content="{TIMESTAMP}"' in html
    assert f'<time datetime="{TIMESTAMP}">28/09/2026</time> às 08h58' in html
    assert "2026-09-25T" not in html
    assert "Atualizado em:" not in html
    assert "Atualização de" not in html
    assert "article-badge-informativo" in html
    assert ">Informativo</span>" in html


def test_article_reports_the_confirmed_facts():
    body = _text(_article_body(_page_html()))
    required = (
        "proibiu a propaganda do medicamento Semavy",
        "com semaglutida",
        "fabricado pela Cosmed",
        "25 de setembro de 2026",
        "Resolução-RE nº 3.750/2026",
        "painéis eletrônicos",
        "Aeroporto de Congonhas",
        "site do produto",
        "redes sociais",
        "tratamento de diabetes tipo 2 insuficientemente controlado",
        "publicidade dirigida ao público em geral",
        "profissionais habilitados a prescrever ou dispensar medicamentos",
    )
    for text in required:
        assert text in body, text


def test_measure_is_not_described_as_sale_ban_recall_fake_or_cancellation():
    body = _text(_article_body(_page_html()))
    assert (
        "não deve ser interpretada como proibição de venda, determinação de "
        "recolhimento, indicação de falsificação ou cancelamento do registro"
    ) in body
    assert "não descreve a situação regulatória do produto além do que foi informado" in body

    lowered = body.casefold()
    forbidden = (
        "proibiu a venda",
        "proíbe a venda",
        "venda proibida",
        "determinou o recolhimento",
        "determina o recolhimento",
        "foi recolhido",
        "é falsificado",
        "produto falsificado",
        "registro cancelado",
        "cancelou o registro",
        "produto proibido",
        "interditado",
        "suspensão do registro",
    )
    for text in forbidden:
        assert text not in lowered, text


def test_body_has_no_links_urls_sources_or_attachments():
    body = _article_body(_page_html())
    assert "<a " not in body
    assert "href=" not in body
    assert "http" not in body
    assert "www." not in body
    assert "gov.br" not in body
    assert ".pdf" not in body.casefold()
    assert not re.search(
        r"<h[1-6][^>]*>\s*(Fontes?|Bibliografia|Referências|Anexos?)", body, re.IGNORECASE
    )
    assert "Fonte oficial:" not in _page_html()


def test_body_has_no_treatment_dose_or_promotional_claims():
    body = _text(_article_body(_page_html())).casefold()
    forbidden = (
        " mg",
        "dose",
        "posologia",
        "aplicação semanal",
        "emagrec",
        "perda de peso",
        "perder peso",
        "eficaz",
        "resultado garantido",
        "compre",
        "promoção",
        "desconto",
    )
    for text in forbidden:
        assert text not in body, text
    assert "não constitui orientação de uso nem recomendação de tratamento" in body


def test_article_explains_relevance_without_ad_tutorial():
    body = _text(_article_body(_page_html()))
    assert "Por que o caso interessa a farmácias e empresas do setor" in body
    assert "Mídia exterior e ambientes digitais aparecem, assim, lado a lado" in body
    assert "o ponto central é a distinção feita pela Agência" in body
    lowered = body.casefold()
    for text in ("passo a passo", "como montar", "modelo de anúncio", "checklist"):
        assert text not in lowered, text


def test_article_drops_generalizations_without_primary_source():
    body = _text(_article_body(_page_html())).casefold()
    for text in (
        "atenção regulatória crescente",
        "supervisão do farmacêutico",
        "glp-1",
        "governança",
        "telas instaladas",
        "está no centro da medida",
        "não recebe o mesmo tratamento",
        "a medida noticiada diz respeito",
    ):
        assert text not in body, text


def test_navigation_contact_and_related_news_follow_site_pattern():
    html = _page_html()
    related = re.search(
        r'<section class="article-related-news".*?</section>', html, re.DOTALL
    )
    assert related is not None
    links = re.findall(r'href="(/noticias/[^"]+/)"', related.group(0))
    assert links == [
        "/noticias/anvisa-revisao-propaganda-medicamentos-alimentos/",
        "/noticias/farmaceutico-supervisiona-conteudos-farmacia-redes-sociais-sites/",
        "/noticias/anvisa-registra-cinco-medicamentos-semaglutida/",
    ]
    for link in links:
        assert (ROOT / link.strip("/") / "index.html").is_file(), link
    assert '<a class="article-back-link" href="/noticias/">Ver todas as notícias</a>' in html
    assert 'class="article-final-cta__link article-final-cta__link--primary" href="/contato/"' in html
    assert "article-important-notice" in html
    assert "propaganda%20do%20Semavy" in html
    assert html.count("pagead2.googlesyndication.com/pagead/js/adsbygoogle.js") == 1
    assert "adsbygoogle.push" not in html


def test_share_image_metadata_and_asset():
    html = _page_html()
    assert html.count(OG_URL) == 4
    assert '<meta property="og:image:type" content="image/webp"' in html
    assert '<meta property="og:image:width" content="1200"' in html
    assert '<meta property="og:image:height" content="630"' in html
    assert (
        '<meta property="og:image:alt" content="Card da Regularize sobre a proibição '
        'da propaganda do Semavy dirigida ao consumidor"' in html
    )
    with Image.open(OG_PATH) as image:
        assert image.size == (1200, 630)
        assert image.format == "WEBP"


def test_index_card_is_first_informativo_and_counts_are_updated():
    html = _index_html()
    cards = _cards(html)
    assert html.count(f'href="/noticias/{SLUG}/"') == 1
    assert len(cards) == 81
    card = cards[0]
    opening = card.split(">", 1)[0]
    assert f'href="/noticias/{SLUG}/"' in card
    assert "news-card-compact" not in opening
    assert 'data-category="anvisa"' in opening
    assert f'data-updated="{TIMESTAMP}"' in opening
    assert f'data-title="{TITLE}"' in opening
    assert f'<time datetime="{TIMESTAMP}" class="leading-none">28/09/2026 • 08h58</time>' in card
    assert "news-orange-badge" in card and ">Informativo</span>" in card
    assert "Ler notícia" in card
    assert "Atualização" not in card and "Ler atualização" not in card
    assert "81 notícias encontradas" in html
    assert '>Todos</span><span class="text-xs text-slate-400">81<' in html
    assert '>ANVISA</span><span class="text-xs text-slate-400">53<' in html


def test_index_card_is_searchable_by_product_substance_and_resolution():
    card = _cards(_index_html())[0]
    opening = card.split(">", 1)[0]
    tags = re.search(r'data-tags="([^"]*)"', opening).group(1).split()
    keywords = re.search(r'data-keywords="([^"]*)"', opening).group(1)
    for tag in ("semavy", "semaglutida", "propaganda", "re-3750-2026"):
        assert tag in tags, tag
    assert "RE 3.750/2026" in keywords
    assert "RE nº 3.750/2026" in card
    assert "Aeroporto de Congonhas" in card


def test_index_keeps_five_highlighted_cards_after_new_entry():
    classes = [
        re.search(r'<article class="([^"]*)"', card).group(1)
        for card in _cards(_index_html())
    ]
    assert all("news-card-compact" not in value for value in classes[:5])
    assert all("news-card-compact" in value for value in classes[5:])


def test_itemlist_lists_the_new_url_once_in_first_position():
    html = _index_html()
    collection = next(
        block for block in _jsonld_blocks(html) if block.get("@type") == "CollectionPage"
    )
    items = collection["mainEntity"]["itemListElement"]
    urls = [item["url"] for item in items]
    assert urls[0] == PUBLIC_URL
    assert urls.count(PUBLIC_URL) == 1
    assert [item["position"] for item in items] == list(range(1, len(items) + 1))
    assert len(items) == 81


def test_sitemap_contains_new_url_with_editorial_lastmod():
    namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    root = ET.parse(SITEMAP_PATH).getroot()
    matches = [
        item
        for item in root.findall("s:url", namespace)
        if item.findtext("s:loc", namespaces=namespace) == PUBLIC_URL
    ]
    assert len(matches) == 1
    assert matches[0].findtext("s:lastmod", namespaces=namespace) == "2026-09-28"
    assert matches[0].findtext("s:changefreq", namespaces=namespace) == "monthly"
    assert matches[0].findtext("s:priority", namespaces=namespace) == "0.8"


def test_subject_is_not_inserted_into_consolidated_sncr_cnes_or_comunicado():
    for path in UNTOUCHED_PAGES:
        html = path.read_text(encoding="utf-8")
        assert "Semavy" not in html, path.relative_to(ROOT)
        assert "3.750/2026" not in html, path.relative_to(ROOT)
        assert SLUG not in html, path.relative_to(ROOT)
