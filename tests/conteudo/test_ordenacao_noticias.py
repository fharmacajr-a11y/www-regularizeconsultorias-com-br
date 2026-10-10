import pytest
import re
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
NEWS_INDEX_PATH = ROOT / "noticias" / "index.html"
CREDENCIAMENTO_PATH = ROOT / "noticias" / "credenciamento-farmacia-popular-municipios-com-vagas" / "index.html"
MONITORAMENTO_PATH = ROOT / "noticias" / "farmacia-popular-inconsistencias-prescricoes-monitoramento" / "index.html"
GLP1_PATH = ROOT / "noticias" / "canetas-emagrecedoras-glp1-anvisa-fiscalizacao-manipulacao" / "index.html"
ALTERACAO_CADASTRAL_PATH = ROOT / "noticias" / "alteracao-cadastral-farmacia-popular-regularizacao" / "index.html"
MONITORAMENTO_URL = "https://www.regularizeconsultorias.com.br/noticias/farmacia-popular-inconsistencias-prescricoes-monitoramento/"
GLP1_URL = "https://www.regularizeconsultorias.com.br/noticias/canetas-emagrecedoras-glp1-anvisa-fiscalizacao-manipulacao/"
COSMETICOS_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-atualiza-listas-substancias-cosmeticos/"
SIFAP_SUSPENSAO_URL = "https://www.regularizeconsultorias.com.br/noticias/farmacia-popular-suspensao-temporaria-recadastramento-sifap/"
CBPF_IN451_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-atualiza-fluxo-cbpf-in451-2026/"
RPBR_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-atualiza-periodicidade-rpbr-farmacovigilancia/"
SIPROQUIM_IN338_URL = "https://www.regularizeconsultorias.com.br/noticias/produtos-quimicos-controlados-siproquim2-assinador-pf/"
PRODUTOS_IRREGULARES_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-suspende-medicamento-proibe-produtos-irregulares/"
PRODUTOS_IRREGULARES_UPDATED = "2026-10-09T20:27:00-03:00"
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
# Nova notícia de saneantes: RDC 1.040 e IN 468/2026.
SANEANTES_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-rdc-1040-in-468-2026-saneantes-regularizacao/"
# Nova notícia da competência 09/2026 do CNES (Informe de 14/09/2026).
CNES_COMPETENCIA_09_2026_URL = "https://www.regularizeconsultorias.com.br/noticias/cnes-competencia-09-2026-prazo-transmissao/"
# Nova notícia do Edital de Chamamento 6/2026 (AFE para preparações estéreis).
EDITAL_6_2026_AFE_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-edital-6-2026-afe-manipulacao-preparacoes-estereis/"
# Notícia CNES/SNCR revisada em 28/09/2026 e reposicionada pelo dateModified.
CNES_SNCR_URL = "https://www.regularizeconsultorias.com.br/noticias/cnes-continua-obrigatorio-sncr-afe-farmacias/"
# Notícia SNCR atualizada com a etapa de 30/09/2026 e reposicionada pelo dateModified.
SNCR_WEBINAR_URL = "https://www.regularizeconsultorias.com.br/noticias/rdc-1000-2025-anvisa-prorroga-prazo-sncr/"
# Nova notícia sobre a proibição da propaganda do Semavy (RE nº 3.750/2026).
SEMAVY_PROPAGANDA_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-proibe-propaganda-semavy-consumidor/"
# Nova notícia sobre a IN Anvisa 470/2026.
IN_470_SUPLEMENTOS_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-in-470-2026-suplementos-ingredientes-limites-alegacoes/"
# Seis notícias Anvisa que receberam conteúdo factual novo e subiram na ordenação.
PASSIVO_DISPOSITIVOS_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-reducao-passivo-peticoes-dispositivos-medicos/"
IFAS_GLP1_PETICOES_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-peticoes-ifas-glp1-importados/"
DUIMP_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-orienta-duimp-importacao-produtos-regulados/"
FITOTERAPICOS_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-novas-normas-regularizacao-fitoterapicos/"
SICERT_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-descontinua-sicert-certificados-dispositivos-medicos/"
ARMAZENS_ALFANDEGADOS_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-boas-praticas-armazens-alfandegados/"
CREDENCIAMENTO_UPDATED = "2026-10-09T20:31:00-03:00"
ALTERACAO_CADASTRAL_URL = "https://www.regularizeconsultorias.com.br/noticias/alteracao-cadastral-farmacia-popular-regularizacao/"
PORTARIA_URL = "https://www.regularizeconsultorias.com.br/noticias/farmacia-popular-portaria-12091-2026-novas-regras/"
PORTARIA_UPDATED = "2026-10-09T20:33:00-03:00"
MONITORAMENTO_UPDATED = "2026-10-09T20:33:00-03:00"


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
    assert 'data-updated="2026-09-30T09:30:00-03:00"' in glp1_card
    assert "Atualização" in glp1_card
    assert "Ler atualização" in glp1_card

    glp1_page = GLP1_PATH.read_text(encoding="utf-8")
    assert '"datePublished": "2026-05-31T19:00:00-03:00"' in glp1_page
    assert '"dateModified": "2026-09-30T09:30:00-03:00"' in glp1_page

    credenciamento_match = re.search(r'(<article[^>]*?data-title="Credenciamento no Farmácia Popular exige atenção à lista oficial de municípios com vagas"[^>]*?>.*?)</article>', html, re.DOTALL)
    assert credenciamento_match is not None, "Credenciamento article not found in HTML"
    credenciamento_html = credenciamento_match.group(1)
    assert f'data-updated="{CREDENCIAMENTO_UPDATED}"' in credenciamento_html, "Credenciamento data-updated attribute missing or incorrect"

    credenciamento_page = CREDENCIAMENTO_PATH.read_text(encoding="utf-8")
    assert '"datePublished": "2026-05-22T23:30:00-03:00"' in credenciamento_page, "Credenciamento original datePublished was falsified"
    assert f'"dateModified": "{CREDENCIAMENTO_UPDATED}"' in credenciamento_page, "Credenciamento dateModified missing or incorrect"

    article_match = re.search(r'(<article[^>]*?data-title="Alteração cadastral no Farmácia Popular exige atenção para evitar pendências no programa"[^>]*?>.*?)</article>', html, re.DOTALL)
    assert article_match is not None, "Article not found in HTML"
    article_html = article_match.group(1)

    assert 'data-updated="2026-08-14T09:04:41-03:00"' in article_html, "data-updated attribute missing or incorrect"
    # O card mostra "Atualizado em 14/08/2026 • 09h04": o <time> do card é essa atualização, a data que ordena a lista
    # (layout comum, revisão v2, 10/10/2026; test_listagem_rotulo_atualizacao.py). A publicação original de 22/05/2026
    # continua protegida na página da matéria, no datePublished e no "Publicado em".
    assert 'Atualizado em <span class="whitespace-nowrap"><time datetime="2026-08-14T09:04:41-03:00" class="leading-none">14/08/2026 • 09h04</time>' in article_html, "The card <time> must carry the update it shows"
    alteracao_page = ALTERACAO_CADASTRAL_PATH.read_text(encoding="utf-8")
    assert '"datePublished": "2026-05-22T23:30:00-03:00"' in alteracao_page, "Original datePublished was falsified in the article page"
    assert '"dateModified": "2026-08-14T09:04:41-03:00"' in alteracao_page, "dateModified missing or incorrect in the article page"
    assert 'Publicado em:</span> <time datetime="2026-05-22T23:30:00-03:00">22/05/2026</time> às 23h30' in alteracao_page, "Original publication date was falsified in the article page"

    portaria_card = next(
        (card for card in _news_cards(html) if _card_url(card) == PORTARIA_URL),
        None,
    )
    assert portaria_card is not None
    assert f'data-updated="{PORTARIA_UPDATED}"' in portaria_card
    assert f'<time datetime="{PORTARIA_UPDATED}"' in portaria_card

    produtos_irregulares_card = next(
        (card for card in _news_cards(html) if _card_url(card) == PRODUTOS_IRREGULARES_URL),
        None,
    )
    assert produtos_irregulares_card is not None
    assert f'data-updated="{PRODUTOS_IRREGULARES_UPDATED}"' in produtos_irregulares_card

