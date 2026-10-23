import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).parents[2]
NEWS_PATH = ROOT / "noticias" / "anvisa-suspende-medicamento-proibe-produtos-irregulares" / "index.html"
NEWS_INDEX_PATH = ROOT / "noticias" / "index.html"
SITEMAP_PATH = ROOT / "sitemap.xml"
URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-suspende-medicamento-proibe-produtos-irregulares/"
PUBLISHED = "2026-07-05T18:00:00-03:00"
# 21/10/2026, 18h42: quadro da RE nº 4.140/2026 (DOU de 21/10/2026) e correção da RE nº 3.159/2026.
# O carimbo anterior foi 20/10/2026, 10h12 (RE nº 4.090 e 4.105/2026).
# Os carimbos anteriores foram 15/10/2026, 17h44 (RE nº 4.035/2026), 13/10/2026, 19h54 (alcance da
# RE nº 3.634/2026) e 11h51 (seis resoluções do mesmo dia). A DCB permanece às 09h06 de 13/10/2026; o SNCR saiu desse
# carimbo em 20/10/2026, às 13h00 (lote 2 do SNCR).
# 22/10/2026, 22h40 (hora do commit): quadro das RE nº 4.143, 4.147 e 4.150/2026 (DOU de 22/10/2026).
# O carimbo anterior foi 21/10/2026, 18h42 (RE nº 4.140/2026 e correção da RE nº 3.159/2026).
UPDATED = "2026-10-22T22:40:00-03:00"
UPDATED_DAY = f"{datetime.fromisoformat(UPDATED):%d/%m/%Y}"
UPDATED_CLOCK = f"{datetime.fromisoformat(UPDATED):%Hh%M}"
# Links das íntegras retirados em 20/10/2026 (notícias sem links externos); não podem voltar.
DOU_RE_4035_URL = "https://www.in.gov.br/web/dou/-/resolucao-re-n-4.035-de-9-de-outubro-de-2026-738059775"
DOU_RE_4090_URL = "https://www.in.gov.br/web/dou/-/resolucao-re-n-4.090-de-15-de-outubro-de-2026-738844837"
DOU_RE_4105_URL = "https://www.in.gov.br/web/dou/-/resolucao-re-n-4.105-de-15-de-outubro-de-2026-738856116"
DOU_RE_4140_URL = "https://www.in.gov.br/web/dou/-/resolucao-re-n-4.140-de-19-de-outubro-de-2026-739392776"
DOU_RE_3159_URL = "https://www.in.gov.br/web/dou/-/resolucao-re-n-3.159-de-12-de-agosto-de-2026-*-739134036"
DOBUTAMINA_LOTES = ("24092127", "24102310", "25102244", "25102243", "25112308")



def _page_html():
    """HTML da notícia sem os <summary> dos itens recolhidos da v2.

    Desde a v2, cada RE fica num <details class="irregulares-re"> com um resumo (RE, produto e data) antes do
    texto. As fatias deste arquivo vão de um título ao seguinte; sem os resumos, elas continuam a ver só o texto da
    notícia, que é o mesmo da v1.
    """
    html = NEWS_PATH.read_text(encoding="utf-8")
    return re.sub(r'(<details class="irregulares-(?:re|detalhes)"[^>]*>)<summary>.*?</summary>', r"\1", html,
                  flags=re.DOTALL)

def _section_between(html, start, end):
    begin = html.index(start)
    return html[begin:html.index(end, begin)]


def _august_callout(html):
    start = html.index('data-news-update-callout aria-labelledby="novas-medidas-agosto-title"')
    return html[start:html.index("</aside>", start)]


def _re3717_callout(html):
    return _section_between(html, "<h2>21 de setembro: RE nº 3.717/2026", "<h2>21 de setembro: RE nº 3.718/2026")


def _latest_callout(html):
    return _section_between(html, "<h2>16 de setembro: quatro resoluções", "<h2>Setembro: RE nº 3.547/2026")


def _september_callout(html):
    return _section_between(html, "<h2>Setembro: RE nº 3.547/2026", "<h2>11 de setembro: RE nº 3.546/2026")


def _september_section(html):
    start = html.index("<h2>Setembro: RE nº 3.547/2026")
    # A RE nº 3.546/2026 (TYG), do mesmo dia, e os atos de 08 e 01/09 vêm depois e ficam fora da fatia.
    return html[start:html.index("<h2>11 de setembro: RE nº 3.546/2026", start)]


def _re3717_section(html):
    start = html.index("<h2>21 de setembro: RE nº 3.717/2026")
    # A revogação da RE nº 3.718/2026, também de 21/09, vem logo depois e fica fora da fatia.
    return html[start:html.index("<h2>21 de setembro: RE nº 3.718/2026", start)]


def _latest_section(html):
    start = html.index("<h2>16 de setembro: quatro resoluções")
    return html[start:html.index("<h2>Setembro: RE nº 3.547/2026", start)]


def _subsection(section, heading, next_heading=None):
    start = section.index(f"<h3>{heading}</h3>")
    if next_heading is None:
        return section[start:]
    return section[start:section.index(f"<h3>{next_heading}</h3>", start)]


def _items(callout):
    return re.findall(r"<li\b[^>]*>(.*?)</li>", callout, re.DOTALL)


def _consolidated_card(news_index):
    cards = re.findall(r'(<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>)', news_index, re.DOTALL)
    own = [card for card in cards if 'href="/noticias/anvisa-suspende-medicamento-proibe-produtos-irregulares/"' in card]
    assert len(own) == 1
    return own[0]


def _text(html):
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def test_article_consolidates_the_measures_of_17_and_19_august():
    html = _page_html()
    callout = _august_callout(html)

    assert f'"datePublished": "{PUBLISHED}"' in html
    assert f'"dateModified": "{UPDATED}"' in html
    assert datetime.fromisoformat(UPDATED) > datetime.fromisoformat(PUBLISHED)
    assert 'property="article:modified_time"' in html
    assert "17/08" in callout and "19/08" in callout
    assert callout.index("17/08") < callout.index("19/08")
    assert "data-news-update-callout" in callout
    assert "ATUALIZAÇÃO" in callout
    for term in (
        "Newfit",
        "sibutramina",
        "fluoxetina",
        "furosemida",
        "Mounja Gummy",
        "Trodelvy",
        "lote 10008808",
        "Shark Pro",
        "Boas Práticas de Fabricação",
        "Máscara Avocado Tutano Vegano",
        "Capi Hair",
        "Essence",
        "Geo Beauty",
        "Essencial for Men",
        "Rainha Solar",
        "Mixderme",
        "Ar Tratamento",
        "Natural Perfection Double Shield Sun Stick SPD50+",
        "Fraijour Retin-Collagen 3D Core Eye Cream",
    ):
        assert term in callout
    assert "não alcança todos os lotes ou a marca" in callout
    assert "recolhimento" in callout
    assert "Mounjaro" not in callout
    assert "suspensão de AFE" not in callout
    assert "Fonte oficial" not in html


def test_september_update_reflects_re_3547_and_keeps_history():
    html = _page_html()
    september = _september_callout(html)
    text = _text(september)

    assert html.index('id="novas-medidas-21-outubro-title"') < html.index('id="novas-medidas-19-outubro-title"')
    assert html.index('id="novas-medidas-19-outubro-title"') < html.index('id="novas-medidas-14-outubro-title"')
    assert html.index('id="novas-medidas-14-outubro-title"') < html.index('id="novas-medidas-13-outubro-title"')
    assert html.index('id="novas-medidas-13-outubro-title"') < html.index('id="novas-medidas-06-outubro-title"')
    assert html.index('id="novas-medidas-06-outubro-title"') < html.index('id="novas-medidas-02-outubro-title"')
    assert html.index('id="novas-medidas-02-outubro-title"') < html.index('id="novas-medidas-25-setembro-title"')
    assert html.index('id="novas-medidas-25-setembro-title"') < html.index('id="novas-medidas-21-setembro-title"')
    assert html.index('id="novas-medidas-21-setembro-title"') < html.index('id="novas-medidas-16-setembro-title"')
    assert html.index('id="novas-medidas-16-setembro-title"') < html.index('id="novas-medidas-setembro-title"')
    assert html.index('id="novas-medidas-setembro-title"') < html.index('id="novas-medidas-agosto-title"')
    # Sete quadros desde 22/10/2026 (o das RE nº 4.143, 4.147 e 4.150 entrou acima do de 21/10). Os demais ids ficam nos meses.
    assert html.count("data-news-update-callout aria-labelledby=") == 7
    assert "ATUALIZAÇÃO" in html
    assert "RE nº 3.547/2026" in text
    assert "Resolução-RE nº 3.547/2026" in html
    assert "de 09/09/2026 e publicada no DOU em 11/09/2026" in html
    assert "Medidas de julho a outubro mostram" in html
    assert "Medidas de julho a setembro" not in html
    assert "Medidas de julho e agosto" not in html
    assert f'<time datetime="{UPDATED}">{UPDATED_DAY}</time> às {UPDATED_CLOCK}' in html
    assert f'<time datetime="{PUBLISHED}">05/07/2026</time> às 18h00' in html
    # Histórico de agosto e julho preservado.
    for term in ("12/08 — saneantes sem registro", "14/08 — Chá Sarapião", "Fiscalização de julho amplia", "Chlorohex 2,0%"):
        assert term in html
    for forbidden in ("Ozempic", "Mounjaro", "150 g", "150 mg", "href="):
        assert forbidden not in september


def _h3_parts(section):
    parts = re.split(r"(?=<h3>)", section)
    return parts[1:]


def test_latest_callout_keeps_each_resolution_bound_to_its_own_products_and_measures():
    html = _page_html()
    callout = _latest_callout(html)
    items = [_text(item) for item in _h3_parts(callout)]

    assert len(items) == 4
    t36, moringa, notshake, aloe = (_text(item) for item in items)

    assert "T36 — RE nº 3.626/2026" in t36
    assert "proíbe o armazenamento, a comercialização, a distribuição, a exportação, a importação, a propaganda, o transporte e o uso" in t36
    assert "não determina recolhimento nem apreensão" in t36

    assert "Moringa da Paz — RE nº 3.628/2026" in moringa
    assert "determina a apreensão e proíbe a fabricação, a comercialização, a distribuição, a propaganda e o uso" in moringa
    assert "não determina recolhimento" in moringa

    assert "NotShake Protein — RE nº 3.629/2026" in notshake
    assert "determina o recolhimento e proíbe a fabricação, a comercialização, a distribuição, a propaganda e o uso" in notshake
    assert "apreensão" not in notshake

    assert "Aloe Care — RE nº 3.634/2026" in aloe
    assert "determina o recolhimento e proíbe a fabricação, a distribuição, a comercialização, a propaganda e o uso" in aloe
    assert "divulgação" not in aloe
    assert "RE nº 3.629/2026" not in aloe

    for item, own_re in zip(items, ("3.626", "3.628", "3.629", "3.634")):
        assert all(other not in item for other in ("3.626", "3.628", "3.629", "3.634") if other != own_re)


def test_four_new_body_subsections_preserve_exact_products_measures_and_negative_limits():
    html = _page_html()
    section = _latest_section(html)
    t36 = _text(_subsection(section, "T36 — RE nº 3.626/2026", "Moringa da Paz — RE nº 3.628/2026"))
    moringa = _text(_subsection(section, "Moringa da Paz — RE nº 3.628/2026", "NotShake Protein — RE nº 3.629/2026"))
    notshake = _text(_subsection(section, "NotShake Protein — RE nº 3.629/2026", "Aloe Care — RE nº 3.634/2026"))
    aloe = _text(_subsection(section, "Aloe Care — RE nº 3.634/2026"))

    assert "todos os lotes" in t36
    assert "empresa não foi identificada" in t36 and "CNPJ é desconhecido" in t36
    assert "medicamento sem registro sanitário concedido pela Agência" in t36
    for measure in ("armazenamento", "comercialização", "distribuição", "exportação", "importação", "propaganda", "transporte", "uso"):
        assert measure in t36
    assert "não determina recolhimento nem apreensão" in t36
    assert "determina o recolhimento" not in t36 and "determina a apreensão" not in t36
    assert "Go Pharma" not in section and "3.480" not in section

    # Retificação publicada no DOU de 02/10/2026: nova denominação do primeiro produto, sem nova medida.
    assert "Cápsula Nespresso de Moringa Oleífera</strong>" not in moringa
    assert "retificação publicada no Diário Oficial da União de 02/10/2026" in moringa
    assert "não cria nova medida nem altera a empresa, os demais produtos, o alcance ou o tipo de medida" in moringa
    for product in (
        "Cápsulas de Moringa Oleífera, marca Moringa da Paz, compatíveis com máquinas Nespresso®",
        "Pó Orgânico de Moringa Oleífera",
        "Cápsulas com Pó Orgânico de Moringa Oleífera",
        "Chá Orgânico de Moringa Oleífera",
    ):
        assert product in moringa
    assert "apreensão e proíbe a fabricação, a comercialização, a distribuição, a propaganda e o uso" in moringa
    assert "não determina recolhimento" in moringa
    assert "efeitos genotóxicos e hepatotóxicos não puderam ser afastados" in moringa
    assert "não equivalem a afirmar que a moringa cause câncer ou dano hepático" in moringa

    for product in (
        "NotShake Protein Morango com Tâmara",
        "NotShake Protein Baunilha com Coco",
        "NotShake Protein Chocolate",
        "NotShake Protein Café Caramelo",
    ):
        assert product in notshake
    assert "NotCo Brasil Distribuição e Comércio de Produtos Alimentícios Ltda." in notshake
    assert "determina o recolhimento e proíbe a fabricação, a comercialização, a distribuição, a propaganda e o uso" in notshake
    for reason in ("suco concentrado de repolho", "recategorização inadequada", "ausência de notificação como suplemento", "insuficiência dos estudos", "zero lactose"):
        assert reason in notshake
    assert "apreensão" not in notshake and "3.634" not in notshake

    assert "Aloe Care – Cranberry Flavored Aloe Vera Gel" in aloe
    assert "Biodis Industrial Ltda." in aloe
    assert "União Vegetal Agroindustrial Ltda." in aloe
    assert "retificação publicada no DOU em 09/10/2026" in aloe
    assert "não cria outra medida nem altera o produto, os lotes ou as proibições" in aloe
    assert "10.536.977/0001-81" in aloe
    assert "determina o recolhimento e proíbe a fabricação, a distribuição, a comercialização, a propaganda e o uso" in aloe
    assert "a propaganda, a divulgação e o uso" not in aloe
    for reason in ("sem prévia avaliação de segurança e autorização de uso", "língua estrangeira", "alegações de saúde ou terapêuticas não autorizadas"):
        assert reason in aloe
    assert "não representa proibição genérica de todo uso de Aloe vera" in aloe
    assert "3.629" not in aloe


