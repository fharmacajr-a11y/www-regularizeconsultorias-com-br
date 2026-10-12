import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
NEWS_INDEX = ROOT / "noticias" / "index.html"
SITEMAP = ROOT / "sitemap.xml"

AFE = ROOT / "noticias" / "anvisa-atualiza-acesso-sncr-afe-farmacias-privadas" / "index.html"
CNES = ROOT / "noticias" / "nova-regra-anvisa-cnes-receitas-farmacias" / "index.html"
GLP1 = ROOT / "noticias" / "canetas-emagrecedoras-glp1-anvisa-fiscalizacao-manipulacao" / "index.html"

AFE_PUBLISHED = "2026-05-09T09:00:00-03:00"
AFE_UPDATED = "2026-10-07T09:08:00-03:00"
CNES_PUBLISHED = "2026-04-29T09:00:00-03:00"
CNES_UPDATED = "2026-10-06T22:09:00-03:00"
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
        # Fase 1M v2: notícias revistas em 08/10 sobem para o topo.
        # 11/10/2026, 06h07: a atualização do CNES 09/2026 (prazo encerrado, item 48) leva aquele card ao 1º lugar; os cards das posições 1 a 31 descem uma.
        ("anvisa-atualiza-acesso-sncr-afe-farmacias-privadas", AFE_UPDATED, "07/10/2026 • 09h08", 26, True, "2026-10-07"),
        ("nova-regra-anvisa-cnes-receitas-farmacias", CNES_UPDATED, "06/10/2026 • 22h09", 28, True, "2026-10-06"),
        ("canetas-emagrecedoras-glp1-anvisa-fiscalizacao-manipulacao", GLP1_UPDATED, "30/09/2026 • 09h30", 33, True, "2026-09-30"),
    )
    for slug, updated, label, position, compact, lastmod in expected:
        card = _card(index, slug)
        assert cards.index(card) == position
        assert f'data-updated="{updated}"' in card
        assert label in card
        opening = card.split(">", 1)[0]
        assert ("news-card-compact" in opening) is compact
        assert f"<loc>https://www.regularizeconsultorias.com.br/noticias/{slug}/</loc>\n    <lastmod>{lastmod}</lastmod>" in sitemap

    assert "ausência de acesso direto" not in index
    assert '>Todos</span><span class="text-xs text-slate-400">83<' in index
    assert '>ANVISA</span><span class="text-xs text-slate-400">54<' in index
    assert '>CNES</span><span class="text-xs text-slate-400">5<' in index
    assert '>SNCR</span><span class="text-xs text-slate-400">2<' in index


def _plain_body(path):
    return " ".join(re.sub(r"<[^>]+>", " ", _body(path)).split())


def test_historical_pages_no_longer_tie_cnes_to_farmacia_popular_participation():
    afe = _plain_body(AFE)
    cnes = _plain_body(CNES)
    for text in (afe, cnes):
        folded = text.casefold()
        # Correção atual: CNES fora do rol mínimo da Portaria 12.091 e da convocação, sem dispensa geral.
        assert "não incluem o cnes no rol mínimo de documentos para participar do programa" in folded
        assert ("corrigid" in folded or "correção" in folded) and "06/10/2026" in text
        for wrong in ("como serviços clínicos, vacinação e o programa farmácia popular",
                      "o cnes também não era tratado como dispensável para farmácias vinculadas",
                      "cnes é exigido para participar", "exige o cnes", "farmácia popular exige cnes",
                      "dispensada do cnes por participar", "participação no programa dispensa o cnes",
                      "o sifap não cruza", "nunca cruza"):
            assert wrong not in folded, wrong
    # Sem dispensa geral do CNES.
    assert "isso não significa que a farmácia participante esteja dispensada do cnes" in afe.casefold()
    assert "não dispensa a farmácia participante das obrigações próprias do cnes" in cnes.casefold()
    # A leitura de maio é atribuída à versão anterior da própria página, não à comunicação do CFF.
    assert "a versão de maio desta página lembrava" in afe
    assert "Na versão de maio, esta página recomendava, por prudência" in afe
    assert "versões anteriores desta página incluíam o Programa Farmácia Popular" in cnes
    assert "o texto da época já lembrava" not in afe


def test_cnes_record_uses_the_atualizacao_type_after_the_correction():
    html = CNES.read_text(encoding="utf-8")
    hero = re.search(r"<header\b[^>]*article-hero[^>]*>.*?</header>", html, re.DOTALL).group(0)
    assert "article-hero-atualizacao" in hero and "article-hero-informativo" not in hero
    assert '<span class="article-badge-atualizacao inline-flex items-center rounded-full px-2.5 py-1 whitespace-nowrap">Atualização</span>' in hero
    assert "article-badge-informativo" not in html and ">Informativo<" not in hero
    assert ">CNES</span>" in hero
    assert "CNES no SNCR: orientação inicial foi atualizada para farmácias privadas" in hero
    # O aviso institucional e a natureza informativa do conteúdo continuam.
    assert "Conteúdo informativo produzido pela Regularize Consultoria." in html

    card = _card(NEWS_INDEX.read_text(encoding="utf-8"), "nova-regra-anvisa-cnes-receitas-farmacias")
    opening = card.split(">", 1)[0]
    assert "news-amber-card" in opening and "orange" not in card
    assert 'data-category="cnes"' in opening
    assert 'data-title="CNES no SNCR: orientação inicial foi atualizada para farmácias privadas"' in opening
    assert ">Atualização</span>" in card and ">Informativo<" not in card
    assert "news-amber-badge" in card and "news-amber-button" in card
    assert "Ler atualização" in card and "Ler notícia" not in card