def test_news_index_itemlist_ordering():
    html = NEWS_INDEX_PATH.read_text(encoding="utf-8")
    items = _itemlist(html)

    assert items, "ItemList is empty"
    urls = [item.get("url") for item in items]
    # Lote de conteúdo e dados de 09/10/2026: as 13 matérias atualizadas no lote ocupam o topo, pelo carimbo.
    lote = [
        "policia-federal-classificacao-produtos-simples-compostos-siproquim",
        "anvisa-atualiza-listas-portaria-344-1998",
        "sngpc-boas-praticas-evitar-pendencias",
        "o-que-e-afe-e-por-que-e-importante",
        "crf-responsavel-tecnico-farmacias-drogarias",
        "produtos-veterinarios-controle-especial-mapa-portaria-837",
        "farmacia-popular-adequacao-materiais-periodo-eleitoral",
        "farmacia-popular-portaria-12091-2026-novas-regras",
        "farmacia-popular-inconsistencias-prescricoes-monitoramento",
        "credenciamento-farmacia-popular-municipios-com-vagas",
        "anvisa-suspende-medicamento-proibe-produtos-irregulares",
        "anvisa-regras-cosmeticos-artesanais",
        "anvisa-edital-6-2026-afe-manipulacao-preparacoes-estereis",
    ]
    assert urls[:13] == [f"https://www.regularizeconsultorias.com.br/noticias/{slug}/" for slug in lote]
    # Fase 1M v2: As 6 matérias atualizadas em 08/10/2026 vêm logo depois.
    certidoes_url = "https://www.regularizeconsultorias.com.br/noticias/anvisa-certidoes-certificados-medicamentos-solicita/"
    alimentos_url = "https://www.regularizeconsultorias.com.br/noticias/anvisa-prazo-adequacao-notificacao-alimentos-setembro-2026/"
    cnes_08_url = "https://www.regularizeconsultorias.com.br/noticias/cnes-competencia-08-2026-prazo-transmissao/"
    assert urls[13] == HEMOTERAPIA_URL
    assert urls[14] == certidoes_url
    assert urls[15] == EDITAL_5_2026_URL
    assert urls[16] == alimentos_url
    assert urls[17] == cnes_08_url
    assert urls[18] == SICERT_URL
    assert urls[19] == "https://www.regularizeconsultorias.com.br/noticias/novos-compendios-farmacopeia-brasileira-entram-em-vigor/"
    assert urls[20] == "https://www.regularizeconsultorias.com.br/noticias/anvisa-hmp-solicita-medicamentos-produtos-biologicos/"
    # A suspensão do SIFAP permanece à frente das duas matérias empatadas às 11h13.
    assert urls[21] == SIFAP_SUSPENSAO_URL
    assert urls[22] == "https://www.regularizeconsultorias.com.br/noticias/prazo-sifap-terminou-pendencias-analise-rta-farmacia-popular/"
    assert urls[23] == "https://www.regularizeconsultorias.com.br/noticias/sifap-regularizacao-cadastral-farmacias-notificadas-13-maio/"

    # SNCR, AFE e Cadastro compartilham 07/10/2026 às 09h08. O empate conserva a ordem relativa.
    assert urls[24] == SNCR_WEBINAR_URL
    assert urls.count(SNCR_WEBINAR_URL) == 1
    assert urls[25] == "https://www.regularizeconsultorias.com.br/noticias/anvisa-atualiza-acesso-sncr-afe-farmacias-privadas/"
    assert urls[26] == "https://www.regularizeconsultorias.com.br/noticias/cadastro-anvisa-govbr-transicao-sistemas/"
    assert urls[27] == "https://www.regularizeconsultorias.com.br/noticias/nova-regra-anvisa-cnes-receitas-farmacias/"
    assert urls.count("https://www.regularizeconsultorias.com.br/noticias/cadastro-anvisa-govbr-transicao-sistemas/") == 1
    assert urls[28] == CNES_SNCR_URL
    assert urls.count(CNES_SNCR_URL) == 1
    assert urls[29] == "https://www.regularizeconsultorias.com.br/noticias/receituarios-controlados-modelos-oficiais-anvisa/"
    assert urls[7] == PORTARIA_URL
    assert urls[9] == CREDENCIAMENTO_URL
    # O consolidado de fiscalização permanece em 06/10/2026 às 16h32.
    assert urls[10] == PRODUTOS_IRREGULARES_URL
    assert urls.count(PRODUTOS_IRREGULARES_URL) == 1
    mapa_portaria_1617 = "https://www.regularizeconsultorias.com.br/noticias/mapa-portaria-1617-2026-aditivos-antimicrobianos-alimentacao-animal/"
    assert urls[30] == mapa_portaria_1617
    assert urls.count(mapa_portaria_1617) == 1
    assert urls[31] == CNES_COMPETENCIA_09_2026_URL
    assert urls.count(CNES_COMPETENCIA_09_2026_URL) == 1
    assert urls[32] == COSMETICOS_URL
    assert urls.count(COSMETICOS_URL) == 1
    assert urls[11] == "https://www.regularizeconsultorias.com.br/noticias/anvisa-regras-cosmeticos-artesanais/"
    assert urls.count("https://www.regularizeconsultorias.com.br/noticias/anvisa-regras-cosmeticos-artesanais/") == 1
    assert urls[33] == GLP1_URL
    assert urls[34] == SEMAVY_PROPAGANDA_URL
    assert urls.count(SEMAVY_PROPAGANDA_URL) == 1
    assert urls[35] == IN_470_SUPLEMENTOS_URL
    assert urls.count(IN_470_SUPLEMENTOS_URL) == 1
    assert urls[36] == SANEANTES_URL
    assert urls.count(SANEANTES_URL) == 1
    assert urls[12] == EDITAL_6_2026_AFE_URL
    assert urls.count(EDITAL_6_2026_AFE_URL) == 1
    assert urls[37] == PASSIVO_DISPOSITIVOS_URL
    assert urls[38] == IFAS_GLP1_PETICOES_URL
    assert urls[39] == DUIMP_URL
    assert urls[40] == FITOTERAPICOS_URL
    assert urls[41] == ARMAZENS_ALFANDEGADOS_URL
    assert urls[42] == CANNABIS_URL
    assert urls[43] == RPBR_URL
    assert urls[44] == SIPROQUIM_IN338_URL
    assert urls[45] == CBPF_IN451_URL
    assert urls[46] == "https://www.regularizeconsultorias.com.br/noticias/anvisa-cadastro-eletronico-fabricantes-internacionais-cosmeticos-saneantes/"
    assert urls[47] == FABRICANTES_INTERNACIONAIS_URL
    assert urls[48] == "https://www.regularizeconsultorias.com.br/noticias/anvisa-formulario-cbpf-terapias-avancadas/"
    assert urls[8] == MONITORAMENTO_URL
    edital_position = urls.index(EDITAL_5_2026_URL)
    assert edital_position == 15
    revisao_position = urls.index(REVISAO_PROPAGANDA_URL)
    assert revisao_position == 51
    assert urls[revisao_position - 1] == "https://www.regularizeconsultorias.com.br/noticias/anvisa-amplia-painel-medicamentos-pendentes-registro/"
    assert urls[revisao_position + 1] == DISPOSITIVOS_IRREGULARES_URL
    dispositivos_position = urls.index(DISPOSITIVOS_IRREGULARES_URL)
    assert dispositivos_position == 52
    assert urls[dispositivos_position - 1] == REVISAO_PROPAGANDA_URL
    assert urls[dispositivos_position + 1] == DCB_IN462_URL
    dcb_position = urls.index(DCB_IN462_URL)
    assert dcb_position == 53
    assert urls[dcb_position - 1] == DISPOSITIVOS_IRREGULARES_URL
    assert urls[dcb_position + 1] == PARAMOL_URL
    paramol_position = urls.index(PARAMOL_URL)
    assert paramol_position == 54
    assert urls[paramol_position - 1] == DCB_IN462_URL
    assert urls[paramol_position + 1] == SEMAGLUTIDA_URL
    supervisao_position = urls.index(SUPERVISAO_CONTEUDO_URL)
    assert urls[supervisao_position - 1] == RETATRUTIDA_URL
    assert urls[supervisao_position + 1] == "https://www.regularizeconsultorias.com.br/noticias/anvisa-suspende-dispositivos-medicos-heuer-international/"
    assert CREDENCIAMENTO_URL in urls, "Credenciamento is missing from JSON-LD"
    assert urls.index(CREDENCIAMENTO_URL) == 9


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