def test_each_september_measure_is_attributed_only_to_its_product():
    html = _page_html()
    items = [_text(item) for item in _h3_parts(_september_callout(html))]
    assert len(items) == 4
    dobutamina, pharmes, soll, berberina = items

    assert "Hypofarma" in dobutamina and "dobutamina 12,5 mg/mL" in dobutamina
    assert all(lote in dobutamina for lote in DOBUTAMINA_LOTES)
    assert "recolhimento e suspensão da comercialização, da distribuição e do uso" in dobutamina
    assert "restrita aos lotes identificados" in dobutamina
    assert "todos os lotes" not in dobutamina and "apreensão" not in dobutamina

    assert "Pharmes" in pharmes and "Lupatini e Pinheiro Instituto de Manipulação Ltda." in pharmes
    assert "suspensão da propaganda" in pharmes
    assert "O ato não determina recolhimento, apreensão ou proibição de fabricação desses produtos." in pharmes

    assert "Soll*Q-75" in soll and "Método Quantumbio" in soll
    assert "apreensão de todos os lotes e proibição de comercialização, distribuição, fabricação, propaganda e uso" in soll
    assert "recolhimento" not in soll and "importação" not in soll

    assert "berberina sem registro, notificação ou cadastro" in berberina
    assert "apreensão de todos os lotes e proibição de comercialização, distribuição, fabricação, importação, propaganda e uso" in berberina
    assert "recolhimento" not in berberina

    assert all(lote not in _text(item) for item in items[1:] for lote in DOBUTAMINA_LOTES)


def test_september_body_details_and_numbering_note():
    html = _page_html()
    section = _text(_september_section(html))

    assert "Resolução-RE nº 3.547, de 09/09/2026" in section
    assert "11/09/2026" in section
    assert "A medida é restrita aos lotes identificados." in section
    assert "O ato não determina recolhimento, apreensão ou proibição de fabricação desses produtos." in section
    assert "Nattubras Produtos Natturais Ltda. também ficou proibida de fabricar o produto" in section
    assert "quaisquer pessoas físicas ou jurídicas, ou veículos de comunicação" in section
    # 3.457 só aparece na nota neutra de divergência; a referência normativa é 3.547.
    assert html.count("3.457") == 1
    assert "A notícia institucional da Anvisa sobre essas medidas traz a numeração 3.457/2026, enquanto o ato normativo publicado no DOU corresponde à RE nº 3.547/2026." in section
    for forbidden in ("Ozempic", "150 g", "150 mg"):
        assert forbidden not in section
    for term in ("Expert Berlian", "Nutra Senior", "3.540", "3.541"):
        assert term not in html


def test_article_is_unique_and_current_in_the_listing_and_sitemap():
    news_index = NEWS_INDEX_PATH.read_text(encoding="utf-8")
    sitemap = SITEMAP_PATH.read_text(encoding="utf-8")

    assert news_index.count('href="/noticias/anvisa-suspende-medicamento-proibe-produtos-irregulares/"') == 1
    assert f'data-updated="{UPDATED}"' in news_index
    assert "13/10/2026 • 09h06" in news_index
    article = _page_html()
    # O card ficou em duas frases. O histórico dessas medidas continua na matéria.
    assert "todos os produtos da marca United Labz" in article
    assert "Mounjcaps" in article and "Enhertu" in article
    assert "Higia Pharmaceutical" in article and "Tha &amp; Thi" in article
    assert "RE nº 3.436" in article and "3.743/2026" in article
    assert "As RE nº 3.946 e 3.947 foram assinadas em 02/10/2026" in article
    assert "União Vegetal Agroindustrial Ltda." in article
    for term in ("Hytamicina", "Pangastri", "Gripinew", "Lipo Top Gold", "Anagalis", "RE 3.440/2026", "RE 3.479/2026",
                 "RE 3.480/2026", "RE 3.546/2026", "RE 3.738/2026"):
        assert term in _consolidated_card(news_index).split('data-keywords="', 1)[1].split('"', 1)[0]
    assert "Publicações da Anvisa de 01 a 28/09" not in news_index
    assert "Publicações da Anvisa de 21 a 28/09" not in news_index
    assert "Publicações da Anvisa de 21 e 25/09" not in news_index
    cards = re.findall(r'(<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>)', news_index, re.DOTALL)
    # 15/10/2026, 17h44: o quadro da RE nº 4.035/2026 mantém o card na 1ª posição, com o resumo curto.
    # 16/10/2026, 20h06: o card do CNES 10/2026 (publicação mais recente) passa à frente; o consolidado fica em 2º.
    # 17/10/2026, 09h50: o card do esclarecimento do Farmácia Popular entra na 1ª posição da listagem; os demais descem uma. O consolidado fica em 3º.
    # 20/10/2026, 10h12: o quadro das RE nº 4.090 e 4.105/2026 leva o consolidado de volta à 1ª posição, com o mesmo resumo curto.
    # 20/10/2026, 13h00: o card do SNCR, atualizado no lote 2, passa à frente; o consolidado fica em 2º.
    # 21/10/2026, 17h45: a RE nº 4.140/2026 e a correção da RE nº 3.159/2026 devolvem o consolidado à 1ª posição.
    # 22/10/2026, 22h40: as RE nº 4.143, 4.147 e 4.150/2026 mantêm o consolidado na 1ª posição, com resumo novo.
    summary = ("O DOU de 22/10/2026 publica a RE nº 4.143/2026, que proíbe dois produtos Accu-Chek Active identifica"
               "dos no anexo, em caso enquadrado como falsificação; a RE nº 4.147/2026, sobre o lote 11-2025 do NAC "
               "(N-acetil L-cisteína) Lauton; e a RE nº 4.150/2026, que determina, por 90 dias, a interdição cautelar do lote 25D0808 do Fauldleuco, da Libbs.")
    assert 'anvisa-suspende-medicamento-proibe-produtos-irregulares' in cards[0]
    assert "news-card-compact" in cards[0].split(">", 1)[0]
    assert f"{UPDATED_DAY} • {UPDATED_CLOCK}" in cards[0]
    assert "09h06" not in cards[0]
    assert f'data-summary="{summary}"' in cards[0]
    assert f"<p class=\"text-slate-500 text-sm leading-relaxed mb-4\">{summary}</p>" in cards[0]
    # Números e lotes do resumo de 13/10/2026 saíram do texto do card e seguem na busca pelas palavras-chave.
    keywords = cards[0].split('data-keywords="', 1)[1].split('"', 1)[0]
    for term in ("RE 3.989/2026", "RE 4.000/2026", "RE 4.001/2026", "RE 4.002/2026", "RE 4.009/2026", "RE 4.028/2026",
                 "HXTZ251015", "NDC 46785-162-03", "P07725A", "Xeomin", "cloreto de sódio", "insumos farmacêuticos"):
        assert term in keywords, term
        assert term not in summary, term
    # Empresas, marcas e sítios do novo ato entram só como texto pesquisável, sem link.
    for term in ("RE 4.035/2026", "14/10/2026", "Farmácia Global de Peptídeos do Brasil", "Cris Barden Naturopatia",
                 "Liberty Pharma", "ZPH Contabilidade", "zyntrashop.site", "peptideosdobrasil.com.br",
                 "oxygenkwpharmabrasil.com", "zphcstore.com.br"):
        assert term in keywords, term
    # 19/10/2026: atos, produtos e lotes do novo quadro entram só nas palavras-chave; o resumo não muda.
    for term in ("RE 4.090/2026", "RE 4.105/2026", "19/10/2026", "Dysport", "Keytruda", "pembrolizumabe",
                 "025155", "Z005197", "Z012354"):
        assert term in keywords, term
        assert term not in summary, term
    assert "As RE nº 3.946 e 3.947/2026 foram publicadas no DOU de 06/10/2026" not in cards[0]
    assert "União Vegetal Agroindustrial Ltda. como fabricante do Aloe Care" not in cards[0]
    assert 'href="http' not in cards[0]
    assert sitemap.count(f"<loc>{URL}</loc>") == 1
    assert f"<loc>{URL}</loc>\n    <lastmod>{UPDATED[:10]}</lastmod>" in sitemap


def test_re_3717_callout_keeps_each_measure_inside_its_own_item():
    html = _page_html()
    items = [_text(item) for item in _h3_parts(_re3717_callout(html))]

    assert len(items) == 5
    phesgo, dysport, queen, malheiro, cannabis = items

    assert "Phesgo — lote B5011B05" in phesgo
    assert "fabricação 06/2025" in phesgo
    assert "33.009.945/0001-23" in phesgo
    assert "determina a apreensão e proíbe o armazenamento, a comercialização, a distribuição, a exportação, a importação e o uso" in phesgo
    assert "não determina recolhimento" in phesgo
    assert "Dysport" not in phesgo and "Queen" not in phesgo and "Malheiro" not in phesgo and "cannabis" not in phesgo

    assert "lotes P08191, P08192 e P22368" in dysport
    assert "07.718.721/0001-80" in dysport
    assert "P08191" in dysport and "04/2029" in dysport
    assert "P08192" in dysport and "05/2029" in dysport
    assert "P22368" in dysport and "02/2029" in dysport
    assert "determina a apreensão e proíbe a comercialização, a distribuição e o uso" in dysport
    assert "Não há, nesse item, proibição de armazenamento, exportação, importação ou propaganda, nem determinação de recolhimento." in dysport
    assert "Phesgo" not in dysport and "Queen" not in dysport and "Malheiro" not in dysport and "cannabis" not in dysport

    assert "48.822.189/0001-24" in queen
    assert "suspensão da propaganda" in queen
    assert "não determina recolhimento, apreensão nem proibição de fabricação ou comercialização" in queen
    assert "Phesgo" not in queen and "Dysport" not in queen and "Malheiro" not in queen and "cannabis" not in queen

    assert "47.843.321/0001-11" in malheiro
    assert "suspensão da propaganda de todos os manipulados" in malheiro
    assert "não determina recolhimento, apreensão, proibição de fabricação nem interdição do estabelecimento" in malheiro
    assert "comercialização" not in malheiro
    assert "Phesgo" not in malheiro and "Dysport" not in malheiro and "Queen" not in malheiro and "cannabis" not in malheiro

    assert "proíbe a comercialização e a propaganda" in cannabis
    assert "não determina apreensão, recolhimento nem proibição de uso" in cannabis
    assert "Phesgo" not in cannabis and "Dysport" not in cannabis and "Queen" not in cannabis and "Malheiro" not in cannabis
    assert "href=" not in _re3717_callout(html)


def test_re_3717_body_uses_the_dou_text_and_does_not_mix_measures():
    html = _page_html()
    section = _re3717_section(html)
    phesgo = _text(_subsection(section, "Phesgo — lote B5011B05 com fabricação 06/2025", "Dysport — lotes P08191, P08192 e P22368"))
    dysport = _text(_subsection(section, "Dysport — lotes P08191, P08192 e P22368", "Queen Pharma Aesthetic — suspensão de propaganda"))
    queen = _text(_subsection(section, "Queen Pharma Aesthetic — suspensão de propaganda", "Farmácia Malheiro — suspensão de propaganda"))
    malheiro = _text(_subsection(section, "Farmácia Malheiro — suspensão de propaganda", "Cannabis — comercialização e propaganda proibidas"))
    cannabis = _text(_subsection(section, "Cannabis — comercialização e propaganda proibidas"))

    assert "de 18/09/2026" in _text(section)
    assert "21/09/2026, edição 178, seção 1, página 183" in _text(section)
    assert "33.009.945/0001-23" in phesgo
    assert "CNPJ 3.009.945/0001-23" not in section and "CNPJ <strong>3.009.945/0001-23" not in section
    assert "quaisquer pessoas físicas ou jurídicas" in phesgo
    assert "não determina recolhimento do Phesgo" in phesgo
    for lot, validity in (("P08191", "04/2029"), ("P08192", "05/2029"), ("P22368", "02/2029")):
        assert lot in dysport and validity in dysport
    assert "Não há, nesse item, proibição de armazenamento, exportação, importação ou propaganda" in dysport
    for product in (
        "lidocaína 2% sem vasoconstritor",
        "Desinflame",
        "Morusil Slim+",
        "Hepato Detox",
        "Metabolismo Power",
        "Muscledefin",
        "glicose 75% com lidocaína",
        "hialuronidase 3000 UTR",
        "mescla capilar",
        "Strill Repair",
        "Face Body Firm",
        "Boom de Colágeno",
        "Cellu Slim",
        "Soft Lipo",
        "Slim Flash/Gordura Light",
        "Lipo Slim",
        "Liposolve Intensive",
        "gordura localizada descafeinada",
        "Skinbooster",
        "Papada Slim",
        "Melasma",
    ):
        assert product in queen
    assert "@queenpharmaaesthetic" in queen
    assert "item 5.14" in queen and "RDC nº 67/2007" in queen
    assert "não determina recolhimento, apreensão nem proibição de fabricação ou comercialização" in queen
    assert "todos os manipulados" in malheiro
    assert "item 5.14" in malheiro
    assert "não determina recolhimento, apreensão, proibição de fabricação nem interdição do estabelecimento" in malheiro
    assert "artigos 2º, 12 e 59 da Lei nº 6.360/1976" in cannabis
    assert "@medicinatural.sac" in cannabis
    assert "não determina apreensão, recolhimento nem proibição de uso" in cannabis
    assert "não representa proibição genérica de produtos de cannabis" in cannabis
    assert "href=" not in section


