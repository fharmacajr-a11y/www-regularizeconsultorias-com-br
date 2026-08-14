import re
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEWS_INDEX_PATH = ROOT / "noticias" / "index.html"
CREDENCIAMENTO_PATH = ROOT / "noticias" / "credenciamento-farmacia-popular-municipios-com-vagas" / "index.html"
MONITORAMENTO_PATH = ROOT / "noticias" / "farmacia-popular-inconsistencias-prescricoes-monitoramento" / "index.html"
GLP1_PATH = ROOT / "noticias" / "canetas-emagrecedoras-glp1-anvisa-fiscalizacao-manipulacao" / "index.html"
MONITORAMENTO_URL = "https://www.regularizeconsultorias.com.br/noticias/farmacia-popular-inconsistencias-prescricoes-monitoramento/"
GLP1_URL = "https://www.regularizeconsultorias.com.br/noticias/canetas-emagrecedoras-glp1-anvisa-fiscalizacao-manipulacao/"
SUPERVISAO_CONTEUDO_URL = "https://www.regularizeconsultorias.com.br/noticias/farmaceutico-supervisiona-conteudos-farmacia-redes-sociais-sites/"
RETATRUTIDA_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-retatrutida-sem-registro-produtos-irregulares/"
HEMOTERAPIA_URL = "https://www.regularizeconsultorias.com.br/noticias/ministerio-saude-atualiza-procedimentos-hemoterapicos-transicao-2026/"
DISPOSITIVOS_IRREGULARES_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-medidas-dispositivos-medicos-irregulares-fiscalizacao/"
SEMAGLUTIDA_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-registra-cinco-medicamentos-semaglutida/"
CREDENCIAMENTO_URL = "https://www.regularizeconsultorias.com.br/noticias/credenciamento-farmacia-popular-municipios-com-vagas/"
ALTERACAO_CADASTRAL_URL = "https://www.regularizeconsultorias.com.br/noticias/alteracao-cadastral-farmacia-popular-regularizacao/"
PORTARIA_URL = "https://www.regularizeconsultorias.com.br/noticias/farmacia-popular-portaria-12091-2026-novas-regras/"
MONITORAMENTO_UPDATED = "2026-08-14T12:46:22-03:00"


def _news_cards(html):
    return re.findall(r'(<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>)', html, re.DOTALL)


def _card_url(card):
    match = re.search(r'<a\b[^>]*href="(/noticias/[^"]+/)"', card)
    assert match is not None, "News card URL not found"
    return f"https://www.regularizeconsultorias.com.br{match.group(1)}"


def _card_timestamp(card):
    updated_match = re.search(r'\bdata-updated="([^"]+)"', card)
    if updated_match:
        return datetime.fromisoformat(updated_match.group(1)).timestamp()

    published_match = re.search(r'<time\b[^>]*datetime="([^"]+)"', card)
    assert published_match is not None, "News card timestamp not found"
    return datetime.fromisoformat(published_match.group(1)).timestamp()