def _validar_conteudo_alimentos(html: str):
    assert "article-badge-urgente" not in html, "Alimentos não pode conter selo de urgente"
    assert "news-urgent-badge" not in html, "Alimentos não pode conter classe de badge urgente"
    assert "URGENTE" not in html, "Alimentos não pode conter menção textual a URGENTE"
    assert "article-badge-atualizacao" in html, "Alimentos deve conter selo de atualização"
    assert "devem ter a adequação solicitada até 1º de setembro" not in html, "Alimentos mantém frase legada de prazo aberto"
    assert "180 dias contados da data da notificação" in html, "Alimentos deve citar 180 dias da notificação"
    assert "exclusivamente para o esgotamento dessas embalagens" in html, "Alimentos deve delimitar ao esgotamento de embalagens"
    for bad in ("180 dias de formulação", "180 dias para vender produtos acabados", "prazo geral de 180 dias de estoque", "estoque de produtos acabados abrangido pelo prazo"):
        assert bad not in html.casefold(), f"Alimentos contém expansão indevida de prazo: {bad}"


def _validar_conteudo_solicita(html: str):
    assert "não deixar solicitações relevantes para o último momento" not in html.casefold(), "Solicita contém orientação indevida de último momento"
    assert ("transição encerrou-se em 11/09/2026" in html or "encerrou-se em 11/09/2026" in html), "Solicita deve explicitar transição encerrada em 11/09/2026"
    atribuicao_pattern = re.compile(
        r"11/08/2026.*?(?:anunciou|informou).*?início informado a partir de\s*(?:<strong>)?12/08/2026(?:</strong>)?",
        re.DOTALL | re.IGNORECASE,
    )
    assert atribuicao_pattern.search(html) is not None, "Solicita deve atribuir expressamente o início de 12/08 ao anúncio de 11/08"
    for bad in (
        "pleno funcionamento comprovado em teste",
        "sistema testado com sucesso nesta data",
        "operação 100% disponível",
        "disponibilidade atual confirmada em auditoria técnica",
        "disponibilidade confirmada em auditoria técnica",
        "funcionamento plenamente confirmado",
    ):
        assert bad not in html.casefold(), f"Solicita contém alegação operacional indevida: {bad}"