def test_new_measures_of_21_and_25_september_keep_their_own_scope():
    html = _page_html()
    body_start = html.index("<h2>25 de setembro: RE nº 3.751/2026")
    body = _text(html[body_start:html.index("<h2>21 de setembro: RE nº 3.717/2026", body_start)])
    scope = html[html.index("<h2>28 de setembro: RE nº 3.764/2026"):html.index("<h2>16 de setembro: quatro resoluções")]

    def chunk(start, end):
        begin = html.index(start)
        return _text(html[begin:html.index(end, begin)])

    ocrevus = chunk("<h3>LAF MED", "<h3>ICT Farmacêutica")
    ict = chunk("<h3>ICT Farmacêutica", "<h2>23 de setembro: RE nº 3.738/2026")
    eleve = chunk("<h3>Eleve — RE nº 3.712/2026", "<h3>D Casa")
    dcasa = chunk("<h3>D Casa", "<h3>Smart GR")
    smart = chunk("<h3>Smart GR", "<h2>21 de setembro: RE nº 3.717/2026")

    assert "RE nº 3.751/2026" in body
    assert "LAF MED" in ocrevus and "H7953B14" in ocrevus and "H7953B06" in ocrevus
    assert "se aplicam a quaisquer medicamentos" in ocrevus
    assert "não é uma proibição geral do Ocrevus" in ocrevus
    assert "restrita aos dois lotes" not in ocrevus
    assert "todos os medicamentos manipulados estéreis, em todos os lotes" in ict
    assert "suspensão da comercialização, da distribuição, da manipulação, da propaganda e do uso" in ict
    assert "produzidos" not in ict and "refere-se ao recolhimento" not in ict
    assert "RE nº 3.712/2026" in eleve and "Gama Suplementos Alimentares" in eleve
    assert "RE nº 3.714/2026" in dcasa and "Fórmula Química" in dcasa
    assert "RE nº 3.714/2026" in smart
    assert "A publicação da Anvisa identifica esses três produtos da Klug como atingidos pela medida." in smart
    assert "A publicação da Anvisa identifica esses três produtos da Klug como atingidos pela medida." in body
    assert "demais produtos da Klug" not in scope and "demais produtos da Klug" not in body
    assert "href=" not in scope

    # Limites de alcance e de atribuição informados na revisão.
    assert "falsific" not in ocrevus.casefold()
    assert "falsific" not in _text(html[body_start:html.index("<h3>ICT Farmacêutica", body_start)]).casefold()
    laf_body = _text(html[body_start:html.index("<h3>ICT Farmacêutica", body_start)])
    ict_body = _text(html[html.index("<h3>ICT Farmacêutica", body_start):html.index("<h2>23 de setembro: RE nº 3.738/2026", body_start)])
    assert "Resolução-RE nº 3.751, de 24/09/2026, publicada no DOU em 25/09/2026" in body
    assert "proibição de armazenamento, comercialização, distribuição, exportação, importação, propaganda e transporte" in laf_body
    assert "o item não determina recolhimento" in laf_body
    assert "se aplicam a quaisquer medicamentos" in laf_body
    assert "não é uma proibição geral do Ocrevus" in laf_body
    assert "art. 7º, inciso XV, da Lei nº 9.782/1999" in laf_body
    assert "não se estende aos demais lotes" not in laf_body
    assert "todos os medicamentos manipulados estéreis, em todos os lotes" in ict_body
    assert "suspensão da comercialização, da distribuição, da manipulação, da propaganda e do uso" in ict_body
    assert "o item não determina apreensão" in ict_body
    assert "correspondem à inspeção de boas práticas de manipulação" in ict_body
    assert "não delimitam a produção nem os lotes alcançados" in ict_body
    assert "art. 7º da Lei nº 6.360/1976" in ict_body
    assert "produzidos entre" not in ict_body and "se refere ao recolhimento" not in ict_body
    assert "o alcance da suspensão deve ser conferido no ato publicado" not in body
    assert "Smart GR" not in dcasa and "saneantes" not in smart
    # RE nº 3.738/2026 (DOU de 23/09) tem seção própria desde a Fase 1F; não aparece nos itens nem nas seções
    # das RE nº 3.751, 3.712 e 3.714/2026.
    assert all("3.738" not in part for part in (ocrevus, ict, eleve, dcasa, smart, laf_body, ict_body))
    assert "3.738" not in _text(html[html.index("<h2>21 de setembro: RE nº 3.712"):html.index("<h2>21 de setembro: RE nº 3.717/2026")])
    assert "CNPJ" not in dcasa and "CNPJ" not in _text(html[html.index("<h3>D Casa"):html.index("<h3>Smart GR")])
    assert "href=" not in html[body_start:html.index("<h2>21 de setembro: RE nº 3.717/2026", body_start)]


def test_re_3764_and_re_3743_keep_suspension_and_revocation_apart():
    html = _page_html()
    reach_start = html.index("<h2>28 de setembro: RE nº 3.764/2026")
    reach = _text(html[reach_start:html.index("<h2>25 de setembro: RE nº 3.751/2026", reach_start)])
    higia_start = html.index("<h2>23 de setembro: RE nº 3.743/2026")
    higia = _text(html[higia_start:html.index("<h2>21 de setembro: RE nº 3.712", higia_start)])
    reach_item, higia_item = reach, higia

    # Os quadros curtos de setembro foram reunidos no detalhe de cada resolução.
    assert html.count("data-news-update-callout aria-labelledby=") == 7
    assert "publicações de 01, 21, 23, 25 e 28/09/2026" in html
    assert "As RE nº 3.436, 3.718 e 3.743/2026 revogam, cada uma, uma medida anterior referente a uma empresa" in html
    # Ordem cronológica das seções: 28/09, 25/09, 23/09, 21/09.
    assert reach_start < html.index("<h2>25 de setembro: RE nº 3.751/2026") < higia_start
    assert higia_start < html.index("<h2>21 de setembro: RE nº 3.712")

    # RE nº 3.764/2026 (24/09, DOU 28/09): suspensão dirigida à Reach Latam.
    assert "Reach Latam" in reach_item
    assert "suspensão de armazenamento, comercialização, distribuição, importação, propaganda e transporte" in reach_item
    assert "não representa proibição geral da tirzepatida" in reach_item
    assert "Resolução-RE nº 3.764, de 24/09/2026, publicada no DOU em 28/09/2026" in reach
    assert "Reach Latam Consultoria e Comércio Exterior Ltda." in reach and "24.662.773/0001-00" in reach
    assert "todos os produtos sujeitos a controle especial, incluindo tirzepatida" in reach
    assert "todos os lotes" in reach and "insumo farmacêutico" in reach
    assert "suspensão de armazenamento, comercialização, distribuição, importação, propaganda e transporte" in reach
    assert "Boas Práticas de Distribuição, Armazenamento, Importação e Controle de Insumos Farmacêuticos" in reach
    assert "identidade, segurança, controle e rastreabilidade" in reach
    assert "não representa proibição geral da tirzepatida nem medida contra a manipulação em geral" in reach
    assert "o ato não determina recolhimento nem apreensão" in reach
    for wrong in ("fabricação", "exportação", "uso,", " uso ", "proíbe", "proibição de", "determina o recolhimento", "determina a apreensão"):
        assert wrong not in reach_item and wrong not in reach.replace("proibição geral", ""), wrong

    # RE nº 3.743/2026 (22/09, DOU 23/09): revogação da medida nº 2 da RE nº 939/2026, com as restrições da motivação.
    assert "Higia Pharmaceutical" in higia_item
    assert "medida preventiva nº 2" in higia_item and "939" in higia_item
    assert "Satisfatória Com Restrições" in higia_item and "estudo complementar de validações" in higia_item
    assert "Resolução-RE nº 3.743, de 22/09/2026, publicada no DOU em 23/09/2026" in higia
    assert "medida preventiva nº 2 do anexo da Resolução-RE nº 939, de 12/03/2026, publicada no DOU em 13/03/2026" in higia
    assert "Higia Pharmaceutical Limitada" in higia and "57.022.608/0001-34" in higia
    assert "apreensão, o recolhimento e a suspensão de comercialização, manipulação, propaganda e uso" in higia
    assert "de 08 a 09/09/2026" in higia and "Satisfatória Com Restrições" in higia
    assert "resultados do estudo complementar de validações" in higia and "desinterdição" in higia
    assert "não informa que essa renovação já tenha ocorrido" in higia
    assert "A revogação alcança apenas a medida nº 2 da RE nº 939/2026" in higia
    assert "Não equivale à manutenção da medida anterior nem a uma liberação sem condições" in higia
    assert "não se estende à outra medida do mesmo ato nem a outras empresas" in higia
    for wrong in ("El Elyon", "liberação total", "licença renovada", "teve a licença renovada", "mantém a suspensão"):
        assert wrong not in higia and wrong not in higia_item
    assert "href=" not in html[reach_start:html.index("<h2>25 de setembro", reach_start)]
    assert "href=" not in html[higia_start:html.index("<h2>21 de setembro: RE nº 3.712", higia_start)]


def test_re_3718_and_re_3436_revoke_only_their_own_items():
    html = _page_html()
    thathi_start = html.index("<h2>21 de setembro: RE nº 3.718/2026")
    thathi = _text(html[thathi_start:html.index("<h2>16 de setembro: quatro resoluções", thathi_start)])
    terapeutica_start = html.index("<h2>1º de setembro: RE nº 3.436/2026")
    terapeutica_end = html.index("Os atos constam de publicações de 01, 21, 23, 25 e 28/09/2026", terapeutica_start)
    terapeutica = _text(html[terapeutica_start:terapeutica_end])
    thathi_item, terapeutica_item = thathi, terapeutica

    assert html.count("data-news-update-callout aria-labelledby=") == 7
    assert "publicações de 01, 21, 23, 25 e 28/09/2026" in html
    assert "As RE nº 3.436, 3.718 e 3.743/2026 revogam, cada uma, uma medida anterior referente a uma empresa" in html
    # Seções por data de publicação; no dia 21/09, a revogação vem depois das medidas preventivas.
    assert html.index("<h2>21 de setembro: RE nº 3.717/2026") < thathi_start < html.index("<h2>16 de setembro")
    assert html.index("<h2>Setembro: RE nº 3.547/2026") < terapeutica_start < html.index("<h2>Agosto amplia")

    # RE nº 3.718/2026 (18/09, DOU 21/09): só a medida nº 2 da RE nº 3.357/2026; proibição revogada.
    assert "Tha &amp; Thi" in thathi_item
    assert "medida preventiva nº 2" in thathi_item and "3.357" in thathi_item
    assert "apreensão e a proibição de comercialização, manipulação, propaganda e uso" in thathi_item
    assert "o art. 1º revoga apenas a medida nº 2, referente à Tha &amp; Thi" in thathi_item
    assert "Resolução-RE nº 3.718, de 18/09/2026, publicada no DOU em 21/09/2026" in thathi
    assert "medida preventiva nº 2 do anexo da Resolução-RE nº 3.357, de 26/08/2026, publicada no DOU em 27/08/2026" in thathi
    assert "06.177.615/0001-74" in thathi and "preparações magistrais estéreis" in thathi
    assert "apreensão e a proibição de comercialização, manipulação, propaganda e uso" in thathi
    assert "AFE vigente para a manipulação de produtos estéreis" in thathi
    assert "o ato não concede nova autorização" in thathi
    assert "item 5.10 da RDC nº 67/2007" in thathi
    assert "o art. 1º revoga apenas a medida nº 2, referente à Tha &amp; Thi" in thathi
    assert "não equivale a uma certificação de toda a produção da empresa" in thathi
    for wrong in ("suspensão", "distribuição", "recolhimento", "estudo complementar", "Satisfatória", "concede AFE", "nova AFE"):
        assert wrong not in thathi_item and wrong not in thathi, wrong

    # RE nº 3.436/2026 (28/08, DOU 01/09): só a medida nº 3 da RE nº 1.380/2026; suspensão revogada.
    assert "Terapêutica" in terapeutica_item
    assert "medida preventiva nº 3" in terapeutica_item and "1.380" in terapeutica_item
    assert "apreensão e a suspensão de comercialização, distribuição, manipulação, propaganda e uso" in terapeutica_item
    assert "Resolução-RE nº 3.436, de 28/08/2026, publicada no DOU em 01/09/2026" in terapeutica
    assert "medida preventiva nº 3 do anexo da Resolução-RE nº 1.380, de 07/04/2026, publicada no DOU em 08/04/2026" in terapeutica
    assert "47.545.371/0001-12" in terapeutica and "todos os medicamentos manipulados estéreis" in terapeutica
    assert "apreensão e a suspensão de comercialização, distribuição, manipulação, propaganda e uso" in terapeutica
    assert "Vigilância Sanitária de São José dos Campos" in terapeutica and "04/08/2026" in terapeutica
    assert "não se estende às demais medidas do mesmo ato" in terapeutica
    assert "atribuída pelo ato à fiscalização municipal" in terapeutica
    # O anexo da RE nº 3.436 não lista recolhimento: o texto não o acrescenta nem conclui que ele permanece.
    for wrong in ("recolhimento", "proibição de", "AFE", "estudo complementar", "Satisfatória", "denúncia"):
        assert wrong not in terapeutica_item and wrong not in terapeutica, wrong
    assert "href=" not in html[thathi_start:html.index("<h2>16 de setembro", thathi_start)]
    assert "href=" not in html[terapeutica_start:terapeutica_end]


