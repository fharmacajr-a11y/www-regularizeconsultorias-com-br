import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SLUG = "anvisa-in-470-2026-suplementos-ingredientes-limites-alegacoes"
PAGE_PATH = ROOT / "noticias" / SLUG / "index.html"
INDEX_PATH = ROOT / "noticias" / "index.html"
SITEMAP_PATH = ROOT / "sitemap.xml"
PUBLIC_URL = f"https://www.regularizeconsultorias.com.br/noticias/{SLUG}/"
TIMESTAMP = "2026-09-21T09:05:11-03:00"
TITLE = "IN 470/2026 atualiza constituintes, limites e alegações de suplementos alimentares"


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


def test_page_title_canonical_and_single_h1():
    html = _page_html()
    assert f"<title>{TITLE} | Regularize Consultoria</title>" in html
    assert f'<link rel="canonical" href="{PUBLIC_URL}"' in html
    assert len(re.findall(r"<h1\b", html, re.IGNORECASE)) == 1


def test_newsarticle_and_breadcrumb_are_consistent():
    blocks = _jsonld_blocks(_page_html())
    news = next(block for block in blocks if block.get("@type") == "NewsArticle")
    breadcrumb = next(
        block for block in blocks if block.get("@type") == "BreadcrumbList"
    )

    assert news["headline"] == TITLE
    assert news["url"] == PUBLIC_URL
    assert news["datePublished"] == TIMESTAMP
    assert news["dateModified"] == TIMESTAMP
    assert news["articleSection"] == "ANVISA"
    assert news["image"].endswith("/assets/img/og/noticias.jpg")
    assert breadcrumb["itemListElement"][-1]["item"] == PUBLIC_URL


def test_publication_metadata_is_synchronized_without_update_label():
    html = _page_html()
    assert f'content="{TIMESTAMP}"' in html
    assert f'<time datetime="{TIMESTAMP}">' in html
    assert "Atualizado em:" not in html


def test_article_identifies_norm_dates_and_changed_annexes():
    html = _page_html()
    assert "IN 470/2026" in html
    assert "IN 28/2018" in html
    assert "18 de setembro de 2026" in html
    assert "18/09/2026" in html
    for annex in ("Anexo I", "Anexo III", "Anexo IV", "Anexo V", "Anexo VI"):
        assert annex in html


def test_article_covers_every_constituent_included_by_in_470():
    html = _page_html()
    required = (
        "óleo de krill",
        "Euphausia superba",
        "L-cistina",
        "L-cisteína",
        "extrato das folhas de milho",
        "6-metoxi-2-benzoxazolinona",
        "hidrolisado da membrana da casca de ovo",
        "esqualeno obtido de fígado de tubarão",
        "glicosaminoglicanos",
        "peso molecular médio de 3 kDa",
    )
    assert all(text in html for text in required)


def test_article_has_correct_limits_and_explains_ne():
    html = _page_html()
    required = (
        "0,5 mg/dia",
        "1,5 mg/dia",
        "200 mg/dia",
        "637 mg/dia",
        "5 g/dia",
        "22,5 mg/dia",
        "19,2 para 22,5 mg/dia",
        "limite máximo não está estabelecido",
    )
    assert all(text in html for text in required)
    assert "consumo ilimitado" in html


def test_krill_requires_simultaneous_epa_dha_and_choline_limits():
    html = _page_html()
    assert "fonte de colina" in html
    assert "observados simultaneamente" in html
    assert "EPA e DHA" in html
    assert "krill tivesse sido autorizado pela primeira vez" in html


def test_three_authorized_claims_are_described_without_therapeutic_promise():
    html = _page_html()
    required = (
        "treinamento regular de resistência",
        "adultos com mais de 55 anos",
        "qualidade do sono",
        "saúde das articulações",
    )
    assert all(text in html for text in required)
    assert "Alegação autorizada não é promessa de tratamento, prevenção ou cura" in html