def _validar_conteudo_cnes08(html: str):
    assert "período divulgado no cronograma oficial do CNES" in html
    assert "13/08/2026 a 08/09/2026" in html
    for bad in ("sistema indisponível atualmente", "transmissor bloqueado em definitivo", "serviço desativado hoje"):
        assert bad not in html.casefold()


def _validar_conteudo_hemoterapia(html: str):
    assert "serviços de hemoterapia" in html.casefold(), "Hemoterapia deve delimitar o público aos serviços de hemoterapia"
    assert "portaria gm/ms 11.685" in html.casefold() or "portaria gm/ms nº 11.685" in html.casefold()
    assert "30/09/2026" in html, "Hemoterapia deve citar a data de 30/09 informada pela Anvisa"
    assert "90 dias" in html, "Hemoterapia deve citar o prazo de 90 dias da Portaria"
    assert "bvs/ms" in html.casefold(), "Hemoterapia deve citar o informe da BVS/MS"
    h1_m = re.search(r"<h1\b[^>]*>(.*?)</h1>", html, re.DOTALL)
    assert h1_m is not None
    assert "30 de setembro" not in h1_m.group(1).casefold(), "H1 de hemoterapia não deve conter data única incondicional"
    assert "outubro" not in h1_m.group(1).casefold(), "H1 de hemoterapia não deve conter data única incondicional"
    for bad in ("todos os estabelecimentos de saúde", "todas as farmácias e drogarias devem se adequar à portaria 11.685"):
        assert bad not in html.casefold()


