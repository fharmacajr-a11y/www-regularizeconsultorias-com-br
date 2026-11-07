import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
ARTICLE = ROOT / "noticias" / "anvisa-atualiza-listas-substancias-cosmeticos" / "index.html"
INDEX = ROOT / "noticias" / "index.html"
SITEMAP = ROOT / "sitemap.xml"
URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-atualiza-listas-substancias-cosmeticos/"
UPDATED = "2026-10-02T21:50:00-03:00"
PUBLISHED = "2026-07-05T17:00:00-03:00"


def _cards(html):
    return re.findall(
        r"<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>",
        html,
        re.DOTALL,
    )


def test_cp_1399_is_recorded_as_closed_on_the_existing_article():
    html = ARTICLE.read_text(encoding="utf-8")

    for banned in ("permanece aberta", "prazo permanece vigente", "recebe contribuições"):
        assert banned not in html
    assert "08/07/2026 a 08/09/2026" in html
    assert "está encerrada" in html
    assert "não alterou a lista vigente" in html
    assert "não informa prorrogação" in html
    assert "Eventual norma posterior deve ser acompanhada separadamente." in html
    assert f'"datePublished": "{PUBLISHED}"' in html
    assert f'"dateModified": "{UPDATED}"' in html
    assert f'content="{UPDATED}" property="article:modified_time"' in html
    assert f'<time datetime="{PUBLISHED}">05/07/2026</time> às 17h00' in html
    assert f'<time datetime="{UPDATED}">02/10/2026</time> às 21h50' in html


def test_listing_places_the_updated_cosmetics_card_eighth():
    html = INDEX.read_text(encoding="utf-8")
    cards = _cards(html)
    # Lote de 09/10/2026: as 13 matérias atualizadas no lote sobem pelo carimbo; as demais descem.
    # 16/10/2026, 20h06: o card do CNES 10/2026 entra na 1ª posição da listagem; os demais descem uma.
    # 17/10/2026, 09h50: o card do esclarecimento do Farmácia Popular entra na 1ª posição da listagem; os demais descem uma.
    # 20/10/2026, 10h12: os cards do consolidado de produtos irregulares e do SISPA sobem para a 1ª e a 2ª posições; os que ficavam entre eles descem uma.
    # 01/11/2026 (reenvio ao AdSense): os 11 cards de 01/11 (5 matérias novas e 6 ampliadas) vão ao topo e saem os das
    # 6 páginas reunidas (total 85 + 5 - 6 = 84). Índice novo = anterior + 11 - reunidas que ficavam à frente -
    # ampliadas que já ficavam à frente: 36 + 11 - 5 - 0 = 42.
    # 07/11/2026: a notícia da auditoria do Farmácia Popular abre a listagem; este card desce uma posição.
    card = cards[43]

    # 02/11/2026 (decisão do Jr): a notícia do Paramol (lote 114053) ganhou noindex e saiu da listagem e do sitemap.
    # 07/11/2026: a notícia da auditoria do Farmácia Popular entra no topo da listagem, no ItemList e no sitemap.
    assert len(cards) == 84
    assert "/noticias/anvisa-atualiza-listas-substancias-cosmeticos/" in card
    assert f'data-updated="{UPDATED}"' in card
    assert "está encerrada" in card
    assert "recebe contribuições" not in card
    assert "permanece aberta" not in card
    # 02/11/2026 (decisão do Jr): a notícia do Paramol (lote 114053) ganhou noindex e saiu da listagem e do sitemap.
    # 07/11/2026: a notícia da auditoria do Farmácia Popular entra no topo da listagem, no ItemList e no sitemap.
    assert '>Todos</span><span class="text-xs text-slate-400">84<' in html
    # 01/11/2026: +2 guias da ANVISA (cadastros da drogaria; recolhimentos, suspensões e alertas).
    # 02/11/2026 (decisão do Jr): a notícia do Paramol (lote 114053) ganhou noindex e saiu da listagem e do sitemap.
    assert '>ANVISA</span><span class="text-xs text-slate-400">55<' in html
    # 07/11/2026: a notícia da auditoria do Farmácia Popular abre a listagem; este card desce uma posição.
    assert (
        '"position":44,"url":"https://www.regularizeconsultorias.com.br'
        '/noticias/anvisa-atualiza-listas-substancias-cosmeticos/"'
    ) in html
    sitemap = SITEMAP.read_text(encoding="utf-8")
    assert f"<loc>{URL}</loc>\n    <lastmod>2026-10-02</lastmod>" in sitemap