def test_september_measures_of_re_3440_3479_3480_3546_and_3738_keep_their_own_scope():
    html = _page_html()

    def section(start, end):
        begin = html.index(start)
        return _text(html[begin:html.index(end, begin)])

    re3738 = section("<h2>23 de setembro: RE nº 3.738/2026", "<h2>23 de setembro: RE nº 3.743/2026")
    enhertu = section("<h3>Enhertu — lotes", "<h3>Mounjcaps — todos os lotes</h3>")
    mounjcaps = section("<h3>Mounjcaps — todos os lotes</h3>", "<h2>23 de setembro: RE nº 3.743/2026")
    tyg = section("<h2>11 de setembro: RE nº 3.546/2026", "<h2>8 de setembro: RE nº 3.479/2026")
    re3479 = section("<h2>8 de setembro: RE nº 3.479/2026", "<h2>8 de setembro: RE nº 3.480/2026")
    hytamicina = section("<h3>Hytamicina", "<h3>Pangastri")
    pangastri = section("<h3>Pangastri", "<h2>8 de setembro: RE nº 3.480/2026")
    re3480 = section("<h2>8 de setembro: RE nº 3.480/2026", "<h2>1º de setembro: RE nº 3.440/2026")
    mundial = section("<h3>Mundial Comércio de Encapsulados", "<h3>Produtos à base de retatrutida")
    gopharma = section("<h3>Produtos à base de retatrutida", "<h3>Anagalis")
    anagalis = section("<h3>Anagalis", "<h3>Dysport — lotes P08193")
    dysport = section("<h3>Dysport — lotes P08193", "<h3>Gripinew")
    gripinew = section("<h3>Gripinew", "<h2>1º de setembro: RE nº 3.440/2026")
    united = section("<h2>1º de setembro: RE nº 3.440/2026", "<h2>1º de setembro: RE nº 3.436/2026")

    # Ordem por data do DOU; no mesmo dia, medidas preventivas antes da revogação; RE nº 3.547 preservada antes da 3.546.
    positions = [html.index(h) for h in (
        "<h2>25 de setembro: RE nº 3.751/2026", "<h2>23 de setembro: RE nº 3.738/2026",
        "<h2>23 de setembro: RE nº 3.743/2026", "<h2>21 de setembro: RE nº 3.712",
        "<h2>Setembro: RE nº 3.547/2026", "<h2>11 de setembro: RE nº 3.546/2026",
        "<h2>8 de setembro: RE nº 3.479/2026", "<h2>8 de setembro: RE nº 3.480/2026",
        "<h2>1º de setembro: RE nº 3.440/2026", "<h2>1º de setembro: RE nº 3.436/2026", "<h2>Agosto amplia")]
    assert positions == sorted(positions)
    assert html.count("data-news-update-callout aria-labelledby=") == 7

    enhertu_item = _text(html[html.index("<h3>Enhertu"):html.index("<h3>Mounjcaps")])
    mounj_item = _text(html[html.index("<h3>Mounjcaps"):html.index("<h2>23 de setembro: RE nº 3.743")])
    assert "432221" in enhertu_item and "432844" in enhertu_item and "432862" in enhertu_item
    assert "não se refere ao Mounjaro" in mounj_item
    september = _text(_september_callout(html))
    assert len(_h3_parts(_september_callout(html))) == 4
    assert "RE nº 3.440/2026 (DOU de 01/09, marca United Labz)" in html
    assert "RE nº 3.479 e 3.480/2026 (DOU de 08/09)" in html
    assert "RE nº 3.546/2026 (DOU de 11/09, interdição cautelar de um lote do TYG)" in html
    assert "Eles não integram a RE nº 3.547/2026." in html

    # RE nº 3.738/2026: Enhertu falsificado e Mounjcaps, sem atribuição à detentora nem confusão com Mounjaro.
    assert "Resolução-RE nº 3.738, de 22/09/2026, publicada no DOU em 23/09/2026" in re3738
    assert "distintas da revogação referente à Higia" in re3738
    re3738_intro = re3738.split("Enhertu — lotes", 1)[0]
    assert "duas medidas preventivas referentes a produtos distintos, cada uma com a motivação e o alcance indicados em seu item" in re3738_intro
    assert "em comum" not in re3738_intro and "sem empresa, produto ou fundamento" not in re3738_intro
    assert all(lote in enhertu for lote in ("432221", "432844", "432862"))
    assert "empresa responsável não identificada" in enhertu
    assert "Daiichi Sankyo Brasil Farmacêutica Ltda." in enhertu and "60.874.187/0001-84" in enhertu
    assert "proíbe o armazenamento, a comercialização, a distribuição, o transporte e o uso" in enhertu
    assert "A falsificação não é atribuída à detentora do registro" in enhertu
    assert "não alcança os demais lotes do Enhertu" in enhertu
    for wrong in ("fabricação", "propaganda", "importação", "recolhimento"):
        assert wrong not in enhertu, wrong
    assert "todos os lotes" in mounjcaps and "empresa desconhecida" in mounjcaps
    assert "“Mounjcaps Natural”" in mounjcaps
    assert "armazenamento, comercialização, distribuição, fabricação, propaganda, transporte e uso" in mounjcaps
    assert "não se refere ao Mounjaro" in mounjcaps
    for wrong in ("importação", "recolhimento"):
        assert wrong not in mounjcaps, wrong

    # RE nº 3.546/2026: interdição cautelar de um lote, por suspeita, com 90 dias.
    assert "Resolução-RE nº 3.546, de 09/09/2026, publicada no DOU em 11/09/2026" in tyg
    assert "2604940" in tyg and "TYG 50 mg" in tyg and "60.665.981/0001-18" in tyg
    assert "interdição cautelar" in tyg and "suspeita" in tyg and "90 dias" in tyg
    assert "a motivação registra suspeita, não desvio confirmado" in tyg
    assert "O anexo determina interdição cautelar e não lista recolhimento como ação adicional" in tyg
    assert "Enquanto a interdição estiver vigente, o lote não pode ser utilizado ou comercializado" in tyg
    assert "distinta da RE nº 3.547/2026" in tyg
    # A interdição não é apresentada como liberação: nenhuma negativa de "proibição" nem permissão de uso/venda.
    assert "não determina recolhimento nem proibição" not in tyg
    for wrong in ("pode ser utilizado e", "pode ser comercializado e", "pode ser utilizado ou comercializado durante",
                  "liberad", "permitid"):
        assert wrong not in tyg, wrong
    assert tyg.count("pode ser utilizado ou comercializado") == 1
    assert "não pode ser utilizado ou comercializado" in tyg
    # Fora da negativa exata do recolhimento, nenhuma outra ação é atribuída ao lote.
    tyg_rest = tyg.replace("não lista recolhimento como ação adicional", "")
    for wrong in ("recolhimento", "proibição", "proíbe", "apreensão", "suspensão de", "confirmação de desvio"):
        assert wrong not in tyg_rest, wrong
    assert "3.456" not in html

    # RE nº 3.479/2026: Hytamicina (desvio confirmado) e Pangastri (recolhimento voluntário).
    assert "Resolução-RE nº 3.479, de 03/09/2026, publicada no DOU em 08/09/2026" in re3479
    assert all(lote in hytamicina for lote in ("25091367", "25111733", "25081181"))
    assert "suspensão de comercialização, distribuição, fabricação e uso" in hytamicina
    assert "confirmação de desvio de qualidade" in hytamicina and "corpo estranho" in hytamicina
    for wrong in ("voluntário", "apreensão", "2610715"):
        assert wrong not in hytamicina, wrong
    assert "2610715" in pangastri and "recolhimento voluntário" in pangastri
    assert "suspensão de comercialização, distribuição e uso" in pangastri and "pedaço de vidro" in pangastri
    for wrong in ("fabricação", "confirmação", "25091367", "TYG"):
        assert wrong not in pangastri, wrong
    assert "não se estendem à produção das empresas" in re3479

    # RE nº 3.480/2026: cinco medidas sem operações trocadas entre itens.
    assert "Resolução-RE nº 3.480, de 03/09/2026" in re3480 and "DOU em 08/09/2026" in re3480
    re3480_intro = re3480.split("Mundial Comércio de Encapsulados", 1)[0]
    assert "adota cinco medidas preventivas, cada uma com os produtos, as ações e a motivação indicados em seu item" in re3480_intro
    assert "não compartilham" not in re3480_intro and "fundamento" not in re3480_intro
    for product in ("Lipo Top Gold", "Red Nature", "Mundial Caps BR (Lipo Bari)", "Mundial Caps Black (Lipo Top Extra Forte)"):
        assert product in mundial
    assert "56.137.545/0001-07" in mundial
    assert "proibição de comercialização, distribuição, fabricação, propaganda e uso" in mundial
    for wrong in ("importação", "armazenamento", "recolhimento"):
        assert wrong not in mundial, wrong
    assert "todos os produtos à base de retatrutida" in gopharma and "todos os produtos à base de tirzepatida" in gopharma
    assert "gopharma.shop" in gopharma
    assert all(name in gopharma for name in ("T.G. 15 mg", "Tirzec 15 mg", "Lipoless MD 15 mg", "Retatrutide"))
    assert "proibição de comercialização, distribuição, importação, propaganda e uso" in gopharma
    assert "não decide sobre medicamentos registrados" in gopharma
    for wrong in ("fabricação", "armazenamento", "Go Pharma"):
        assert wrong not in gopharma, wrong
    assert "suspensão da propaganda" in anagalis and "04.540.131/0001-12" in anagalis and "item 5.17.14" in anagalis
    assert "não suspende a atividade da farmácia" in anagalis
    anagalis_rest = anagalis.replace("nem determina recolhimento, apreensão ou proibição de manipulação", "")
    for wrong in ("recolhimento", "apreensão", "proibição", "suspensão de comercialização"):
        assert wrong not in anagalis_rest, wrong
    assert "P08193" in dysport and "06/2029" in dysport and "U14534" in dysport and "02/2029" in dysport
    assert "Beaufour Ipsen Farmacêutica Ltda." in dysport
    assert "proíbe a comercialização, a distribuição e o uso" in dysport
    assert "não se confundem com os três lotes de Dysport da RE nº 3.717/2026" in dysport
    assert "a falsificação não é atribuída à detentora do registro" in dysport
    for wrong in ("P08191", "P08192", "P22368", "armazenamento", "exportação", "importação", "propaganda"):
        assert wrong not in dysport, wrong
    re3717 = _text(_re3717_section(html))
    assert "P08193" not in re3717 and "U14534" not in re3717
    assert "OB2529" in gripinew and "0B2529" not in html
    assert "recolhimento voluntário" in gripinew
    assert "suspensão de comercialização, distribuição, exportação e uso" in gripinew
    assert "monitoramento contínuo da qualidade" in gripinew
    for wrong in ("fabricação", "apreensão"):
        assert wrong not in gripinew, wrong

    # RE nº 3.440/2026: toda a marca United Labz, sem extensão a outras marcas ou à revogação do mesmo dia.
    assert "Resolução-RE nº 3.440, de 31/08/2026, publicada no DOU em 01/09/2026" in united
    assert "todos os produtos da marca United Labz" in united
    assert "proíbe armazenamento, comercialização, distribuição, fabricação, importação, propaganda, transporte e uso" in united
    assert "não se estende a outras marcas" in united
    assert "distinta da revogação referente à Terapêutica" in united
    for wrong in ("recolhimento", "tirzepatida", "retatrutida"):
        assert wrong not in united, wrong

    # Sem links nas seções novas (nem para o endereço fiscalizado).
    assert "href=" not in html[html.index("<h2>23 de setembro: RE nº 3.738/2026"):html.index("<h2>23 de setembro: RE nº 3.743/2026")]
    assert "href=" not in html[html.index("<h2>11 de setembro: RE nº 3.546/2026"):html.index("<h2>1º de setembro: RE nº 3.436/2026")]
    assert "gopharma.shop/" not in html and "http://gopharma" not in html and "https://gopharma" not in html