def test_guardas_fase_1m_v2_conteudo_e_coerencia():
    # 1. Alimentos
    alimentos_html = (ROOT / "noticias/anvisa-prazo-adequacao-notificacao-alimentos-setembro-2026/index.html").read_text(encoding="utf-8")
    _validar_conteudo_alimentos(alimentos_html)

    # 2. Solicita
    solicita_html = (ROOT / "noticias/anvisa-certidoes-certificados-medicamentos-solicita/index.html").read_text(encoding="utf-8")
    _validar_conteudo_solicita(solicita_html)

    # 3. CNES 08
    cnes_html = (ROOT / "noticias/cnes-competencia-08-2026-prazo-transmissao/index.html").read_text(encoding="utf-8")
    _validar_conteudo_cnes08(cnes_html)

    # 4. Hemoterapia
    hemo_html = (ROOT / "noticias/ministerio-saude-atualiza-procedimentos-hemoterapicos-transicao-2026/index.html").read_text(encoding="utf-8")
    _validar_conteudo_hemoterapia(hemo_html)

    # 5. Coerência entre dateModified, carimbo visível e card nas 6 matérias
    index_html = NEWS_INDEX_PATH.read_text(encoding="utf-8")
    fase_1m_stamps = {
        "anvisa-certidoes-certificados-medicamentos-solicita": "2026-10-08T07:45:00-03:00",
        "anvisa-edital-5-2026-dispositivos-medicos-inovadores": "2026-10-08T07:44:00-03:00",
        "anvisa-prazo-adequacao-notificacao-alimentos-setembro-2026": "2026-10-08T07:43:00-03:00",
        "cnes-competencia-08-2026-prazo-transmissao": "2026-10-08T07:42:00-03:00",
        "ministerio-saude-atualiza-procedimentos-hemoterapicos-transicao-2026": "2026-10-08T11:55:00-03:00",
        "anvisa-descontinua-sicert-certificados-dispositivos-medicos": "2026-10-08T07:40:00-03:00",
    }
    cards = _news_cards(index_html)
    for slug, stamp in fase_1m_stamps.items():
        article_html = (ROOT / f"noticias/{slug}/index.html").read_text(encoding="utf-8")
        assert f'"dateModified": "{stamp}"' in article_html or f'"dateModified":"{stamp}"' in article_html
        assert f'<time datetime="{stamp}"' in article_html
        card = next(c for c in cards if f'/noticias/{slug}/' in c)
        assert f'data-updated="{stamp}"' in card
        assert f'<time datetime="{stamp}"' in card


