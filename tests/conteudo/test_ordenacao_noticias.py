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
# 22/10/2026, 22h40 (hora do commit): RE nº 4.143, 4.147 e 4.150/2026; o SNCR recebeu o mesmo carimbo no mesmo lote.
PRODUTOS_IRREGULARES_UPDATED = "2026-10-22T22:40:00-03:00"
# Notícia do SISPA, atualizada em 20/10/2026 às 10h12 (Comunicado nº 1/2026 da CGAA/DSV/SDA/MAPA).
SISPA_URL = "https://www.regularizeconsultorias.com.br/noticias/mapa-sispa-registro-agrotoxicos/"
SISPA_UPDATED = "2026-10-20T10:12:00-03:00"
FABRICANTES_INTERNACIONAIS_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-cadastro-eletronico-fabricantes-internacionais-dispositivos-medicos/"
SUPERVISAO_CONTEUDO_URL = "https://www.regularizeconsultorias.com.br/noticias/farmaceutico-supervisiona-conteudos-farmacia-redes-sociais-sites/"
RETATRUTIDA_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-retatrutida-sem-registro-produtos-irregulares/"
CNES_06_URL = "https://www.regularizeconsultorias.com.br/noticias/cnes-prorroga-transmissor-competencia-06-2026/"
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
# Nova notícia da competência 10/2026 do CNES (informe de 16/10/2026), publicada em 16/10/2026 às 20h06.
CNES_COMPETENCIA_10_2026_URL = "https://www.regularizeconsultorias.com.br/noticias/cnes-competencia-10-2026-prazo-transmissao/"
# Esclarecimento sobre lembretes do Farmácia Popular pelo WhatsApp, publicado em 17/10/2026 às 09h50.
FP_LEMBRETES_WHATSAPP_URL = "https://www.regularizeconsultorias.com.br/noticias/farmacia-popular-esclarecimento-lembretes-whatsapp/"
# Nova notícia do Edital de Chamamento 6/2026 (AFE para preparações estéreis).
EDITAL_6_2026_AFE_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-edital-6-2026-afe-manipulacao-preparacoes-estereis/"
# Notícia CNES/SNCR revisada em 28/09/2026 e reposicionada pelo dateModified.
CNES_SNCR_URL = "https://www.regularizeconsultorias.com.br/noticias/cnes-continua-obrigatorio-sncr-afe-farmacias/"
# Notícia SNCR atualizada com a etapa de 30/09/2026 e reposicionada pelo dateModified; atualizada de novo em
# 20/10/2026 às 13h00 (lote 2 do SNCR: informe de 15/10 e Perguntas e Respostas sobre a integração, 1ª edição).
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


def _parse_card_date(value):
    # Data só com o dia (AAAA-MM-DD): início desse dia em Brasília (-03:00), a mesma regra de assets/js/main.js
    # (parseCardDate, 12/10/2026). O card mostra só o dia; a hora 00h00 serve apenas para ordenar.
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        value += "T00:00:00-03:00"
    return datetime.fromisoformat(value).timestamp()


def _card_timestamp(card):
    updated_match = re.search(r'\bdata-updated="([^"]+)"', card)
    if updated_match:
        return _parse_card_date(updated_match.group(1))

    published_match = re.search(r'<time\b[^>]*datetime="([^"]+)"', card)
    assert published_match is not None, "News card timestamp not found"
    return _parse_card_date(published_match.group(1))


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
    # O card mostra "14/08/2026 • 09h04", sem prefixo desde 12/10/2026 (parecer de 11/10/2026, R1): o <time> do
    # card é essa atualização, a data que ordena a lista (test_listagem_rotulo_atualizacao.py). A publicação original
    # de 22/05/2026 continua protegida na página da matéria, no datePublished e no "Publicado em".
    assert '<time datetime="2026-08-14T09:04:41-03:00" class="leading-none">14/08/2026 • 09h04</time>' in article_html, "The card <time> must carry the update it shows"
    assert "Atualizado em" not in article_html
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

    sispa_card = next((card for card in _news_cards(html) if _card_url(card) == SISPA_URL), None)
    assert sispa_card is not None
    assert f'data-updated="{SISPA_UPDATED}"' in sispa_card
    assert f'<time datetime="{SISPA_UPDATED}" class="leading-none">20/10/2026 • 10h12</time>' in sispa_card