def _october_19_callout(html):
    start = html.index('data-news-update-callout aria-labelledby="novas-medidas-19-outubro-title"')
    return html[start:html.index("</aside>", start)]


def test_october_19_callout_keeps_dysport_and_keytruda_lots_apart_without_links():
    html = _page_html()
    callout = _october_19_callout(html)
    items = [_text(item) for item in _items(callout)]

    # O quadro de 21/10/2026 ficou antes deste, que segue antes do de 14/10/2026.
    assert html.index("novas-medidas-21-outubro-title") < html.index("novas-medidas-19-outubro-title")
    assert html.index("novas-medidas-19-outubro-title") < html.index("novas-medidas-14-outubro-title")
    assert "Atualização: medidas publicadas no DOU em 19/10/2026" in callout
    assert "ATUALIZAÇÃO" in callout
    assert len(items) == 2
    dysport, keytruda = items

    assert dysport.startswith("Dysport, lote 025155, empresa desconhecida (RE nº 4.090/2026):")
    assert "apreensão e proibição de comercialização, distribuição e uso" in dysport
    assert "A empresa e o CNPJ são desconhecidos, expediente 0781120/26-9" in dysport
    assert "“DYSPORT (LOTE: 025155)”" in dysport and "sem indicar a apresentação" in dysport
    assert "Beaufour Ipsen Farmacêutica Ltda., CNPJ 07.718.721/0001-80, detentora do registro" in dysport
    assert "conclui que se trata de falsificação" in dysport
    assert "A falsificação não é atribuída à detentora do registro" in dysport
    # Sem apresentação inventada: o anexo do Dysport não traz dose, volume nem unidades.
    for invented in ("500 U", "300 U", " mg", " mL", "toxina botulínica"):
        assert invented not in dysport, invented
    # O código de barras citado na motivação (lote W26232) não vira outro lote alcançado.
    assert "W26232" not in callout

    assert keytruda.startswith(
        "Keytruda 100 mg/4 mL, lotes Z005197 e Z012354, empresa não identificada (RE nº 4.105/2026):")
    assert "apreensão e proibição de comercialização, distribuição e uso" in keytruda
    assert "A empresa não é identificada e o CNPJ é desconhecido, expediente 1057099/26-3" in keytruda
    assert "“KEYTRUDA (LOTES: Z005197, Z012354)”" in keytruda
    assert "a apresentação de 100 mg/4 mL consta da motivação" in keytruda
    assert "Merck Sharp &amp; Dohme Farmacêutica Ltda., detentora do registro" in keytruda
    # Classificação literal do ato: suspeita de falsificação, não lote falsificado.
    assert "“caracterizando suspeita de falsificação”" in keytruda
    assert "A suspeita não é atribuída à detentora do registro" in keytruda
    assert "falsificado" not in keytruda and "lotes falsificados" not in callout

    for item in items:
        assert "O ato não determina recolhimento e não alcança outros lotes nem a marca" in item
        assert "recolhimento" not in item.replace("não determina recolhimento", "")
    assert "Ipsen" not in keytruda and "Merck" not in dysport and "MSD" not in callout

    # Na v2 cada RE tem a sua lista; o parágrafo comum do quadro vem depois da última.
    closing = _text(callout.rsplit("</ul>", 1)[1])
    assert "As Resoluções-RE nº 4.090 e 4.105 foram assinadas em 15/10/2026" in closing
    assert "publicadas no DOU de 19/10/2026, edição 197, Seção 1, páginas 223 e 224, respectivamente" in closing
    assert "data em que entraram em vigor, conforme o art. 2º de cada ato" in closing
    assert closing.endswith("Cada medida vale só para os lotes indicados no próprio ato.")

    # Desde 20/10/2026, o quadro cita DOU, edição, seção e páginas no texto, sem link para as íntegras.
    assert re.findall(r"<a\b[^>]*>", callout) == []
    assert DOU_RE_4090_URL not in html and DOU_RE_4105_URL not in html and "Íntegra da Resolução" not in callout
    assert "http" not in _text(callout)
    for number in ("4.035", "3.717", "3.480"):
        assert number not in callout, number


def _october_14_callout(html):
    start = html.index('data-news-update-callout aria-labelledby="novas-medidas-14-outubro-title"')
    return html[start:html.index("</aside>", start)]


def test_october_14_callout_keeps_each_re_4035_item_apart_without_links():
    html = _page_html()
    callout = _october_14_callout(html)
    items = [_text(item) for item in _items(callout)]

    assert html.index("novas-medidas-14-outubro-title") < html.index("novas-medidas-13-outubro-title")
    assert "Atualização: medidas publicadas no DOU em 14/10/2026" in callout
    assert len(items) == 6
    zyntra, peptideos, barden, liberty, oxygen, zph = items
    for number, item in enumerate(items, start=1):
        assert f"(RE nº 4.035/2026, item {number})" in item
        assert "todos os lotes" in item
        assert "não determina recolhimento" in item or "nem recolhimento" in item

    assert "zyntrashop.site" in zyntra and "1032813/26-1" in zyntra and "campo do CNPJ está em branco" in zyntra
    assert "apreensão e proibição de comercialização, fabricação, importação, propaganda e uso" in zyntra
    assert "distribuição e divulgação, que não constam do campo de ações do anexo" in zyntra

    assert "Farmácia Global de Peptídeos do Brasil Ltda." in peptideos and "64.595.048/0001-72" in peptideos
    assert "1033824/26-1" in peptideos and "peptideosdobrasil.com.br" in peptideos
    assert "apreensão e proibição de comercialização, distribuição, fabricação, importação, propaganda e uso" in peptideos
    assert "produtos identificados na investigação" in peptideos and "veículos de comunicação" in peptideos
    assert "Não é proibição geral da tirzepatida" in peptideos

    assert "Cris Barden Naturopatia Ltda." in barden and "57.360.953/0001-88" in barden and "1045173/26-1" in barden
    assert "proibição de comercialização, distribuição, fabricação, importação, propaganda e uso" in barden
    assert "não determina apreensão nem recolhimento" in barden
    assert "apreensão" not in barden.replace("não determina apreensão", "")
    for product in ("Infantil de 1 a 5 anos", "Kit Detox Desparasitação", "Kit Carvão Pulverizado da Casca do Coco",
                    "Carvão Ativado Vegetal da Casca do Coco Premium 120 g", "Kit Detox com Quelação",
                    "Kit Detox Prevenção | Prata e Ouro Coloidal + Carvão Pulverizado",
                    "Kit Composto Emagrecedor para 3 meses", "Ouro Coloidal; e Prata Coloidal"):
        assert product in barden, product
    assert "tirzepatida" not in barden.lower() and "retatrutida" not in barden.lower()

    assert "empresa não identificada" in liberty and "CNPJ é desconhecido" in liberty and "1018541/26-1" in liberty
    assert "apreensão e proibição de armazenamento, comercialização, distribuição e propaganda" in liberty
    for product in ("Retatrutida e Outros", "NAD+ Liberty Pharma", "Retatrutida Liberty Pharma",
                    "Glow GHK-Cu Liberty Pharma", "Tirzepatida Liberty Pharma", "GHK-Cu Liberty Pharma"):
        assert product in liberty, product
    assert "não se aplicam às importações por pessoa física para uso próprio" in liberty
    assert "não lista fabricação, importação nem uso" in liberty
    assert "Não é proibição geral da tirzepatida" in liberty

    assert "oxygenkwpharmabrasil.com" in oxygen and "1033199/26-9" in oxygen
    assert "apreensão e proibição de comercialização, distribuição, fabricação, importação, propaganda e uso" in oxygen
    for product in ("Retagen 40 mg (retatrutida)", "BPC-157", "GHK-Cu", "TB-500"):
        assert product in oxygen, product
    assert "Liberty" not in oxygen and "Oxygen Pharm" not in oxygen

    assert "ZPH Contabilidade S/C Ltda." in zph and "01.485.419/0001-43" in zph and "1033148/26-4" in zph
    assert "www.zphcstore.com.br" in zph
    assert "apreensão e proibição de comercialização, distribuição, fabricação, importação, propaganda e uso" in zph
    for product in ("Retatrutide 120 mg", "Caneta Retatrutide 60 mg", "Tirzepatide 150 mg", "Caneta Tirzepatide 75 mg"):
        assert product in zph, product
    assert "não correspondem ao medicamento registrado na Anvisa" in zph
    assert "Não é proibição geral da tirzepatida" in zph

    # A exceção de uso próprio, o armazenamento e a falta de AFE são só do item 4.
    for term in ("uso próprio", "armazenamento", "Autorização de Funcionamento"):
        assert [term in item for item in items] == [False, False, False, True, False, False], term

    # Os sítios dos vendedores ficam só como texto. Desde 20/10/2026, o quadro também não tem link para a íntegra.
    assert re.findall(r"<a\b[^>]*>", callout) == []
    assert DOU_RE_4035_URL not in html and "Íntegra da Resolução" not in callout
    assert "http" not in _text(callout)
    for site in ("zyntrashop", "peptideosdobrasil", "oxygenkwpharmabrasil", "zphcstore"):
        assert f"//{site}" not in html and f"//www.{site}" not in html, site

    # Na v2 cada RE tem a sua lista; o parágrafo comum do quadro vem depois da última.
    closing = _text(callout.rsplit("</ul>", 1)[1])
    assert "assinada em 09/10/2026" in closing
    assert "publicada no DOU de 14/10/2026, edição 194, Seção 1, página 73" in closing
    assert "data em que entrou em vigor, conforme o art. 2º" in closing
    assert "o ato não é proibição geral da tirzepatida nem de outra substância" in closing
    assert closing.endswith("Os endereços eletrônicos citados identificam os anúncios descritos no ato e não são indicados como referência.")
    for number in ("3.989", "4.009", "3.947"):
        assert number not in callout


def _october_21_callout(html):
    start = html.index('data-news-update-callout aria-labelledby="novas-medidas-21-outubro-title"')
    return html[start:html.index("</aside>", start)]


def test_re_4140_and_re_3159_keep_scope_spelling_and_do_not_release_the_products():
    html = _page_html()
    callout = _october_21_callout(html)
    items = [_text(item) for item in _items(callout)]
    july_heading = html.index("<h2>Cosméticos e saneantes também foram alcançados</h2>")
    july = _text(html[july_heading:html.index("</p>", july_heading)])

    # Desde 22/10/2026 o quadro das RE nº 4.143, 4.147 e 4.150 vem antes; este é o segundo.
    assert html.index("data-news-update-callout") == html.index(
        'data-news-update-callout aria-labelledby="novas-medidas-22-outubro-title"')
    assert html.index('aria-labelledby="novas-medidas-22-outubro-title"') < html.index(
        'aria-labelledby="novas-medidas-21-outubro-title"') < html.index('aria-labelledby="novas-medidas-19-outubro-title"')
    assert "Atualização: medidas publicadas no DOU em 21/10/2026" in callout
    assert len(items) == 2
    vita, correction = items

    assert vita.startswith("SDK Indústria de Cosméticos — Regenerador de Unhas Vita Nails Podokesia (RE nº 4.140/2026):")
    assert "recolhimento e suspensão de comercialização, distribuição, fabricação, propaganda e uso" in vita
    assert "40.498.582/0001-00" in vita and "1048558/26-9" in vita
    assert "regenerador de unhas, elimina 99% dos fungos e bactérias" in vita
    assert "regularização indevida como cosmético de produto indicando em sua rotulagem indicações terapêuticas" in vita
    assert "não alcança outros produtos da SDK, outras apresentações Vita Nails ou Podokesia" in vita
    assert "O ato não determina apreensão" in vita
    assert "apreensão" not in vita.replace("não determina apreensão", "")
    for forbidden in ("proibição", "falsific", "liberad", "aprovad"):
        assert forbidden not in vita.casefold(), forbidden

    assert "tornou insubsistentes as medidas preventivas de 24/07/2026" in correction
    assert "Air Repair Pescan" in correction and "Pescant" not in html
    assert "Fluído Flesh Air Frionel" in correction and "Bardahl Flush Promax" in correction
    assert "Ecotec-Pro" in correction and "Ecotec" in correction
    assert "não são saneantes" in correction
    assert "passa a identificar a Obatrade Indústria e Importação Ltda." in correction
    assert "12.953.681/0001-91" in correction
    assert "5044747-39.2026.4.04.7000/PR" in correction
    assert "DOU de 13/08/2026, edição 152, Seção 1, p. 66" in correction
    assert "DOU de 20/10/2026, edição 198, Seção 1, p. 110" in correction
    assert "Corrigimos nesta data o trecho de 24/07, que ainda listava esses produtos entre as medidas." in correction
    assert 'id="correcao-re-3159-2026"' in callout
    for untouched in ("Nevada", "Dugold", "Friven", "Pega Barata", "Ar da Terra"):
        assert untouched not in correction, untouched
    for forbidden in ("liberad", "aprovad", "falsific"):
        assert forbidden not in correction.casefold(), forbidden

    # Na v2 cada RE tem a sua lista; o parágrafo comum do quadro vem depois da última.
    closing = _text(callout.rsplit("</ul>", 1)[1])
    assert closing == ("A Resolução-RE nº 4.140 foi assinada em 19/10/2026 e publicada no DOU de 21/10/2026, "
                       "edição 199, Seção 1, página 67, data em que entrou em vigor, conforme o art. 2º.")

    july_html = html[july_heading:html.index("</p>", july_heading)]
    assert july.replace(" .", ".") == (
        "Cosméticos e saneantes também foram alcançados Em 24 de julho, diferentes saneantes foram submetidos à "
        "apreensão e à proibição de fabricação, venda, distribuição, divulgação e uso por ausência de registro ou "
        "notificação, entre eles Nevada A/C Flush, Dugold R141B, Ecomate Dugold, Gás Refrigerante R141B – Friven e "
        "Pega Barata BSB, todos os lotes. O Ar da Terra – Air Flush teve medida semelhante porque a fabricante não "
        "possuía autorização adequada para aquela atividade. As medidas de 24 de julho sobre Fluído Flesh Air Frionel, "
        "Ecotec-Pro, Ecotec, Bardahl Flush Promax e Air Repair Pescan (itens 1 a 4 da Resolução-RE nº 2.895/2026) "
        "foram tornadas insubsistentes pela Resolução-RE nº 3.159/2026; veja a correção publicada nesta página em "
        "21/10/2026."
    )
    assert "Pescant" not in html
    assert july.count("Air Repair Pescan") == 1
    kept = july.split("As medidas de 24 de julho sobre", 1)[0]
    for name in ("Nevada A/C Flush", "Dugold R141B", "Ecomate Dugold", "Friven", "Pega Barata BSB", "Ar da Terra"):
        assert name in kept, name
    for name in ("Fluído Flesh Air Frionel", "Ecotec-Pro", "Bardahl Flush Promax", "Air Repair Pescan"):
        assert name not in kept, name
    for forbidden in ("liberad", "aprovad"):
        assert forbidden not in july.casefold(), forbidden
    assert july_html.count('<a href="#correcao-re-3159-2026">veja a correção publicada nesta página em 21/10/2026</a>') == 1
    assert html.count('id="correcao-re-3159-2026"') == 1
    assert html.count('href="#correcao-re-3159-2026"') >= 1
    assert july_html.count('href="#correcao-re-3159-2026"') == 1

    assert re.findall(r"<a\b[^>]*>", callout) == []
    assert "http" not in _text(callout) and "http" not in july
    assert DOU_RE_4140_URL not in html and DOU_RE_3159_URL not in html
    assert DOU_RE_4035_URL not in html and DOU_RE_4090_URL not in html and DOU_RE_4105_URL not in html