def test_guardas_fase_1m_v2_rejeitam_mutacoes_em_memoria():
    # Valida que as regras de detecção rejeitam regressões simuladas em cópias em memória através das próprias funções de guarda
    alimentos_html = (ROOT / "noticias/anvisa-prazo-adequacao-notificacao-alimentos-setembro-2026/index.html").read_text(encoding="utf-8")
    solicita_html = (ROOT / "noticias/anvisa-certidoes-certificados-medicamentos-solicita/index.html").read_text(encoding="utf-8")
    hemo_html = (ROOT / "noticias/ministerio-saude-atualiza-procedimentos-hemoterapicos-transicao-2026/index.html").read_text(encoding="utf-8")

    # Mutação 1: Reverter Alimentos para Urgente
    mutated_urgente = alimentos_html.replace("article-badge-atualizacao", "article-badge-urgente")
    with pytest.raises(AssertionError):
        _validar_conteudo_alimentos(mutated_urgente)

    # Mutação 2: Alimentos ampliando 180 dias para estoque de produtos acabados
    mutated_180 = alimentos_html.replace("</section>", "<p>Prazo geral de 180 dias de estoque para todos os produtos acabados.</p></section>")
    with pytest.raises(AssertionError):
        _validar_conteudo_alimentos(mutated_180)

    # Mutação 3: Solicita retirando atribuição do início mas mantendo a data em outro trecho
    mutated_sem_atribuicao = solicita_html.replace(
        "com início informado a partir de <strong>12/08/2026</strong>",
        "com diversas novidades divulgadas pelo órgão regulador"
    )
    assert "12/08/2026" in mutated_sem_atribuicao  # data ainda existe no lead
    with pytest.raises(AssertionError):
        _validar_conteudo_solicita(mutated_sem_atribuicao)

    # Mutação 4: Solicita adicionando alegação operacional não comprovada
    mutated_operacional = solicita_html.replace(
        "</section>",
        "<p>Disponibilidade atual confirmada em auditoria técnica pelo órgão regulador.</p></section>"
    )
    with pytest.raises(AssertionError):
        _validar_conteudo_solicita(mutated_operacional)

    # Mutação 5: Solicita reabrindo transição como janela futura
    mutated_reaberta = solicita_html.replace(
        "</section>",
        "<p>Atenção para não deixar solicitações relevantes para o último momento da transição.</p></section>"
    )
    with pytest.raises(AssertionError):
        _validar_conteudo_solicita(mutated_reaberta)

    # Mutação 6: Hemoterapia com data única incondicional no H1 (o H1 tem hífens opcionais em "procedi&shy;mentos" e
    # "hemo&shy;terápicos" desde o layout comum de 10/10/2026; a mutação troca o título inteiro e precisa de fato mudar
    # o HTML)
    mutated_hemo = hemo_html.replace(
        "Novos procedi&shy;mentos hemo&shy;terápicos entram em vigor após período de transição",
        "Novos procedimentos hemoterápicos entraram em vigor em 30 de setembro"
    )
    assert mutated_hemo != hemo_html
    with pytest.raises(AssertionError):
        _validar_conteudo_hemoterapia(mutated_hemo)