def _itemlist(html):
    json_pattern = re.compile(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', re.DOTALL)
    for match in json_pattern.finditer(html):
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue

        if data.get("@type") == "CollectionPage":
            main_entity = data.get("mainEntity", {})
            if main_entity.get("@type") == "ItemList":
                return main_entity.get("itemListElement", [])

    return []

def test_news_index_sorting_rule_and_attributes():
    html = NEWS_INDEX_PATH.read_text(encoding="utf-8")

    monitoramento_card = next(
        (card for card in _news_cards(html) if _card_url(card) == MONITORAMENTO_URL),
        None,
    )
    assert monitoramento_card is not None, "Monitoramento article not found in HTML"
    assert f'data-updated="{MONITORAMENTO_UPDATED}"' in monitoramento_card

    monitoramento_page = MONITORAMENTO_PATH.read_text(encoding="utf-8")
    assert '"datePublished": "2026-06-22T09:40:00-03:00"' in monitoramento_page
    assert f'"dateModified": "{MONITORAMENTO_UPDATED}"' in monitoramento_page

    glp1_card = next(
        (card for card in _news_cards(html) if _card_url(card) == GLP1_URL),
        None,
    )
    assert glp1_card is not None, "GLP-1 article not found in HTML"
    assert 'data-updated="2026-08-14T16:13:12-03:00"' in glp1_card
    assert "Atualização" in glp1_card
    assert "Ler atualização" in glp1_card

    glp1_page = GLP1_PATH.read_text(encoding="utf-8")
    assert '"datePublished": "2026-05-31T19:00:00-03:00"' in glp1_page
    assert '"dateModified": "2026-08-14T16:13:12-03:00"' in glp1_page

    credenciamento_match = re.search(r'(<article[^>]*?data-title="Credenciamento no Farmácia Popular exige atenção à lista oficial de municípios com vagas"[^>]*?>.*?)</article>', html, re.DOTALL)
    assert credenciamento_match is not None, "Credenciamento article not found in HTML"
    credenciamento_html = credenciamento_match.group(1)
    assert 'data-updated="2026-08-14T10:31:09-03:00"' in credenciamento_html, "Credenciamento data-updated attribute missing or incorrect"

    credenciamento_page = CREDENCIAMENTO_PATH.read_text(encoding="utf-8")
    assert '"datePublished": "2026-05-22T23:30:00-03:00"' in credenciamento_page, "Credenciamento original datePublished was falsified"
    assert '"dateModified": "2026-08-14T10:31:09-03:00"' in credenciamento_page, "Credenciamento dateModified missing or incorrect"

    article_match = re.search(r'(<article[^>]*?data-title="Alteração cadastral no Farmácia Popular exige atenção para evitar pendências no programa"[^>]*?>.*?)</article>', html, re.DOTALL)
    assert article_match is not None, "Article not found in HTML"
    article_html = article_match.group(1)

    assert 'data-updated="2026-08-14T09:04:41-03:00"' in article_html, "data-updated attribute missing or incorrect"
    assert '<time datetime="2026-05-22T23:30:00-03:00"' in article_html, "Original datePublished was falsified in the <time> tag"

def test_news_index_itemlist_ordering():
    html = NEWS_INDEX_PATH.read_text(encoding="utf-8")
    items = _itemlist(html)

    assert items, "ItemList is empty"
    urls = [item.get("url") for item in items]

    assert urls[0] == GLP1_URL
    assert urls[1] == "https://www.regularizeconsultorias.com.br/noticias/cnes-competencia-08-2026-prazo-transmissao/"
    assert urls[2] == MONITORAMENTO_URL, "Monitoramento should be at position 3 after its material update"
    assert urls[3] == CREDENCIAMENTO_URL, "Credenciamento should be at position 4 in JSON-LD"
    dispositivos_position = urls.index(DISPOSITIVOS_IRREGULARES_URL)
    assert dispositivos_position == 10
    assert urls[dispositivos_position - 1] == "https://www.regularizeconsultorias.com.br/noticias/anvisa-novas-regras-cannabis-autorizacao-especial/"
    assert urls[dispositivos_position + 1] == SEMAGLUTIDA_URL
    supervisao_position = urls.index(SUPERVISAO_CONTEUDO_URL)
    assert urls[supervisao_position - 1] == RETATRUTIDA_URL
    assert urls[supervisao_position + 1] == HEMOTERAPIA_URL
    assert PORTARIA_URL in urls, "Portaria is missing from JSON-LD"
    assert urls.index(PORTARIA_URL) > urls.index(ALTERACAO_CADASTRAL_URL), "Portaria should appear after Alteracao Cadastral"


def test_all_news_orders_match_effective_timestamp_sorting():
    html = NEWS_INDEX_PATH.read_text(encoding="utf-8")
    cards = _news_cards(html)
    items = _itemlist(html)

    assert cards
    assert len(items) == len(cards)

    physical_urls = [_card_url(card) for card in cards]
    itemlist_urls = [item["url"] for item in items]
    calculated_urls = [
        _card_url(card)
        for card in sorted(cards, key=_card_timestamp, reverse=True)
    ]

    assert len(set(physical_urls)) == len(physical_urls)
    assert [item["position"] for item in items] == list(range(1, len(items) + 1))
    assert physical_urls == calculated_urls
    assert itemlist_urls == physical_urls

    assert all("news-card-compact" not in card.split(">", 1)[0] for card in cards[:5])
    assert all("news-card-compact" in card.split(">", 1)[0] for card in cards[5:])