def _october_13_callout(html):
    start = html.index('data-news-update-callout aria-labelledby="novas-medidas-13-outubro-title"')
    return html[start:html.index("</aside>", start)]


def test_october_13_callout_keeps_each_measure_bound_to_its_own_act_and_scope():
    html = _page_html()
    callout = _october_13_callout(html)
    items = [_text(item) for item in _items(callout)]

    assert html.count("data-news-update-callout aria-labelledby=") == 7
    assert html.index("novas-medidas-13-outubro-title") < html.index("novas-medidas-06-outubro-title")
    assert "Atualização: medidas publicadas no DOU em 13/10/2026" in callout
    assert len(items) == 19
    (
        sergio, dhermamix, mavi, splendid, natureza, toalhas_5s, ottopar, lamarka,
        natumix, capilar, apitoxina, mamede, naturell, legacy, farmausa, xeomin,
        global_supplies, farmarin, gugu,
    ) = items

    assert "Sergio Paris" in sergio and "88.029.244/0001-48" in sergio and "1025163/26-4" in sergio
    assert "proibição de comercialização, distribuição, fabricação, propaganda e uso, e recolhimento" in sergio
    assert "não determina apreensão" in sergio
    assert "Dhermamix" not in sergio and "Mavi" not in sergio

    assert "Dhermamix Cola Ultra Hold" in dhermamix and "1032988/26-9" in dhermamix
    assert "empresa e o CNPJ são desconhecidos" in dhermamix
    assert "apreensão e proibição de comercialização, distribuição, fabricação, propaganda e uso" in dhermamix
    assert "não determina recolhimento nem importação" in dhermamix
    assert "Sergio Paris" not in dhermamix

    assert "Mavi" in mavi and "39.311.130/0001-80" in mavi and "0996529/26-7" in mavi
    assert "apreensão e proibição de armazenamento, comercialização, fabricação, importação, propaganda e uso" in mavi
    assert "não determina distribuição nem recolhimento" in mavi

    assert "Splendid Body Splash Edison Feijó" in splendid and "1041959/26-4" in splendid
    assert "www.voteconcursos.com" in splendid and "href=" not in splendid
    assert "não determina recolhimento nem importação" in splendid
    assert "Oleicos" not in splendid

    assert "Natureza Raiz" in natureza and "33.290.848/0001-51" in natureza and "1022596/26-0" in natureza
    assert "desconhece a fabricação" in natureza and "não é atribuída à Oleicos" in natureza
    assert "importação" in natureza

    assert "Sensitive For You Baby" in toalhas_5s and "Sensitive For You Adulto" in toalhas_5s
    assert "01.781.409/0001-55" in toalhas_5s and "1036448/26-0" in toalhas_5s
    assert "RDC nº 528/2021" in toalhas_5s and "não se enxaguam" in toalhas_5s
    assert "não determina apreensão" in toalhas_5s
    assert "Gugu Dadá" not in toalhas_5s

    assert "Ottopar" in ottopar and "03.723.193/0001-05" in ottopar and "1000457/26-2" in ottopar
    assert "suspensão de comercialização, distribuição, fabricação, propaganda e uso" in ottopar
    assert "04/08/2026" in ottopar and "Colombo/PR" in ottopar
    assert "não determina apreensão" in ottopar
    assert "apreensão" not in ottopar.replace("não determina apreensão", "")

    assert "Mara Arruda Liso Perfeito 4D" in lamarka and "27.799.585/0001-08" in lamarka
    assert "1006421/26-4" in lamarka and "encerra em “de 19.”" in lamarka
    assert "edição certificada do DOU de 13/10/2026, edição 193, Seção 1, página 159" in lamarka
    assert "O ano não foi completado" in lamarka
    assert "não foi conferido" not in lamarka
    assert "não determina apreensão" in lamarka
    assert "1999" not in lamarka

    assert "PSM Pennaforte" in natumix and "PSMP Produtos Naturais ME EPP (Natumix)" in natumix
    assert "12.316.032/0001-80" in natumix and "1058669/26-5" in natumix
    assert "Marataízes/ES" in natumix and "418/2026/NEVS/GEVS/SSVS/SESA" in natumix
    assert "ora-pro-nóbis" in natumix and "Não é proibição geral do Mounjaro nem do ora-pro-nóbis" in natumix
    assert "não determina recolhimento" in natumix
    assert "tirzepatida" not in natumix

    assert "Divora" in capilar and "Miss Romantic" in capilar and "1000772/26-5" in capilar
    assert "importação" in capilar and "não determina recolhimento" in capilar
    assert "apitoxina" not in capilar

    assert "apitoxina" in apitoxina and "Néctar Cosméticos" in apitoxina and "1019448/26-7" in apitoxina
    assert "sem registro" in apitoxina and "não determina importação nem recolhimento" in apitoxina
    assert "Divora" not in apitoxina

    assert "Pharmácia Mamede" in mamede and "04.745.752/0001-32" in mamede and "1037947/26-9" in mamede
    assert "suspensão de comercialização e propaganda" in mamede
    assert "não determina recolhimento nem apreensão" in mamede
    assert "Naturell" not in mamede

    assert "Naturell" in naturell and "62.069.760/0003-74" in naturell and "62.069.760.0001-02" in naturell
    assert "1013476/26-0" in naturell and "29 a 31/07/2026" in naturell
    assert "proibição de armazenamento, comercialização e distribuição" in naturell
    assert "não determina fabricação, uso, recolhimento nem apreensão" in naturell
    assert "Global Supplies" not in naturell

    assert "MC Legacy Lab" in legacy and "23.334.258/0001-20" in legacy and "1033060/26-7" in legacy
    assert "implantes hormonais estéreis" in legacy
    assert "suspensão de comercialização, manipulação, propaganda e uso" in legacy
    assert "ausência de prescrições médicas individualizadas" in legacy
    assert "ausência de prescrições individualizadas" not in legacy
    assert "não determina recolhimento nem apreensão" in legacy

    assert "HXTZ251015" in farmausa and "37.124.240/0001-08" in farmausa and "1048833/26-2" in farmausa
    assert "apreensão, proibição de comercialização, distribuição, manipulação e uso, e recolhimento" in farmausa
    assert "Não é proibição geral da tirzepatida" in farmausa
    assert "Xeomin" not in farmausa

    assert "NDC 46785-162-03" in xeomin and "0999500/26-5" in xeomin and "11.681.446/0001-45" in xeomin
    assert "não é atribuída à Merz" in xeomin
    assert "quaisquer pessoas físicas ou jurídicas" in xeomin
    assert "não determina recolhimento" in xeomin
    assert "Farmausa" not in xeomin

    assert "Global Supplies" in global_supplies and "22.579.717/0001-72" in global_supplies
    assert "1021052/26-1" in global_supplies and "31/08/2026 a 04/09/2026" in global_supplies
    assert "classifica o tipo como medicamento" in global_supplies
    assert "insumos farmacêuticos importados e distribuídos" in global_supplies
    assert "não determina apreensão" in global_supplies
    assert "Farmarin" not in global_supplies

    assert "P07725A" in farmarin and "58.635.830/0001-75" in farmarin and "1013292/26-9" in farmarin
    assert "CLORETO DE SÓDIO - 200 MG / ML SOL INJ IV CX 200 AMP PLAS TRANS X 10 ML" in farmarin
    assert "Cloreto de Sódio 20% MG/mL" in farmarin and "flaconete íntegro" in farmarin
    assert "recolhimento voluntário" in farmarin and "restrita ao lote identificado" in farmarin
    assert "apreensão" not in farmarin

    assert "Gugu Dadá" in gugu and "Castelo Rá Tim Bum" in gugu and "Quintal da Cultura Premium" in gugu
    assert "1037827/26-8" in gugu and "empresa e o CNPJ são desconhecidos" in gugu
    assert "não determina recolhimento nem importação" in gugu
    assert "Sensitive For You" not in gugu

    # Na v2 cada RE tem a sua lista; o parágrafo comum do quadro vem depois da última.
    closing = _text(callout.rsplit("</ul>", 1)[1])
    assert "assinadas em 08/10/2026" in closing and "assinadas em 09/10/2026" in closing
    assert "publicação das seis resoluções no DOU de 13/10/2026, Seção 1" in closing
    assert "href=" not in callout
    for number in ("3.946", "3.947", "3.850", "3.852"):
        assert number not in callout


def _october_06_callout(html):
    start = html.index('data-news-update-callout aria-labelledby="novas-medidas-06-outubro-title"')
    return html[start:html.index("</aside>", start)]


def test_october_06_callout_keeps_each_act_and_the_aloe_rectification_apart():
    html = _page_html()
    callout = _october_06_callout(html)
    items = [_text(item) for item in _items(callout)]

    assert len(items) == 8
    labs, costa, sintonia, peptideos, marcas, imaavy, lizbi, aloe = items
    assert "LABS" in labs and "25.178.555/0001-59" in labs and "28/09/2026 a 02/10/2026" in labs
    assert "Costa Mar" not in labs and "Sintonia" not in labs
    assert "Costa Mar" in costa and "51.939.490/0001-27" in costa and "insulina glargina" in costa
    assert "não determina recolhimento nem apreensão" in costa and "não é proibição geral da insulina" in costa
    assert "Sintonia Pharma" in sintonia and "37.560.104/0001-60" in sintonia and "Vermefree" in sintonia
    assert "LABS" not in sintonia
    assert "empresa não identificada" in peptideos and "CNPJ é desconhecido" in peptideos
    assert "BPC157" not in peptideos and "Imaavy" not in peptideos
    assert "BPC157" in marcas and "Alluvi Healthcare" in marcas and "Oxygen KW Pharma" in marcas
    assert "Retagen 40 mg retatrutide — Oxygen Pharm" in marcas
    assert "Retatrutide 40 mg — Alluvi Healthcare" in marcas
    assert "Retagen 40 mg retatrutida" not in marcas
    assert "Retatrutida 40 mg" not in marcas
    assert "Não é proibição geral da tirzepatida nem da retatrutida" in marcas
    assert "Imaavy" in imaavy and "JNYJ1201" in imaavy and "51.780.468/0001-87" in imaavy
    assert "não alcança outros lotes" in imaavy
    assert "Lizbi" in lizbi and "0000207107" in lizbi and "01.571.702/0001-98" in lizbi
    assert "restrita ao lote identificado" in lizbi
    assert "Biodis Industrial Ltda." in aloe and "União Vegetal Agroindustrial Ltda." in aloe
    assert "10.536.977/0001-81" in aloe
    assert "não cria outra medida nem altera o produto, os lotes ou as proibições" in aloe
    assert "RE nº 3.946 e 3.947 foram assinadas em 02/10/2026" in _text(callout)
    assert "publicação de ambas no DOU de 06/10/2026" in _text(callout)
    for number in ("3.850", "3.852", "3.854", "3.855", "3.856", "3.857"):
        assert number not in callout


def _october_callout(html):
    return _section_between(html, "<h2>2 de outubro: RE nº 3.850/2026", 'id="mes-setembro-2026"')


