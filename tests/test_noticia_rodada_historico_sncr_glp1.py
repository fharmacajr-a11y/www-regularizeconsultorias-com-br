import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEWS_INDEX = ROOT / "noticias" / "index.html"
SITEMAP = ROOT / "sitemap.xml"

AFE = ROOT / "noticias" / "anvisa-atualiza-acesso-sncr-afe-farmacias-privadas" / "index.html"
CNES = ROOT / "noticias" / "nova-regra-anvisa-cnes-receitas-farmacias" / "index.html"
GLP1 = ROOT / "noticias" / "canetas-emagrecedoras-glp1-anvisa-fiscalizacao-manipulacao" / "index.html"

AFE_PUBLISHED = "2026-05-09T09:00:00-03:00"
AFE_UPDATED = "2026-09-30T09:32:00-03:00"
CNES_PUBLISHED = "2026-04-29T09:00:00-03:00"
CNES_UPDATED = "2026-09-30T09:31:00-03:00"
GLP1_PUBLISHED = "2026-05-31T19:00:00-03:00"
GLP1_UPDATED = "2026-09-30T09:30:00-03:00"

FORBIDDEN = (
    "ausência de acesso direto",
    "orientação mais recente",
    "atualização mais recente",
    "comunicação mais recente",
    "SNCR-Farmácia",
    "passo a passo",
    "gov.br",
)


def _body(path):
    html = path.read_text(encoding="utf-8")
    return re.search(r'<section class="article-body">(.*?)</section>', html, re.DOTALL).group(1)


def _card(html, slug):
    cards = re.findall(r"(<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>)", html, re.DOTALL)
    return next(card for card in cards if f"/noticias/{slug}/" in card)


def test_historical_sncr_pages_keep_may_as_period_and_add_september():
    for path, published, updated in (
        (AFE, AFE_PUBLISHED, AFE_UPDATED),
        (CNES, CNES_PUBLISHED, CNES_UPDATED),
    ):
        html = path.read_text(encoding="utf-8")
        body = _body(path)
        assert f'"datePublished": "{published}"' in html
        assert f'"dateModified": "{updated}"' in html
        assert f'article:modified_time" content="{updated}"' in html or f'content="{updated}" property="article:modified_time"' in html
        assert "href=" not in body
        folded = body.casefold()
        for phrase in FORBIDDEN:
            assert phrase.casefold() not in folded, (path.name, phrase)
        assert "setembro de 2026" in folded
        assert "29 de setembro" in folded
        assert "dispensam o cnes" in folded or "não dispensa o cnes" in folded
        assert "ministério da saúde" in folded
        assert "funcionamento integral" in folded
        assert "regularize consultoria executa" in folded


def test_glp1_adds_september_alert_without_turning_old_totals_current():
    html = GLP1.read_text(encoding="utf-8")
    body = _body(GLP1)
    folded = body.casefold()

    assert f'"datePublished": "{GLP1_PUBLISHED}"' in html
    assert f'"dateModified": "{GLP1_UPDATED}"' in html
    assert f'content="{GLP1_UPDATED}" property="article:modified_time"' in html
    assert "href=" not in body
    assert "23 de setembro de 2026" in body
    assert "tirzepatida em pó" in folded
    assert "impurezas ou contaminantes" in folded
    assert "infecções graves" in folded
    assert "manipulação submetida aos requisitos sanitários" in folded
    assert "toda tirzepatida manipulada tenha sido proibida" in folded
    assert "não orienta preparo, diluição, aplicação ou dose" in folded
    assert "6 de abril de 2026" in body
    assert "balanço divulgado em julho" in folded
    assert "não é o total atual" in folded or "nenhum desses recortes é o total atual" in folded
    for banned in ("como diluir", "como aplicar", "mg/ml", "unidades por"):
        assert banned not in folded


def test_listing_sitemap_and_cards_follow_the_review_timestamps():
    index = NEWS_INDEX.read_text(encoding="utf-8")
    sitemap = SITEMAP.read_text(encoding="utf-8")
    cards = re.findall(r"(<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>)", index, re.DOTALL)

    expected = (
        ("anvisa-atualiza-acesso-sncr-afe-farmacias-privadas", AFE_UPDATED, "30/09/2026 • 09h32", 4, False),
        ("nova-regra-anvisa-cnes-receitas-farmacias", CNES_UPDATED, "30/09/2026 • 09h31", 5, True),
        ("canetas-emagrecedoras-glp1-anvisa-fiscalizacao-manipulacao", GLP1_UPDATED, "30/09/2026 • 09h30", 6, True),
    )
    for slug, updated, label, position, compact in expected:
        card = _card(index, slug)
        assert cards.index(card) == position
        assert f'data-updated="{updated}"' in card
        assert label in card
        opening = card.split(">", 1)[0]
        assert ("news-card-compact" in opening) is compact
        assert f"<loc>https://www.regularizeconsultorias.com.br/noticias/{slug}/</loc>\n    <lastmod>2026-09-30</lastmod>" in sitemap

    assert "ausência de acesso direto" not in index
    assert '>Todos</span><span class="text-xs text-slate-400">83<' in index
    assert '>ANVISA</span><span class="text-xs text-slate-400">54<' in index
    assert '>CNES</span><span class="text-xs text-slate-400">5<' in index
    assert '>SNCR</span><span class="text-xs text-slate-400">2<' in index
