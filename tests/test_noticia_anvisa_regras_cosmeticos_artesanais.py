import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTICLE = ROOT / "noticias" / "anvisa-regras-cosmeticos-artesanais" / "index.html"
NEWS_INDEX = ROOT / "noticias" / "index.html"
SITEMAP = ROOT / "sitemap.xml"
SLUG = "anvisa-regras-cosmeticos-artesanais"
URL = f"https://www.regularizeconsultorias.com.br/noticias/{SLUG}/"
ROUTE = f"/noticias/{SLUG}/"
STAMP = "2026-10-01T16:48:00-03:00"
TITLE = "Anvisa aprova novas regras para cosméticos artesanais"

FORBIDDEN = (
    "todo cosmético artesanal",
    "todos os cosméticos artesanais",
    "qualquer cosmético pode",
    "qualquer produto artesanal está dispensado",
    "está automaticamente dispensado",
    "dispensa automática",
    "precisa de registro na anvisa",
    "exigem registro na anvisa",
    "exige registro na anvisa",
    "processo de registro do cosmético artesanal",
    "registro na anvisa de cosmético artesanal",
    "registro de cosmético artesanal",
    "está em vigor",
    "estão em vigor",
    "entram em vigor",
    "já vigente",
    "passam a valer",
    "passa a valer",
    "passo a passo",
    "clique aqui",
    "código de assunto",
    "fórmula",
    "como fabricar",
    "checklist",
)


def _html():
    return ARTICLE.read_text(encoding="utf-8")


def _main(html):
    match = re.search(r"<main>(.*)</main>", html, re.DOTALL)
    assert match, "main ausente"
    return match.group(1)


def _jsonld(html):
    return [
        json.loads(block)
        for block in re.findall(
            r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
            html,
            re.DOTALL,
        )
    ]


def test_article_exists_with_canonical_title_and_date():
    html = _html()
    assert ARTICLE.is_file()
    assert html.count("<h1") == 1
    assert f"<title>{TITLE} | Regularize Consultoria</title>" in html
    assert f'rel="canonical" href="{URL}"' in html
    assert f'<h1 class="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight leading-tight text-white mb-5">{TITLE}</h1>' in html
    assert "noindex" not in html.casefold()
    assert "Atualizado em" not in html
    assert f'<time datetime="{STAMP}">01/10/2026</time> às 16h48' in html
    assert "Júnior Costa" in html
    assert "Conteúdo informativo produzido pela Regularize Consultoria." in html
    assert ">Categoria:</span>" in html
    assert "Órgão regulador:" in html
    assert html.count("category-chip--anvisa") >= 2
    assert "article-badge-informativo" in html
    assert ">Informativo</span>" in html


def test_article_metadata_uses_publication_stamp_and_fallback_image():
    html = _html()
    assert html.count(f'content="{STAMP}"') == 2
    assert 'property="article:section" content="ANVISA"' in html
    assert "assets/img/og/noticias.jpg" in html
    assert 'property="og:image:type" content="image/jpeg"' in html
    assert 'property="og:image:width" content="1200"' in html
    assert 'property="og:image:height" content="630"' in html
    alt = re.search(r'property="og:image:alt" content="([^"]*)"', html)
    assert alt
    assert "cosméticos artesanais" in alt.group(1).casefold()
    assert "OG TEMPORÁRIA" not in alt.group(1)
    assert "substituir futuramente" not in alt.group(1).casefold()
    assert "ca-pub-2993532924249779" in html
    news = next(block for block in _jsonld(html) if block.get("@type") == "NewsArticle")
    assert news["headline"] == TITLE
    assert news["datePublished"] == STAMP
    assert news["dateModified"] == STAMP
    assert news["url"] == URL
    assert news["articleSection"] == "ANVISA"
    assert news["author"]["name"] == "Júnior Costa"
    assert news["publisher"]["name"] == "Regularize Consultoria"
    assert news["image"].endswith("/assets/img/og/noticias.jpg")
    breadcrumb = next(block for block in _jsonld(html) if block.get("@type") == "BreadcrumbList")
    items = breadcrumb["itemListElement"]
    assert [item["position"] for item in items] == [1, 2, 3]
    assert items[2]["item"] == URL