def test_news_index_itemlist_ordering():
    html = NEWS_INDEX_PATH.read_text(encoding="utf-8")
    items = _itemlist(html)

    assert items, "ItemList is empty"
    urls = [item.get("url") for item in items]
    # 26/10/2026, 08h30: as matérias do MAPA 1.617 e do período eleitoral, atualizadas, sobem para a 1ª e a 2ª posições; as que ficavam acima delas descem duas (até a 6ª) ou uma (da 8ª à 35ª).
    # 26/10/2026, 08h30: a matéria do SNCR, atualizada (itens A-1 e M-1), entra no mesmo carimbo do MAPA e do período eleitoral e fica em 3º, logo depois delas; o consolidado de irregulares desce para o 4º.
    assert urls[2] == SNCR_WEBINAR_URL
    # 21/10/2026, 17h45: produtos irregulares (RE nº 4.140/2026 e correção da RE nº 3.159/2026) voltam à 1ª posição.
    assert urls[3] == PRODUTOS_IRREGULARES_URL
    # SISPA (Comunicado nº 1/2026) segue logo depois.
    assert urls[4] == SISPA_URL
    # 17/10/2026, 09h50: o card do esclarecimento do Farmácia Popular entrou na 1ª posição da listagem.
    assert urls[5] == FP_LEMBRETES_WHATSAPP_URL
    # 16/10/2026, 20h06: o card do CNES 10/2026 entrou na 1ª posição da listagem.
    assert urls[6] == CNES_COMPETENCIA_10_2026_URL
    # A DCB segue às 09h06 de 13/10; o SNCR saiu desse empate em 20/10.
    # A matéria eleitoral (12/10/2026, 18h08) e o CNES 09/2026 (11/10/2026, 06h07) vêm em seguida.
    assert urls[7] == DCB_IN462_URL
    assert urls[1] == "https://www.regularizeconsultorias.com.br/noticias/farmacia-popular-adequacao-materiais-periodo-eleitoral/"
    assert urls[8] == CNES_COMPETENCIA_09_2026_URL
    # Lote de conteúdo e dados de 09/10/2026, sem o consolidado de fiscalização, que subiu com o carimbo de 13/10.
    lote = [
        "policia-federal-classificacao-produtos-simples-compostos-siproquim",
        "anvisa-atualiza-listas-portaria-344-1998",
        "sngpc-boas-praticas-evitar-pendencias",
        "o-que-e-afe-e-por-que-e-importante",
        "crf-responsavel-tecnico-farmacias-drogarias",
        "produtos-veterinarios-controle-especial-mapa-portaria-837",
        "farmacia-popular-portaria-12091-2026-novas-regras",
        "farmacia-popular-inconsistencias-prescricoes-monitoramento",
        "credenciamento-farmacia-popular-municipios-com-vagas",
        "anvisa-regras-cosmeticos-artesanais",
        "anvisa-edital-6-2026-afe-manipulacao-preparacoes-estereis",
    ]
    assert urls[9:20] == [f"https://www.regularizeconsultorias.com.br/noticias/{slug}/" for slug in lote]
    # Fase 1M v2: As 6 matérias atualizadas em 08/10/2026 vêm logo depois.
    certidoes_url = "https://www.regularizeconsultorias.com.br/noticias/anvisa-certidoes-certificados-medicamentos-solicita/"
    alimentos_url = "https://www.regularizeconsultorias.com.br/noticias/anvisa-prazo-adequacao-notificacao-alimentos-setembro-2026/"
    cnes_08_url = "https://www.regularizeconsultorias.com.br/noticias/cnes-competencia-08-2026-prazo-transmissao/"
    assert urls[20] == HEMOTERAPIA_URL
    assert urls[21] == certidoes_url
    assert urls[22] == EDITAL_5_2026_URL
    assert urls[23] == alimentos_url
    assert urls[24] == cnes_08_url
    assert urls[25] == SICERT_URL
    assert urls[26] == "https://www.regularizeconsultorias.com.br/noticias/novos-compendios-farmacopeia-brasileira-entram-em-vigor/"
    assert urls[27] == "https://www.regularizeconsultorias.com.br/noticias/anvisa-hmp-solicita-medicamentos-produtos-biologicos/"
    # A suspensão do SIFAP permanece à frente das duas matérias empatadas às 11h13.
    assert urls[28] == SIFAP_SUSPENSAO_URL
    assert urls[29] == "https://www.regularizeconsultorias.com.br/noticias/prazo-sifap-terminou-pendencias-analise-rta-farmacia-popular/"
    assert urls[30] == "https://www.regularizeconsultorias.com.br/noticias/sifap-regularizacao-cadastral-farmacias-notificadas-13-maio/"

    # AFE e Cadastro continuam empatados em 07/10/2026 às 09h08. O SNCR saiu desse empate em 13/10/2026.
    assert urls.count(SNCR_WEBINAR_URL) == 1
    assert urls[31] == "https://www.regularizeconsultorias.com.br/noticias/anvisa-atualiza-acesso-sncr-afe-farmacias-privadas/"
    assert urls[32] == "https://www.regularizeconsultorias.com.br/noticias/cadastro-anvisa-govbr-transicao-sistemas/"
    assert urls[33] == "https://www.regularizeconsultorias.com.br/noticias/nova-regra-anvisa-cnes-receitas-farmacias/"
    assert urls.count("https://www.regularizeconsultorias.com.br/noticias/cadastro-anvisa-govbr-transicao-sistemas/") == 1
    assert urls[34] == CNES_SNCR_URL
    assert urls.count(CNES_SNCR_URL) == 1
    assert urls[35] == "https://www.regularizeconsultorias.com.br/noticias/receituarios-controlados-modelos-oficiais-anvisa/"
    assert urls[15] == PORTARIA_URL
    assert urls[17] == CREDENCIAMENTO_URL
    assert urls.count(PRODUTOS_IRREGULARES_URL) == 1
    assert urls.count(SISPA_URL) == 1
    mapa_portaria_1617 = "https://www.regularizeconsultorias.com.br/noticias/mapa-portaria-1617-2026-aditivos-antimicrobianos-alimentacao-animal/"
    assert urls[0] == mapa_portaria_1617
    assert urls.count(mapa_portaria_1617) == 1
    assert urls.count(CNES_COMPETENCIA_09_2026_URL) == 1
    assert urls[36] == COSMETICOS_URL
    assert urls.count(COSMETICOS_URL) == 1
    assert urls[18] == "https://www.regularizeconsultorias.com.br/noticias/anvisa-regras-cosmeticos-artesanais/"
    assert urls.count("https://www.regularizeconsultorias.com.br/noticias/anvisa-regras-cosmeticos-artesanais/") == 1
    assert urls[37] == GLP1_URL
    assert urls[38] == SEMAVY_PROPAGANDA_URL
    assert urls.count(SEMAVY_PROPAGANDA_URL) == 1
    assert urls[39] == IN_470_SUPLEMENTOS_URL
    assert urls.count(IN_470_SUPLEMENTOS_URL) == 1
    assert urls[40] == SANEANTES_URL
    assert urls.count(SANEANTES_URL) == 1
    assert urls[19] == EDITAL_6_2026_AFE_URL
    assert urls.count(EDITAL_6_2026_AFE_URL) == 1
    assert urls[41] == PASSIVO_DISPOSITIVOS_URL
    assert urls[42] == IFAS_GLP1_PETICOES_URL
    assert urls[43] == DUIMP_URL
    assert urls[44] == FITOTERAPICOS_URL
    assert urls[45] == ARMAZENS_ALFANDEGADOS_URL
    assert urls[46] == CANNABIS_URL
    assert urls[47] == RPBR_URL
    assert urls[48] == SIPROQUIM_IN338_URL
    assert urls[49] == CBPF_IN451_URL
    assert urls[50] == "https://www.regularizeconsultorias.com.br/noticias/anvisa-cadastro-eletronico-fabricantes-internacionais-cosmeticos-saneantes/"
    assert urls[51] == FABRICANTES_INTERNACIONAIS_URL
    assert urls[52] == "https://www.regularizeconsultorias.com.br/noticias/anvisa-formulario-cbpf-terapias-avancadas/"
    assert urls[16] == MONITORAMENTO_URL
    edital_position = urls.index(EDITAL_5_2026_URL)
    assert edital_position == 22
    revisao_position = urls.index(REVISAO_PROPAGANDA_URL)
    assert revisao_position == 55
    assert urls[revisao_position - 1] == "https://www.regularizeconsultorias.com.br/noticias/anvisa-amplia-painel-medicamentos-pendentes-registro/"
    assert urls[revisao_position + 1] == DISPOSITIVOS_IRREGULARES_URL
    dispositivos_position = urls.index(DISPOSITIVOS_IRREGULARES_URL)
    assert dispositivos_position == 56
    assert urls[dispositivos_position - 1] == REVISAO_PROPAGANDA_URL
    assert urls[dispositivos_position + 1] == PARAMOL_URL
    dcb_position = urls.index(DCB_IN462_URL)
    assert dcb_position == 7
    assert urls[dcb_position - 1] == CNES_COMPETENCIA_10_2026_URL
    eleitoral = "https://www.regularizeconsultorias.com.br/noticias/farmacia-popular-adequacao-materiais-periodo-eleitoral/"
    # Desde 26/10/2026 a matéria eleitoral está em 2º; depois da DCB vem o CNES 09/2026.
    assert urls[1] == eleitoral
    assert urls[dcb_position + 1] == CNES_COMPETENCIA_09_2026_URL
    paramol_position = urls.index(PARAMOL_URL)
    assert paramol_position == 57
    assert urls[paramol_position - 1] == DISPOSITIVOS_IRREGULARES_URL
    assert urls[paramol_position + 1] == SEMAGLUTIDA_URL
    supervisao_position = urls.index(SUPERVISAO_CONTEUDO_URL)
    # 12/10/2026 (R2): o card do CNES 06/2026 passou a mostrar a atualização declarada na matéria (18/07/2026, só o
    # dia) e entrou entre a Retatrutida (24/07/2026) e a Supervisão de conteúdo (17/07/2026).
    assert urls[supervisao_position - 1] == CNES_06_URL
    assert urls[supervisao_position - 2] == RETATRUTIDA_URL
    assert urls[supervisao_position + 1] == "https://www.regularizeconsultorias.com.br/noticias/anvisa-suspende-dispositivos-medicos-heuer-international/"
    assert CREDENCIAMENTO_URL in urls, "Credenciamento is missing from JSON-LD"
    assert urls.index(CREDENCIAMENTO_URL) == 17


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
    # Modelo único (12/10/2026, R1): todos os cards levam news-card-compact; a posição não troca o formato.
    assert all("news-card-compact" in card.split(">", 1)[0] for card in cards)


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