def _normalize_search(value):
    # Mesma normalização de normalizeText() em assets/js/main.js: minúsculas, NFD e sem diacríticos.
    import unicodedata
    value = unicodedata.normalize("NFD", value.lower())
    return "".join(ch for ch in value if not "\u0300" <= ch <= "\u036f").strip()


def test_october_callout_keeps_each_measure_bound_to_its_own_act_and_scope():
    html = _page_html()
    callout = _october_callout(html)

    # O detalhe de 02/10 fica depois dos quadros de 13 e 06/10 e antes de setembro.
    assert html.count("data-news-update-callout aria-labelledby=") == 7
    assert html.index('id="novas-medidas-13-outubro-title"') < html.index('id="novas-medidas-06-outubro-title"')
    assert html.index('id="novas-medidas-06-outubro-title"') < html.index('id="novas-medidas-02-outubro-title"')
    assert html.index('id="novas-medidas-02-outubro-title"') < html.index('id="novas-medidas-25-setembro-title"')
    assert "assinadas em 29 e 30/09/2026 e publicadas no DOU em 02/10/2026, data em que entraram em vigor" in callout

    heads = ("<h2>2 de outubro: RE nº 3.850/2026", "<h2>2 de outubro: RE nº 3.852/2026",
             "<h2>2 de outubro: RE nº 3.854/2026", "<h2>2 de outubro: RE nº 3.855/2026",
             "<h2>2 de outubro: RE nº 3.856/2026", "<h2>2 de outubro: RE nº 3.857/2026",
             'id="mes-setembro-2026"')
    positions = [html.index(h) for h in heads]
    parts = [html[a:b] for a, b in zip(positions, positions[1:])]
    for part, own in zip(parts, ("3.850", "3.852", "3.854", "3.855", "3.856", "3.857")):
        assert all(other not in part for other in ("3.850", "3.852", "3.854", "3.855", "3.856", "3.857") if other != own)
    assert "href=" not in callout


def test_october_body_sections_preserve_products_lots_operations_and_limits():
    html = _page_html()

    def section(start, end):
        begin = html.index(start)
        return _text(html[begin:html.index(end, begin)])

    heads = ("<h2>2 de outubro: RE nº 3.850/2026", "<h2>2 de outubro: RE nº 3.852/2026", "<h2>2 de outubro: RE nº 3.854/2026",
             "<h2>2 de outubro: RE nº 3.855/2026",              "<h2>2 de outubro: RE nº 3.856/2026", "<h2>2 de outubro: RE nº 3.857/2026",
             'id="mes-setembro-2026"')
    positions = [html.index(h) for h in heads]
    # Bloco de 02/10 depois do resumo regulatório e antes dos atos de setembro.
    assert html.index("Resumo regulatório") < positions[0] and positions == sorted(positions)
    gtech, hidrafemme, re3854, lgr, brmega, biojet = (_text(html[a:b]) for a, b in zip(positions, positions[1:]))
    perspirex = section("<h3>Item 1 — Perspirex Strong", "<h3>Item 2 — MAV C-22")
    mav = section("<h3>Item 2 — MAV C-22", "<h3>Item 4 — GhostBond XL")
    ghost = section("<h3>Item 4 — GhostBond XL", "<h3>Item 3 — Mult Jet")
    mult = section("<h3>Item 3 — Mult Jet", "<h2>2 de outubro: RE nº 3.855/2026")
    lgr1 = section("<h3>Item 1 — todos os saneantes da LGR", "<h3>Item 2 — Medicpro Zime")
    lgr2 = section("<h3>Item 2 — Medicpro Zime", "<h2>2 de outubro: RE nº 3.856/2026")

    for part, number, signed in ((gtech, "3.850", "29/09/2026"), (hidrafemme, "3.852", "29/09/2026"), (re3854, "3.854", "30/09/2026"),
                                 (lgr, "3.855", "30/09/2026"), (brmega, "3.856", "30/09/2026"), (biojet, "3.857", "30/09/2026")):
        assert f"Resolução-RE nº {number}, de {signed}, publicada no DOU em 02/10/2026" in part, number

    # G TECH: empresa e lote do anexo, três operações suspensas, sem recolhimento, apreensão ou falsificação.
    assert "C &amp; P Comércio de Produtos Médicos, Farmacêuticos e Hospitalares Ltda." in gtech and "36.470.048/0001-00" in gtech
    assert "tiras reagentes para medição de glicose G TECH" in gtech and "lote Z25J215F1" in gtech
    assert "determina a suspensão de comercialização, distribuição e propaganda" in gtech
    assert "inciso IV do art. 10 da Lei nº 6.437/1977" in gtech
    assert "A medida é restrita à empresa e ao lote indicados" in gtech and "não alcança as tiras G TECH em geral" in gtech
    gtech_rest = gtech.replace("O ato não determina recolhimento nem apreensão", "")
    for wrong in ("recolhimento", "apreensão", "proíbe", "proibição", "falsific", "desvio", "importação", "fabricação"):
        assert wrong not in gtech_rest, wrong

    # Hidrafemme: identificador “lot 2 2511006” preservado; origem desconhecida; Helianto não é a fabricante.
    assert "“lot 2 2511006”" in hidrafemme
    assert html.count("2511006") == html.count("lot 2 2511006") == 1
    assert "A empresa responsável por essas unidades e o respectivo CNPJ constam como desconhecidos" in hidrafemme
    assert "determina o recolhimento e proíbe a comercialização, a distribuição, a fabricação, a importação, a propaganda e o uso" in hidrafemme
    assert "Helianto Farmacêutica Ltda." in hidrafemme and "detentora do registro do produto, identificou unidades" in hidrafemme
    assert "A falsificação não é atribuída à Helianto" in hidrafemme and "não alcança os demais lotes do Hidrafemme" in hidrafemme
    for wrong in ("apreensão", "fabricadas pela Helianto", "fabricado pela Helianto", "Shopee"):
        assert wrong not in hidrafemme, wrong

    # RE nº 3.854/2026: ordem editorial 1, 2, 4, 3 com os números corretos; apreensão nos cosméticos, recolhimento no Mult Jet.
    assert "Os itens 1, 2 e 4 tratam de cosméticos e determinam apreensão; o item 3 trata de saneantes e determina recolhimento" in re3854
    assert all(lote in perspirex for lote in ("614326", "614323"))
    assert "Megalabs Farmacêutica S.A." in perspirex and "33.026.055/0001-20" in perspirex
    assert "desconhece a fabricação dessas unidades" in perspirex
    assert "A fabricação dessas unidades não é atribuída à Megalabs" in perspirex and "se limita aos dois lotes indicados" in perspirex
    for part in (perspirex, mav, ghost):
        assert "determina a apreensão e proíbe a comercialização, a distribuição, a fabricação, a importação, a propaganda e o uso" in part
        assert "recolhimento" not in part
    assert "todos os lotes" not in perspirex and "fabricadas pela Megalabs" not in perspirex
    for part in (mav, ghost):
        assert "sem regularização sanitária" in part and "todos os lotes" in part
        for wrong in ("falsific", "Megalabs", "dados cadastrais"):
            assert wrong not in part, wrong
    assert "MAV C-22 Solvente Removedor Cola Mega Hair" in mav
    assert "GhostBond XL — With Xtra Moisture Control Cola para Próteses Capilares" in ghost
    assert "Desincrustante Ácido DX 1:40 Mult-Cap Mult Jet" in mult and "Água Sanitária Mult Jet" in mult
    assert "Ramos Indústria e Comércio de Materiais de Limpeza Ltda." in mult and "46.069.515/0001-49" in mult
    assert "o ato determina o recolhimento" in mult
    assert "além da proibição de comercialização, distribuição, fabricação, importação, propaganda e uso" in mult
    assert "não se estende aos demais saneantes da Ramos" in mult
    assert "apreensão" not in mult.replace("não determina apreensão", "")

    # LGR: item 1 (todos os saneantes, três operações suspensas) separado do item 2 (três produtos, recolhimento e uso).
    assert "LGR Indústria e Comércio de Produtos de Limpeza Ltda." in lgr and "08.706.183/0001-77" in lgr
    assert "todos os produtos saneantes da empresa, em todos os lotes, e determina a suspensão de comercialização, distribuição e fabricação" in lgr1
    assert "RDC nº 47/2013" in lgr1 and "14 a 18/09/2026" in lgr1
    assert "Essas datas são as da inspeção e não delimitam a produção nem os lotes alcançados" in lgr1
    lgr1_rest = lgr1.replace("O item 1 não determina recolhimento nem suspensão do uso", "")
    assert "recolhimento" not in lgr1_rest and not re.search(r"\buso\b", lgr1_rest)
    assert all(product in lgr2 for product in ("Medicpro Zime", "Medicpro Zime Ultra", "Lapzyme"))
    assert "determina o recolhimento e a suspensão de comercialização, distribuição, fabricação e uso" in lgr2
    assert "valem apenas para os três produtos do item 2, e não para toda a produção da LGR" in lgr2

    # BR Mega Limp: todos os saneantes, com BR MT LIMP; sem importação, transporte ou recolhimento.
    assert "todos os produtos saneantes da BR Mega Limp Ltda." in brmega and "BR MT LIMP" in brmega and "16.731.434/0001-00" in brmega
    assert "determina a apreensão e proíbe a comercialização, a distribuição, a fabricação, a propaganda e o uso" in brmega
    assert "importação" not in brmega and "transporte" not in brmega
    assert "recolhimento" not in brmega.replace("O anexo não determina recolhimento.", "")

    # Biojet: só os dois produtos.
    assert "Bio Lavanda Limpador de Uso Geral Biojet" in biojet and "Bio Água Sanitária Biojet" in biojet
    assert "Biojet Indústria de Produtos Químicos Ltda." in biojet and "04.611.333/0001-08" in biojet
    assert "determina o recolhimento e proíbe a comercialização, a distribuição, a fabricação, a importação, a propaganda e o uso desses produtos" in biojet
    assert "A medida alcança apenas os dois produtos indicados, e não toda a produção da Biojet" in biojet
    for wrong in ("todos os produtos saneantes", "todos os saneantes", "apreensão"):
        assert wrong not in biojet, wrong

    # Sem links, prazos inventados ou atos fora da fase.
    block = html[positions[0]:positions[-1]]
    assert "href=" not in block
    for wrong in ("prazo de", "até que", "renova", "autoriza"):
        assert wrong not in _text(block), wrong
    assert "3.851" not in html and "3.853" not in html


def test_october_update_reaches_lead_summary_metadata_and_listing_search():
    html = _page_html()
    news_index = NEWS_INDEX_PATH.read_text(encoding="utf-8")
    description = ("Medidas recentes alcançam medicamentos, dispositivos médicos, cosméticos, saneantes e produtos sem registro, "
                   "inclusive itens divulgados com alegação emagrecedora.")

    assert html.count(description) == 4  # description, og, twitter e JSON-LD
    assert '"keywords": "medicamentos, dispositivos médicos, cosméticos,' in html
    assert "Medidas de julho a outubro alcançaram medicamentos, dispositivos médicos, cosméticos, saneantes" in html
    assert '"headline": "Anvisa suspende medicamento e proíbe produtos irregulares"' in html
    assert f'<meta content="{UPDATED}" property="article:modified_time"/>' in html

    card = _consolidated_card(news_index)
    assert "anvisa-suspende-medicamento-proibe-produtos-irregulares" in card
    attrs = dict(re.findall(r'\b(data-[a-z-]+)="([^"]*)"', card.split(">", 1)[0]))
    haystack = _normalize_search(" ".join([attrs["data-title"], attrs["data-summary"], attrs["data-keywords"],
                                           attrs["data-tags"], _text(card)]).replace("&amp;", "&"))
    for term in ("G TECH", "Hidrafemme", "Perspirex", "MAV C-22", "GhostBond XL", "Mult Jet", "LGR", "Medicpro",
                 "Lapzyme", "BR Mega Limp", "BR MT LIMP", "Biojet", "dispositivos médicos", "RE 3.850/2026",
                 "RE 3.852/2026", "RE 3.854/2026", "RE 3.855/2026", "RE 3.856/2026", "RE 3.857/2026"):
        assert _normalize_search(term) in haystack, term
    assert _consolidated_card(news_index).count(f'data-updated="{UPDATED}"') == 1
    # O carimbo de 21/10/2026, 17h45, é só desta matéria. O SISPA permanece às 10h12 de 20/10/2026.
    # A DCB permanece às 09h06 de 13/10/2026; o SNCR permanece às 13h00 de 20/10/2026.
    # Desde 22/10/2026 o carimbo é dividido com a matéria do SNCR, atualizada no mesmo lote.
    assert news_index.count(f'data-updated="{UPDATED}"') == 2
    assert news_index.count('data-updated="2026-10-20T10:12:00-03:00"') == 1
    assert 'href="/noticias/mapa-sispa-registro-agrotoxicos/"' in news_index
    assert news_index.count('data-updated="2026-10-13T09:06:00-03:00"') == 1
    assert news_index.count('data-updated="2026-10-20T13:00:00-03:00"') == 0