def test_article_states_approval_without_inventing_numbers_or_vigencia():
    main = _main(_html())
    folded = main.casefold()
    for term in (
        "30 de setembro de 2026",
        "18ª Reunião Ordinária Pública",
        "Marcelo Moreira",
        "Lei nº 15.154",
        "Lei nº 6.360/1976",
        "não precisarão de regularização na Anvisa",
        "corretamente classificados",
        "não significa ausência de requisitos sanitários",
        "produtos de perfumaria com base alcoólica",
        "odorizantes de ambiente",
        "produtos sólidos para banho e/ou imersão",
        "sabonetes sólidos para o corpo",
        "xampus e condicionadores sólidos",
        "óleos e manteigas corporais",
        "desodorante axilar em barra",
        "até 12 meses",
        "sem apelos terapêuticos",
        "Vigilância Sanitária local",
        "ainda não foram confirmados",
        "não se confunde com a entrada em vigor",
        "entra em vigor após decorridos 60 dias de sua publicação oficial",
        "a publicação formal, a numeração e a vigência dos atos ainda não estavam confirmadas",
        "regime ordinário",
        "não detalha, por si, as regras simplificadas",
    ):
        assert term in main, term
    assert folded.count("60 dias") == 1
    assert "ainda não é a norma aplicável" not in folded
    assert not re.search(r"\b(?:rdc|in)\s*(?:n[ºo°.])?\s*\d", folded)
    assert not re.search(r"\bafe\b", folded)
    for banned in FORBIDDEN:
        assert banned not in folded, banned


def test_article_keeps_sources_cta_and_natural_internal_links():
    html = _html()
    main = _main(html)
    assert "https://www.gov.br/anvisa/pt-br/assuntos/noticias-anvisa/2026/anvisa-aprova-regularizacao-de-cosmeticos-artesanais" in main
    assert "https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2025/lei/L15154.htm" in main
    assert "https://www.gov.br/anvisa/pt-br/assuntos/regulamentacao/agenda-regulatoria/minutas-previas" in main
    assert "não são o ato publicado" in main
    assert main.count('href="/noticias/anvisa-capacitacao-bpf-cosmeticos-saneantes/"') == 1
    assert 'href="/noticias/anvisa-atualiza-listas-substancias-cosmeticos/"' in html
    assert "manual-cosmeticos-saneantes" not in html
    assert "não é o caminho para obter a dispensa" not in html
    assert "Solicitar análise técnica" in html
    assert 'href="/contato/"' in html
    assert 'href="/servicos/"' in html
    assert "sem prometer dispensa" not in html.casefold()
    assert "avaliar o enquadramento do produto e da atividade" in html
    assert "Ol%C3%A1!%20Vi%20a%20not%C3%ADcia%20da%20Regularize%20sobre%20as%20regras%20para%20cosm%C3%A9ticos%20artesanais%20e%20gostaria%20de%20avaliar%20o%20enquadramento%20da%20minha%20atividade." in html
    assert "Aviso institucional:" in html


def test_listing_places_the_card_first_and_updates_counts():
    html = NEWS_INDEX.read_text(encoding="utf-8")
    cards = re.findall(r"(<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>)", html, re.DOTALL)
    assert len(cards) == 82
    card = cards[0]
    opening = card.split(">", 1)[0]
    assert f'href="{ROUTE}"' in card
    assert html.count(f'href="{ROUTE}"') == 1
    assert "news-card-compact" not in opening
    assert "news-orange-card" in opening
    assert 'data-category="anvisa"' in opening
    assert f'data-updated="{STAMP}"' in opening
    assert f'data-title="{TITLE}"' in opening
    assert "Informativo" in card
    assert "Ler notícia" in card
    assert "Atualização" not in card
    assert f'<time datetime="{STAMP}" class="leading-none">01/10/2026 • 16h48</time>' in card
    assert "82 notícias encontradas" in html
    assert '>Todos</span><span class="text-xs text-slate-400">82<' in html
    assert '>ANVISA</span><span class="text-xs text-slate-400">54<' in html
    assert all("news-card-compact" not in item.split(">", 1)[0] for item in cards[:5])
    assert "news-card-compact" in cards[5].split(">", 1)[0]
    collection = next(block for block in _jsonld(html) if block.get("@type") == "CollectionPage")
    items = collection["mainEntity"]["itemListElement"]
    assert len(items) == 82
    assert items[0]["position"] == 1
    assert items[0]["url"] == URL
    assert [item["position"] for item in items] == list(range(1, 83))


def test_sitemap_adds_only_the_new_url_and_the_listing_lastmod():
    sitemap = SITEMAP.read_text(encoding="utf-8")
    assert sitemap.count(f"<loc>{URL}</loc>") == 1
    assert f"<loc>{URL}</loc>\n    <lastmod>2026-10-01</lastmod>" in sitemap
    assert (
        "<loc>https://www.regularizeconsultorias.com.br/noticias/</loc>\n"
        "    <lastmod>2026-10-01</lastmod>"
    ) in sitemap
    assert (
        "<loc>https://www.regularizeconsultorias.com.br/noticias/rdc-1000-2025-anvisa-prorroga-prazo-sncr/</loc>\n"
        "    <lastmod>2026-09-30</lastmod>"
    ) in sitemap
    import xml.etree.ElementTree as ET

    ET.fromstring(sitemap)