def test_creatine_is_not_presented_as_a_new_general_dose():
    html = _page_html()
    assert "não criou novos limites gerais de creatina" in html
    assert "limites mínimo e máximo já aplicáveis" in html
    forbidden = (
        "a in 470 criou a dose de creatina",
        "nova dose geral de creatina",
        "creatina trata",
    )
    assert all(text not in html.casefold() for text in forbidden)


def test_article_covers_all_required_warnings():
    html = _page_html()
    required = (
        "desordem severa do sono",
        "ansiedade",
        "depressão",
        "crianças abaixo de quatro anos",
        "Peptídeos bioativos de colágeno 3 kDa",
        "Hidrolisado da membrana da casca de ovo",
        "gestantes, lactantes e crianças",
    )
    assert all(text in html for text in required)


def test_transition_and_existing_products_are_treated_prudently():
    html = _page_html()
    assert "não estabelece prazo especial de transição" in html
    assert "todo produto existente esteja automaticamente irregular" in html
    assert "todos os rótulos devam ser substituídos" in html
    assert "procedimento regulatório aplicável" in html
    assert "revisar o portfólio e a rotulagem" in html


def test_article_is_normative_and_does_not_mix_enforcement_topics():
    body = _article_body(_page_html()).casefold()
    assert "não se trata de recolhimento, fiscalização ou medida cautelar" in body
    assert "anvisa-suspende-medicamento-proibe-produtos-irregulares" not in body


def test_og_uses_approved_fallback_and_public_alt():
    html = _page_html()
    assert html.count("https://www.regularizeconsultorias.com.br/assets/img/og/noticias.jpg") >= 4
    assert (
        '<meta property="og:image:alt" content="Anvisa atualiza regras para '
        'suplementos alimentares com a IN 470/2026"' in html
    )
    assert "OG temporária" not in html


def test_adsense_uses_one_canonical_snippet_without_manual_slot():
    html = _page_html()
    assert html.count("pagead2.googlesyndication.com/pagead/js/adsbygoogle.js") == 1
    assert html.count("ca-pub-2993532924249779") == 1
    assert "adsbygoogle.push" not in html


def test_article_body_has_no_government_links_or_sources_section():
    body = _article_body(_page_html())
    assert "gov.br" not in body
    assert "in.gov.br" not in body
    assert "anvisalegis" not in body
    assert not re.search(r"<h[1-6][^>]*>\s*(Fontes|Bibliografia)", body, re.IGNORECASE)


def test_index_has_one_card_in_first_position_and_expected_counts():
    html = _index_html()
    assert html.count(f'href="/noticias/{SLUG}/"') == 1
    assert html.count(f'"url":"{PUBLIC_URL}"') == 1
    cards = re.findall(
        r'<article class="([^"]*)"[^>]*data-news-card.*?</article>', html, re.DOTALL
    )
    assert len(cards) == 80
    assert "news-card-compact" not in cards[0]
    assert all("news-card-compact" not in classes for classes in cards[:5])
    assert "news-card-compact" in cards[5]
    assert '>Todos</span><span class="text-xs text-slate-400">80<' in html
    assert '>ANVISA</span><span class="text-xs text-slate-400">52<' in html


def test_index_card_uses_informativo_contract_and_timestamp():
    html = _index_html()
    card = re.search(
        rf'<article\b[^>]*data-updated="{re.escape(TIMESTAMP)}"[^>]*>.*?</article>',
        html,
        re.DOTALL,
    )
    assert card is not None
    assert "Informativo" in card.group(0)
    assert "Ler notícia" in card.group(0)
    assert "news-orange-badge" in card.group(0)


def test_sitemap_contains_new_url_with_editorial_lastmod():
    namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    root = ET.parse(SITEMAP_PATH).getroot()
    matches = [
        item
        for item in root.findall("s:url", namespace)
        if item.findtext("s:loc", namespaces=namespace) == PUBLIC_URL
    ]
    assert len(matches) == 1
    assert matches[0].findtext("s:lastmod", namespaces=namespace) == "2026-09-21"
    assert len(root.findall("s:url", namespace)) == 100