# Resumo do commit 1624995. A busca lia este texto; o patch revisado trocou-o pelo resumo curto
# e não alterou data-keywords. O "&" aqui é o valor decodificado do atributo.
_SUMMARY_BEFORE_SHORTENING = (
    "O DOU de 13/10/2026 publica as RE nº 3.989, 4.000, 4.001, 4.002, 4.009 e 4.028/2026, "
    "sobre medicamentos, insumos farmacêuticos, alimentos e cosméticos, inclusive o lote "
    "HXTZ251015 de tirzepatida, o lote NDC 46785-162-03 de Xeomin e o lote P07725A de cloreto de sódio. "
    "Publicações da Anvisa de 01/09 a 02/10 trazem seis resoluções de 02/10 sobre dispositivos médicos "
    "(um lote de tiras G TECH e um lote falsificado do Hidrafemme), cosméticos e saneantes, a suspensão "
    "das operações da Reach Latam com insumos controlados, incluindo tirzepatida (RE nº 3.764/2026), "
    "a RE nº 3.751/2026, sobre a distribuidora LAF MED e os manipulados estéreis da ICT Farmacêutica, "
    "medidas sobre United Labz, Mounjcaps, lotes falsificados de Enhertu e Dysport e um lote do TYG, "
    "e revogações de medidas referentes à Higia, à Tha & Thi e à Terapêutica "
    "(RE nº 3.743, 3.718 e 3.436/2026). As RE nº 3.946 e 3.947/2026 foram publicadas no DOU de 06/10/2026. "
    "Retificação de 09/10/2026 indica a União Vegetal Agroindustrial Ltda. como fabricante do Aloe Care."
)
_KEYWORDS_BEFORE_RESTORATION = (
    "ANVISA, Ocrevus, Eleve, D Casa, Smart GR, RE 3.751/2026, RE 3.712/2026, RE 3.714/2026, RE 3.717/2026, "
    "Phesgo, Dysport, Enhertu, Mounjcaps, United Labz, TYG, Hytamicina, Pangastri, Gripinew, Lipo Top Gold, "
    "Anagalis, RE 3.440/2026, RE 3.479/2026, RE 3.480/2026, RE 3.546/2026, RE 3.738/2026, dispositivos médicos, "
    "G TECH, Hidrafemme, Perspirex, MAV C-22, GhostBond XL, Mult Jet, LGR, Medicpro, Lapzyme, BR Mega Limp, "
    "BR MT LIMP, Biojet, RE 3.850/2026, RE 3.852/2026, RE 3.854/2026, RE 3.855/2026, RE 3.856/2026, "
    "RE 3.857/2026, RE 3.989/2026, RE 4.000/2026, RE 4.001/2026, RE 4.002/2026, RE 4.009/2026, RE 4.028/2026, "
    "Xeomin, tirzepatida, cloreto de sódio, produtos irregulares, fiscalização sanitária"
)
# Termos que o resumo antigo continha e o resumo curto não contém. "RE 3.946/2026" não era uma
# sequência contínua: o texto trazia "RE nº 3.946 e 3.947/2026" e "RE nº 3.743, 3.718 e 3.436/2026".
_TERMS_LOST_WITH_THE_SHORT_SUMMARY = (
    "Aloe Care", "União Vegetal Agroindustrial Ltda.", "Reach Latam", "Higia", "Tha & Thi", "Terapêutica",
    "ICT Farmacêutica", "LAF MED", "3.946", "3.947", "3.743", "3.718", "3.436", "3.764", "06/10/2026",
    "02/10", "insumos controlados", "manipulados estéreis", "Retificação",
)
_RESTORED_KEYWORDS = (
    "Aloe Care, União Vegetal Agroindustrial Ltda., Reach Latam, Higia, Tha & Thi, Terapêutica, "
    "ICT Farmacêutica, LAF MED, RE 3.946/2026, RE 3.947/2026, RE 3.743/2026, RE 3.718/2026, "
    "RE 3.436/2026, RE 3.764/2026, 06/10/2026, 02/10/2026, insumos controlados, manipulados estéreis, Retificação"
)
# 15/10/2026: termos da RE nº 4.035/2026 e números e lotes que saíram do resumo de 13/10/2026.
_KEYWORDS_RE_4035 = (
    "RE 4.035/2026, 14/10/2026, Farmácia Global de Peptídeos do Brasil, Cris Barden Naturopatia, Liberty Pharma, "
    "ZPH Contabilidade, zyntrashop.site, peptideosdobrasil.com.br, oxygenkwpharmabrasil.com, zphcstore.com.br, "
    "GHK-Cu, BPC-157, TB-500, NAD+, HXTZ251015, NDC 46785-162-03, P07725A, insumos farmacêuticos"
)
# 19/10/2026: termos das RE nº 4.090 e 4.105/2026 ("Dysport" já estava nas palavras-chave).
_KEYWORDS_RE_4090_4105 = "RE 4.090/2026, RE 4.105/2026, 19/10/2026, Keytruda, pembrolizumabe, 025155, Z005197, Z012354"
# 21/10/2026: RE nº 4.140/2026 e a correção da RE nº 3.159/2026. "Pescan" é a grafia do item 4 da RE nº 2.895.
_KEYWORDS_RE_4140 = (
    "RE 4.140/2026, 21/10/2026, SDK Indústria de Cosméticos, Regenerador de Unhas Vita Nails Podokesia, "
    "RE 3.159/2026, RE 2.895/2026, Air Repair Pescan, Obatrade, 1048558/26-9"
)
# 22/10/2026: RE nº 4.143, 4.147 e 4.150/2026; os nomes de julho que saíram do resumo seguem pesquisáveis.
_KEYWORDS_RE_4143_4147_4150 = (
    "RE 4.143/2026, RE 4.147/2026, RE 4.150/2026, 22/10/2026, Accu-Chek Active, Amazon, Roche Diabetes Care, NAC, "
    "N-acetil L-cisteína, Lauton, Shopee, 11-2025, Fauldleuco, Libbs, 25D0808, material particulado, "
    "Fluído Flesh Air Frionel, Frionel, Ecotec-Pro, Ecotec, Bardahl Flush Promax"
)


def _listing_haystack(attrs, keywords, visible):
    return _normalize_search(" ".join([
        attrs["data-title"], attrs["data-summary"], attrs["data-category"], keywords,
        attrs["data-tags"], visible,
    ]).replace("&amp;", "&"))


def test_shortened_summary_keeps_removed_names_searchable_through_keywords():
    news_index = NEWS_INDEX_PATH.read_text(encoding="utf-8")
    card = _consolidated_card(news_index)
    attrs = dict(re.findall(r'\b(data-[a-z-]+)="([^"]*)"', card.split(">", 1)[0]))
    visible = _text(card)
    summary = attrs["data-summary"]
    keywords = attrs["data-keywords"].replace("&amp;", "&")

    # O resumo curto (386 caracteres desde o ajuste de 21/10/2026; 347 na primeira redação do dia; 352 no de 15/10/2026) permanece nas duas ocorrências.
    # Os termos não voltam para o corpo do card.
    # 22/10/2026: resumo novo, com as RE nº 4.143, 4.147 e 4.150/2026 (342 caracteres).
    assert len(summary) == 342
    assert news_index.count(summary) == 2
    assert f"<p class=\"text-slate-500 text-sm leading-relaxed mb-4\">{summary}</p>" in card
    assert keywords == (f"{_KEYWORDS_BEFORE_RESTORATION}, {_RESTORED_KEYWORDS}, {_KEYWORDS_RE_4035}, "
                        f"{_KEYWORDS_RE_4090_4105}, {_KEYWORDS_RE_4140}, {_KEYWORDS_RE_4143_4147_4150}")
    assert "Tha &amp; Thi" in card.split(">", 1)[0]
    assert "Tha & Thi" not in card.split(">", 1)[0]
    received = _listing_haystack(attrs, _KEYWORDS_BEFORE_RESTORATION, visible)
    corrected = _listing_haystack(attrs, keywords, visible)
    old_summary = _normalize_search(_SUMMARY_BEFORE_SHORTENING)
    for term in _TERMS_LOST_WITH_THE_SHORT_SUMMARY:
        normalized = _normalize_search(term)
        assert normalized in old_summary, term
        assert normalized not in _normalize_search(summary), term
        assert normalized not in _normalize_search(visible), term
        assert normalized not in received, term
        assert normalized in corrected, term
    # A forma contínua "RE 3.946/2026" não estava no resumo antigo; o número estava.
    # A palavra-chave segue o padrão dos demais atos do card e recupera as duas buscas.
    for term in ("RE 3.946/2026", "RE 3.947/2026", "RE 3.743/2026", "RE 3.718/2026", "RE 3.436/2026", "RE 3.764/2026"):
        assert _normalize_search(term) not in old_summary, term
        assert _normalize_search(term) not in received, term
        assert _normalize_search(term) in corrected, term


def _october_22_callout(html):
    start = html.index('data-news-update-callout aria-labelledby="novas-medidas-22-outubro-title"')
    return html[start:html.index("</aside>", start)]


def test_october_22_callout_keeps_re_4143_4147_and_4150_within_their_own_scope():
    html = _page_html()
    callout = _october_22_callout(html)
    items = [_text(item) for item in _items(callout)]

    assert html.index("data-news-update-callout") == html.index(
        'data-news-update-callout aria-labelledby="novas-medidas-22-outubro-title"')
    assert "Atualização: medidas publicadas no DOU em 22/10/2026" in callout and "ATUALIZAÇÃO" in callout
    assert len(items) == 3
    accu, nac, fauld = items

    # RE nº 4.143/2026: só os dois produtos do anexo; o CNPJ do DOU (malformado) não é publicado.
    assert "RE nº 4.143/2026" in accu and "Amazon Serviços de Varejo do Brasil Ltda." in accu
    assert "“ACCU-CHEK ACTIVE 2 FRASCOS COM 50 UNIDADES - (29533831)”" in accu
    assert "“ACCU-CHEK ACTIVE 50 UNIDADES - (295)”" in accu
    assert "proibição de comercialização, distribuição, fabricação, importação, propaganda e uso" in accu
    assert "dispositivo médico" in accu and "1026551/26-1" in accu
    assert "Roche Diabetes Care Brasil Ltda." in accu and "“ONLY FOR GOVERNMENT TENDER”" in accu
    assert "O ato enquadra o caso como falsificação" in accu
    assert "O ato enquadra o caso como falsificação, conforme o art. 7º, XV, da Lei nº 9.782/1999, e em desacordo com o art. 10, XXVIII, da Lei nº 6.437/1977. O ato não atribui a falsificação à Amazon nem à Roche." in accu
    assert "não é proibição de todo o Accu-Chek Active" in accu
    assert "O ato não determina apreensão nem recolhimento." in accu
    assert "15.436.94" not in html and "CNPJ" not in accu
    for wrong in ("lote 29533831", "lote 295", "lotes 29533831", "código 29533831", "código 295", "códigos",
                  "falsificação da Roche", "falsificação da Amazon", "falsificado pela", "falsificados pela"):
        assert wrong not in accu, wrong

    # RE nº 4.147/2026: só o lote 11-2025, produto do tipo alimento.
    assert "RE nº 4.147/2026" in nac and "lote 11-2025" in nac and "tipo alimento" in nac
    assert "apreensão, interdição cautelar e proibição de comercialização, distribuição, fabricação, importação, propaganda e uso" in nac
    assert "Shopee" in nac and "empresa desconhecida" in nac
    assert "não se estende a outros lotes nem à marca" in nac
    assert "medicamento" not in nac

    # RE nº 4.150/2026: interdição cautelar por suspeita, pelo prazo do ato, sem data final calculada.
    assert "RE nº 4.150/2026" in fauld and "Libbs Farmacêutica Ltda." in fauld and "61.230.314/0001-75" in fauld
    assert "LOTE: 25D0808" in fauld and "interdição cautelar" in fauld and "90 (noventa) dias" in fauld
    assert "suspeita de desvio de qualidade relacionado à presença de material particulado" in fauld
    assert "o ato não indica data final" in fauld and "não confirma o desvio" in fauld
    for wrong in ("proibição", "proíbe", "recolhimento", "falsifica", "desvio confirmado", "/2027", "janeiro"):
        assert wrong not in fauld, wrong

    closing = _text(callout.rsplit("</ul>", 1)[1])
    assert closing == ("As Resoluções-RE nº 4.143 e 4.147 foram assinadas em 20/10/2026, e a RE nº 4.150, em 21/10/2026. "
                       "As três foram publicadas no DOU de 22/10/2026, edição 200, Seção 1, página 68, data em que entraram "
                       "em vigor, conforme o art. 2º de cada ato; a RE nº 4.150 vigora pelo prazo de 90 dias.")
    assert "href=" not in callout and "http" not in callout

    # Tabela: grupo de 22/10/2026 no topo de outubro, uma linha por RE.
    outubro = html[html.index('id="mes-outubro-2026"'):html.index('<details class="irregulares-detalhes" id="detalhes-outubro-2026"')]
    primeiro = re.search(r'<tbody>\s*<tr class="irregulares-tabela__data"><th colspan="4" scope="rowgroup">([^<]+)</th></tr>'
                         r'(.*?)</tbody>', outubro, re.DOTALL)
    assert primeiro.group(1) == "22/10/2026"
    linhas = re.findall(r'<tr data-busca="[^"]*" data-alvo="([^"]+)">(.*?)</tr>', primeiro.group(2), re.DOTALL)
    assert [alvo for alvo, _ in linhas] == ["irregulares-item-94", "irregulares-item-95", "irregulares-item-96"]
    situacoes = [_text(re.search(r'<td data-label="Situação"[^>]*>(.*?)</td>', linha).group(1)) for _, linha in linhas]
    assert situacoes == ["Vigente", "Vigente", "Interdição cautelar por 90 dias"]
    assert "15.436.94" not in outubro and "(29533831)" in outubro and "(295)" in outubro
