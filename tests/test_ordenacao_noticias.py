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
COSMETICOS_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-atualiza-listas-substancias-cosmeticos/"
SIFAP_SUSPENSAO_URL = "https://www.regularizeconsultorias.com.br/noticias/farmacia-popular-suspensao-temporaria-recadastramento-sifap/"
CBPF_IN451_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-atualiza-fluxo-cbpf-in451-2026/"
RPBR_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-atualiza-periodicidade-rpbr-farmacovigilancia/"
SIPROQUIM_IN338_URL = "https://www.regularizeconsultorias.com.br/noticias/produtos-quimicos-controlados-siproquim2-assinador-pf/"
PRODUTOS_IRREGULARES_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-suspende-medicamento-proibe-produtos-irregulares/"
FABRICANTES_INTERNACIONAIS_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-cadastro-eletronico-fabricantes-internacionais-dispositivos-medicos/"
SUPERVISAO_CONTEUDO_URL = "https://www.regularizeconsultorias.com.br/noticias/farmaceutico-supervisiona-conteudos-farmacia-redes-sociais-sites/"
RETATRUTIDA_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-retatrutida-sem-registro-produtos-irregulares/"
HEMOTERAPIA_URL = "https://www.regularizeconsultorias.com.br/noticias/ministerio-saude-atualiza-procedimentos-hemoterapicos-transicao-2026/"
EDITAL_5_2026_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-edital-5-2026-dispositivos-medicos-inovadores/"
REVISAO_PROPAGANDA_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-revisao-propaganda-medicamentos-alimentos/"
CANNABIS_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-novas-regras-cannabis-autorizacao-especial/"
DCB_IN462_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-atualiza-lista-denominacoes-comuns-brasileiras-in-462-2026/"
DISPOSITIVOS_IRREGULARES_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-medidas-dispositivos-medicos-irregulares-fiscalizacao/"
PARAMOL_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-suspende-recolhe-lote-114053-paramol-750-mg/"
SEMAGLUTIDA_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-registra-cinco-medicamentos-semaglutida/"
CREDENCIAMENTO_URL = "https://www.regularizeconsultorias.com.br/noticias/credenciamento-farmacia-popular-municipios-com-vagas/"
ALTERACAO_CADASTRAL_URL = "https://www.regularizeconsultorias.com.br/noticias/alteracao-cadastral-farmacia-popular-regularizacao/"
PORTARIA_URL = "https://www.regularizeconsultorias.com.br/noticias/farmacia-popular-portaria-12091-2026-novas-regras/"
PORTARIA_UPDATED = "2026-08-20T18:22:59-03:00"
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

    portaria_card = next(
        (card for card in _news_cards(html) if _card_url(card) == PORTARIA_URL),
        None,
    )
    assert portaria_card is not None
    assert f'data-updated="{PORTARIA_UPDATED}"' in portaria_card
    assert f'<time datetime="{PORTARIA_UPDATED}"' in portaria_card

def test_news_index_itemlist_ordering():
    html = NEWS_INDEX_PATH.read_text(encoding="utf-8")
    items = _itemlist(html)

    assert items, "ItemList is empty"
    urls = [item.get("url") for item in items]

    assert urls[0] == PORTARIA_URL
    assert urls[1] == CANNABIS_URL
    assert urls[2] == RPBR_URL
    assert urls[3] == SIPROQUIM_IN338_URL
    assert urls[4] == PRODUTOS_IRREGULARES_URL
    assert urls[5] == CBPF_IN451_URL
    assert urls[6] == SIFAP_SUSPENSAO_URL
    assert urls[7] == COSMETICOS_URL
    assert urls[8] == "https://www.regularizeconsultorias.com.br/noticias/anvisa-cadastro-eletronico-fabricantes-internacionais-cosmeticos-saneantes/"
    assert urls[9] == FABRICANTES_INTERNACIONAIS_URL
    assert urls[10] == GLP1_URL
    assert urls[11] == "https://www.regularizeconsultorias.com.br/noticias/anvisa-formulario-cbpf-terapias-avancadas/"
    assert urls[12] == "https://www.regularizeconsultorias.com.br/noticias/cnes-competencia-08-2026-prazo-transmissao/"
    assert urls[13] == MONITORAMENTO_URL, "Monitoramento should follow CNES competencia 08"
    assert urls[14] == CREDENCIAMENTO_URL, "Credenciamento should be at position 15 in JSON-LD"
    edital_position = urls.index(EDITAL_5_2026_URL)
    assert edital_position == 19
    assert urls[edital_position - 1] == "https://www.regularizeconsultorias.com.br/noticias/anvisa-amplia-painel-medicamentos-pendentes-registro/"
    assert urls[edital_position + 1] == REVISAO_PROPAGANDA_URL
    revisao_position = urls.index(REVISAO_PROPAGANDA_URL)
    assert revisao_position == 20
    assert urls[revisao_position + 1] == DISPOSITIVOS_IRREGULARES_URL
    dispositivos_position = urls.index(DISPOSITIVOS_IRREGULARES_URL)
    assert dispositivos_position == 21
    assert urls[dispositivos_position - 1] == REVISAO_PROPAGANDA_URL
    assert urls[dispositivos_position + 1] == DCB_IN462_URL
    dcb_position = urls.index(DCB_IN462_URL)
    assert dcb_position == 22
    assert urls[dcb_position - 1] == DISPOSITIVOS_IRREGULARES_URL
    assert urls[dcb_position + 1] == PARAMOL_URL
    paramol_position = urls.index(PARAMOL_URL)
    assert paramol_position == 23
    assert urls[paramol_position - 1] == DCB_IN462_URL
    assert urls[paramol_position + 1] == SEMAGLUTIDA_URL
    supervisao_position = urls.index(SUPERVISAO_CONTEUDO_URL)
    assert urls[supervisao_position - 1] == RETATRUTIDA_URL
    assert urls[supervisao_position + 1] == HEMOTERAPIA_URL
    assert PORTARIA_URL in urls, "Portaria is missing from JSON-LD"
    assert urls.index(PORTARIA_URL) == 0


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
