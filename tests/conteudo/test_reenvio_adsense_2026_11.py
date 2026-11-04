"""Reenvio ao AdSense (parecer de 01/11/2026): páginas reunidas, matérias novas e matérias ampliadas.

Regras do lote, pedidas no parecer:
- Páginas reunidas: as quatro do CNES (competências 06, 08, 09 e 10/2026) viram "Prazos de transmissão do CNES em
  2026" e as duas do SIFAP de maio viram "SIFAP: o ciclo de regularização cadastral de maio de 2026". Sem
  redirecionamento no servidor: a página antiga continua no ar, com noindex, follow no <head>, um aviso curto no topo do
  texto com link para a nova, fora do sitemap e sem card na listagem. Sem o script do AdSense, porque página noindex
  fica fora da monetização (test_privacidade.py).
- Matérias novas: as duas páginas reunidas e três guias (cadastros da drogaria; SNCR e SNGPC; recolhimentos,
  suspensões e alertas). Cada uma com card, item no ItemList, URL no sitemap e o AdSense uma vez no <head>.
- Matérias ampliadas: as seis notícias curtas da tabela do parecer que ganharam parte prática passam de 500 palavras
  no <section class="article-body"> e declaram a atualização (dateModified, "Atualizado em", card e lastmod).
- Nenhuma delas tem link externo no texto (regra de outubro de 2026, test_noticias_sem_links_editoriais_externos.py).
- Decisão do Jr (02/11/2026): a notícia do Paramol (lote 114053, recolhimento encerrado) também ganha noindex, sem o
  AdSense e fora do sitemap e da listagem. Não há página nova que a substitua, então não leva o aviso de página reunida;
  nenhuma outra página aponta para ela, e o guia de recolhimentos cita o caso no texto, sem link.

Os carimbos (01/11/2026, das 23h00 às 23h10, um minuto entre cada um, na ordem da listagem) são os da versão final do
lote, enviada para publicação. Até a revisão de 02/11/2026 eram provisórios (18h55 a 20h00).
"""
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://www.regularizeconsultorias.com.br"
INDEX = ROOT / "noticias" / "index.html"
SITEMAP = ROOT / "sitemap.xml"
COMUNICADO = ROOT / "comunicado" / "index.html"
ADSENSE_TAG = ('<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?'
               'client=ca-pub-2993532924249779"\n     crossorigin="anonymous"></script>')
NOINDEX = '<meta name="robots" content="noindex, follow" />'

CNES = "cnes-prazos-transmissao-2026"
SIFAP = "sifap-ciclo-regularizacao-cadastral-maio-2026"
REUNIDAS = {
    "cnes-prorroga-transmissor-competencia-06-2026": CNES,
    "cnes-competencia-08-2026-prazo-transmissao": CNES,
    "cnes-competencia-09-2026-prazo-transmissao": CNES,
    "cnes-competencia-10-2026-prazo-transmissao": CNES,
    "prazo-sifap-terminou-pendencias-analise-rta-farmacia-popular": SIFAP,
    "sifap-regularizacao-cadastral-farmacias-notificadas-13-maio": SIFAP,
}
# slug: (título, tipo do card, categoria, carimbo de publicação, prioridade no sitemap)
NOVAS = {
    CNES: ("Prazos de transmissão do CNES em 2026", "atualizacao", "cnes", "2026-11-01T23:10:00-03:00", "0.8"),
    "cadastros-autorizacoes-drogaria-afe-licenca-sanitaria-crf-cnes": (
        "Cadastros e autorizações de uma drogaria: AFE, licença sanitária, CRF e CNES", "orientacao", "anvisa",
        "2026-11-01T23:09:00-03:00", "0.7"),
    "sncr-e-sngpc-o-que-cada-sistema-controla-na-farmacia": (
        "SNCR e SNGPC: o que cada sistema controla na farmácia", "orientacao", "sncr",
        "2026-11-01T23:08:00-03:00", "0.7"),
    "recolhimentos-suspensoes-alertas-anvisa-como-a-farmacia-deve-reagir": (
        "Recolhimentos, suspensões e alertas da Anvisa: como a farmácia deve reagir", "orientacao", "anvisa",
        "2026-11-01T23:07:00-03:00", "0.7"),
    SIFAP: ("SIFAP: o ciclo de regularização cadastral de maio de 2026", "informativo", "farmacia-popular",
            "2026-11-01T23:06:00-03:00", "0.8"),
}
# slug: (datePublished, que não muda; carimbo da ampliação)
AMPLIADAS = {
    "anvisa-alerta-soroterapia-promessas-sem-evidencia": ("2026-07-14T10:03:00-03:00", "2026-11-01T23:05:00-03:00"),
    "anvisa-amplia-painel-medicamentos-pendentes-registro": ("2026-08-11T12:28:00-03:00", "2026-11-01T23:04:00-03:00"),
    "anvisa-nova-consulta-alertas-sanitarios-substitui-sistec": ("2026-07-06", "2026-11-01T23:03:00-03:00"),
    "anvisa-recolhimento-suplementos-irregulares-alivemed": ("2026-07-09", "2026-11-01T23:02:00-03:00"),
    "farmacia-popular-cuidados-cadastro-documentacao": ("2026-04-28T09:00:00-03:00", "2026-11-01T23:01:00-03:00"),
    "documentos-tecnicos-essenciais-farmacias-drogarias": ("2026-04-28T09:00:00-03:00", "2026-11-01T23:00:00-03:00"),
}
# 03/11/2026, 12h00 (hora do commit): o guia SNCR × SNGPC passa a declarar a atualização da RDC nº 1.046/2026
# (dateModified, "Atualizado em", data-updated no card e lastmod). Com a matéria do SNCR e o consolidado de irregulares,
# no mesmo carimbo, ele abre a listagem; as outras matérias do lote seguem na ordem dos carimbos de 01/11/2026.
ATUALIZADAS_03_11 = {"sncr-e-sngpc-o-que-cada-sistema-controla-na-farmacia": "2026-11-03T12:00:00-03:00"}
TOPO_03_11 = (
    "rdc-1000-2025-anvisa-prorroga-prazo-sncr",
    "sncr-e-sngpc-o-que-cada-sistema-controla-na-farmacia",
    "anvisa-suspende-medicamento-proibe-produtos-irregulares",
)
# 04/11/2026, 16h30: o guia de recolhimentos passa a declarar a atualização da retificação da RE nº 2.948/2026
# (DOU nº 207, de 04/11/2026: o lote 114053 do Paramol é de 500 mg, em embalagem com 500 comprimidos), com
# dateModified, "Atualizado em", data-updated no card e lastmod. Ele abre a listagem; as três de 03/11/2026 e as
# que ficavam à frente dele descem uma.
ATUALIZADAS_04_11 = {"recolhimentos-suspensoes-alertas-anvisa-como-a-farmacia-deve-reagir": "2026-11-04T16:30:00-03:00"}
ATUALIZADAS = {**ATUALIZADAS_03_11, **ATUALIZADAS_04_11}
TOPO = (*ATUALIZADAS_04_11, *TOPO_03_11)
ORDEM = [*TOPO, *(slug for slug in (*NOVAS, *AMPLIADAS) if slug not in TOPO)]
TIPOS = {
    "atualizacao": (">Atualização</span>", "Ler atualização"),
    "informativo": (">Informativo</span>", "Ler notícia"),
    "orientacao": (">Orientação</span>", "Ler orientação"),
}
WORD = re.compile(r"\w+(?:[-./]\w+)*")


class _Body(HTMLParser):
    """Texto do <section class="article-body">, com seções aninhadas, separado por bloco."""

    BLOCKS = {"p", "h2", "h3", "li", "tr", "td", "th", "div", "summary", "br"}

    def __init__(self):
        super().__init__()
        self.depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        classes = (dict(attrs).get("class") or "").split()
        if tag == "section" and (self.depth or "article-body" in classes):
            self.depth += 1
        if self.depth and tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if self.depth and tag == "section":
            self.depth -= 1

    def handle_data(self, data):
        if self.depth:
            self.parts.append(data)


def _html(slug):
    return (ROOT / "noticias" / slug / "index.html").read_text(encoding="utf-8")


def _body_text(html):
    parser = _Body()
    parser.feed(html)
    return " ".join("".join(parser.parts).split())


def _body_html(html):
    """O <section class="article-body"> inteiro, com as seções aninhadas."""
    start = html.index('<section class="article-body">')
    depth = 0
    for tag in re.finditer(r"<(/?)section\b", html[start:]):
        depth += -1 if tag.group(1) else 1
        if depth == 0:
            return html[start:start + tag.end()]
    raise AssertionError("article-body sem fechamento")


def _words(text):
    return len(WORD.findall(text))


def _news_article(html):
    blocks = re.findall(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', html, re.S)
    found = [item for item in map(json.loads, blocks) if item.get("@type") == "NewsArticle"]
    assert len(found) == 1
    return found[0]


def _canonical(head):
    links = [tag for tag in re.findall(r"<link\b[^>]*>", head) if re.search(r'rel="canonical"', tag)]
    assert len(links) == 1
    return re.search(r'href="([^"]+)"', links[0]).group(1)


def _meta_property(head, name):
    tags = [tag for tag in re.findall(r"<meta\b[^>]*>", head) if f'property="{name}"' in tag]
    assert len(tags) == 1, name
    return re.search(r'content="([^"]+)"', tags[0]).group(1)


def _cards():
    html = INDEX.read_text(encoding="utf-8")
    cards = re.findall(r"(<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>)", html, re.S)
    return html, cards, [re.search(r'href="/noticias/([^/"]+)/"', card).group(1) for card in cards]


def _itemlist(html):
    return [url for _, url in re.findall(r'\{"@type":"ListItem","position":(\d+),"url":"([^"]+)"\}', html)]


def _sitemap():
    text = SITEMAP.read_text(encoding="utf-8")
    entries = re.findall(r"<url>\s*<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>\s*<changefreq>[^<]+</changefreq>"
                         r"\s*<priority>([^<]+)</priority>\s*</url>", text)
    return {loc: (lastmod, priority) for loc, lastmod, priority in entries}, text


def test_paginas_reunidas_ficam_como_registro_com_noindex_e_aviso():
    index, _, slugs = _cards()
    sitemap, _ = _sitemap()
    itemlist = _itemlist(index)
    for antiga, nova in REUNIDAS.items():
        html = _html(antiga)
        head = html.split("</head>", 1)[0]
        url = f"{BASE}/noticias/{antiga}/"
        assert _canonical(head) == url, antiga
        assert head.count(NOINDEX) == 1 and html.count('name="robots"') == 1, antiga
        assert "adsbygoogle" not in html and "<ins" not in html, antiga
        # O aviso abre o texto: rótulo, link interno para a nova com o título dela e a frase de registro.
        body = html[html.index('<section class="article-body">') + len('<section class="article-body">'):]
        notice = body.split("</div>", 1)[0]
        assert body.lstrip().startswith("<div"), antiga
        assert ">Página reunida</p>" in notice, antiga
        assert re.findall(r'href="([^"]+)"', notice) == [f"/noticias/{nova}/"], antiga
        assert f">{NOVAS[nova][0]}</a>" in notice, antiga
        assert "Este texto fica como registro." in notice, antiga
        assert _words(_body_text(notice)) < 45, antiga
        # Fora do sitemap, da listagem e do ItemList.
        assert url not in sitemap, antiga
        assert antiga not in slugs and f'href="/noticias/{antiga}/"' not in index, antiga
        assert url not in itemlist, antiga


def test_so_as_paginas_reunidas_ainda_apontam_umas_para_as_outras():
    """Listagem, Comunicados e as demais matérias levam às páginas novas; o registro antigo só aparece entre si."""
    paths = [path for path in ROOT.rglob("*.html") if "a-publicar" not in path.parts]
    for path in paths:
        relative = path.relative_to(ROOT).parts
        if relative[0] == "noticias" and len(relative) == 3 and relative[1] in REUNIDAS:
            continue
        html = path.read_text(encoding="utf-8")
        for antiga in REUNIDAS:
            assert f"/noticias/{antiga}/" not in html, (path.relative_to(ROOT).as_posix(), antiga)
    comunicado = COMUNICADO.read_text(encoding="utf-8")
    assert comunicado.count(f'href="/noticias/{CNES}/"') == 2
    assert comunicado.count(f'href="/noticias/{SIFAP}/"') == 1


PARAMOL = "anvisa-suspende-recolhe-lote-114053-paramol-750-mg"
RECOLHIMENTOS = "recolhimentos-suspensoes-alertas-anvisa-como-a-farmacia-deve-reagir"


def test_paramol_fica_publicado_com_noindex_sem_anuncio_e_sem_links():
    index, _, slugs = _cards()
    sitemap, _ = _sitemap()
    html = _html(PARAMOL)
    head = html.split("</head>", 1)[0]
    url = f"{BASE}/noticias/{PARAMOL}/"
    assert _canonical(head) == url
    assert head.count(NOINDEX) == 1 and html.count('name="robots"') == 1
    assert "adsbygoogle" not in html and "<ins" not in html
    assert ">Página reunida</p>" not in html
    assert url not in sitemap and PARAMOL not in slugs and url not in _itemlist(index)
    for path in ROOT.rglob("*.html"):
        if "a-publicar" in path.parts or path.parent.name == PARAMOL:
            continue
        assert f"/noticias/{PARAMOL}/" not in path.read_text(encoding="utf-8"), path.relative_to(ROOT).as_posix()
    # O card de notícias relacionadas do guia passou do Paramol para o recolhimento de suplementos (Alivemed), indexável
    # e do mesmo tema; o caso do Paramol continua citado no texto do guia. 04/11/2026: com os dados da retificação da
    # RE nº 2.948/2026 (500 mg, embalagem com 500 comprimidos), que o próprio exemplo cita.
    guia = _html(RECOLHIMENTOS)
    relacionadas = guia.split('<section class="article-related-news"', 1)[1].split("</section>", 1)[0]
    assert re.findall(r'href="/noticias/([^"/]+)/"', relacionadas) == [
        "anvisa-suspende-medicamento-proibe-produtos-irregulares",
        "anvisa-nova-consulta-alertas-sanitarios-substitui-sistec",
        "anvisa-recolhimento-suplementos-irregulares-alivemed",
    ]
    texto = _body_text(guia)
    assert "Paramol 500 mg" in texto and "lote 114053, na apresentação com 500 comprimidos" in texto
    assert "a Anvisa retificou a RE nº 2.948/2026 (DOU nº 207, de 04/11/2026, Seção 1, p. 153)" in texto
    assert "Paramol 750 mg" not in texto


def test_materias_novas_tem_identidade_card_itemlist_sitemap_e_anuncio():
    index, cards, slugs = _cards()
    sitemap, sitemap_text = _sitemap()
    itemlist = _itemlist(index)
    for slug, (titulo, tipo, categoria, carimbo, prioridade) in NOVAS.items():
        posicao = ORDEM.index(slug)
        atualizado = ATUALIZADAS.get(slug, carimbo)
        html = _html(slug)
        head = html.split("</head>", 1)[0]
        url = f"{BASE}/noticias/{slug}/"
        news = _news_article(html)
        assert _canonical(head) == url, slug
        assert _meta_property(head, "og:url") == url, slug
        assert f"<title>{titulo} | Regularize Consultoria</title>" in head, slug
        assert html.count("<h1") == 1 and f">{titulo}</h1>" in html, slug
        assert 'name="robots"' not in html, slug
        assert head.count(ADSENSE_TAG) == 1 and html.count("adsbygoogle.js") == 1, slug
        assert (news["headline"], news["url"]) == (titulo, url), slug
        assert (news["datePublished"], news["dateModified"]) == (carimbo, atualizado), slug
        assert _meta_property(head, "article:published_time") == carimbo, slug
        assert _meta_property(head, "article:modified_time") == atualizado, slug
        if slug in ATUALIZADAS:
            assert (f'Atualizado em:</span> <time datetime="{atualizado}">{atualizado[8:10]}/{atualizado[5:7]}/'
                    f'{atualizado[:4]}</time> às {atualizado[11:13]}h{atualizado[14:16]}') in html, slug
        else:
            assert "Atualizado em" not in html, slug
        badge = {"atualizacao": "Atualização", "informativo": "Informativo", "orientacao": "Orientação"}[tipo]
        assert f'article-badge-{tipo} inline-flex items-center rounded-full px-2.5 py-1 whitespace-nowrap">{badge}</span>' in html, slug
        # Card: as cinco abrem a listagem, na ordem dos carimbos, com o tipo e a categoria da matéria.
        # 03/11/2026: a ordem é a de ORDEM; o card do guia SNCR × SNGPC leva data-updated e mostra a atualização.
        # 04/11/2026: o card do guia de recolhimentos também.
        assert slugs.index(slug) == posicao and slugs.count(slug) == 1, slug
        card = cards[posicao]
        opening = card.split(">", 1)[0]
        assert f'data-category="{categoria}"' in opening, slug
        if slug in ATUALIZADAS:
            assert f'data-updated="{atualizado}"' in opening, slug
        else:
            assert "data-updated" not in opening, slug
        assert f'data-title="{titulo}"' in opening and f">{titulo}</h2>" in card, slug
        assert (f'<time datetime="{atualizado}" class="leading-none">{atualizado[8:10]}/{atualizado[5:7]}/{atualizado[:4]} • '
                f'{atualizado[11:13]}h{atualizado[14:16]}</time>') in card, slug
        assert all(marca in card for marca in TIPOS[tipo]), slug
        assert itemlist[posicao] == url and itemlist.count(url) == 1, slug
        assert sitemap[url] == (atualizado[:10], prioridade), slug
        assert sitemap_text.count(f"<loc>{url}</loc>") == 1, slug
        # Texto próprio acima de 500 palavras, só com links internos.
        body = _body_html(html)
        assert _words(_body_text(html)) > 500, slug
        assert all(href.startswith("/") for href in re.findall(r'href="([^"]+)"', body)), slug
        assert "http" not in _body_text(html) and "www." not in _body_text(html), slug


def test_materias_ampliadas_passam_de_500_palavras_e_declaram_a_atualizacao():
    index, cards, slugs = _cards()
    sitemap, _ = _sitemap()
    for slug, (publicado, carimbo) in AMPLIADAS.items():
        posicao = ORDEM.index(slug)
        html = _html(slug)
        news = _news_article(html)
        assert news["datePublished"] == publicado, slug
        assert news["dateModified"] == carimbo, slug
        # As duas matérias de 28/04/2026 não têm as metas article:*; nas outras, a de modificação acompanha.
        if "article:modified_time" in html:
            assert _meta_property(html.split("</head>", 1)[0], "article:modified_time") == carimbo, slug
        assert f'Atualizado em:</span> <time datetime="{carimbo}">01/11/2026</time> às {carimbo[11:13]}h{carimbo[14:16]}' in html, slug
        assert _words(_body_text(html)) > 500, slug
        assert all(href.startswith("/") for href in re.findall(r'href="([^"]+)"', _body_html(html))), slug
        # Card logo depois das matérias novas, com a atualização como data válida (desde 03/11/2026, na posição de ORDEM).
        assert slugs.index(slug) == posicao, slug
        assert f'data-updated="{carimbo}"' in cards[posicao].split(">", 1)[0], slug
        assert sitemap[f"{BASE}/noticias/{slug}/"][0] == "2026-11-01", slug


def test_listagem_contadores_e_lastmod():
    index, cards, _ = _cards()
    sitemap, _ = _sitemap()
    # 02/11/2026 (decisão do Jr): a notícia do Paramol (lote 114053) ganhou noindex e saiu da listagem e do sitemap.
    assert len(cards) == 83 and "83 notícias encontradas" in index
    contadores = dict(re.findall(r"<span>([^<]+)</span><span class=\"text-xs text-slate-400\">(\d+)</span>", index))
    # 02/11/2026 (decisão do Jr): a notícia do Paramol (lote 114053) ganhou noindex e saiu da listagem e do sitemap.
    assert contadores["Todos"] == "83"
    assert contadores["ANVISA"] == "55"
    assert contadores["CNES"] == "3"
    assert contadores["SNCR"] == "3"
    assert contadores["FARMÁCIA POPULAR"] == "10"
    # 03/11/2026: a listagem trocou os resumos dos cards do SNCR e de produtos irregulares e levou esses dois e o do guia
    # SNCR × SNGPC ao topo.
    assert sitemap[f"{BASE}/noticias/"][0] == "2026-11-03"
    # Comunicados: três avisos trocaram só o destino do link; o texto e o lastmod ficam.
    # 03/11/2026: o aviso do SNCR ganhou a atualização da RDC nº 1.046/2026.
    assert sitemap[f"{BASE}/comunicado/"][0] == "2026-11-03"


def test_cnes_tabela_por_competencia_e_prorrogacoes_atribuidas():
    html = _html(CNES)
    body = _body_html(html)
    tabela = re.search(r"<table\b.*?</table>", body, re.S).group(0)
    limpo = lambda trecho: " ".join(re.sub(r"<[^>]+>", " ", trecho).split())
    cabecalho = [limpo(cell) for cell in re.findall(r"<th\b[^>]*>(.*?)</th>", tabela, re.S)]
    # Duas colunas, para a tabela caber em 320 px sem rolagem lateral (o custom.min.css das páginas não tem a rolagem de
    # .article-table-scroll): a competência e, na segunda, as três datas, uma por linha (<br>), cada uma com o rótulo.
    assert cabecalho == ["Competência", "Abertura, prazo final e cronograma"]
    rotulos = ["Abertura informada", "Prazo final informado", "Data limite no cronograma"]
    por_competencia = {}
    for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", tabela, re.S):
        celulas = re.findall(r"<td\b[^>]*>(.*?)</td>", row, re.S)
        if not celulas:
            continue
        assert len(celulas) == 2, row
        partes = [limpo(parte) for parte in re.split(r"<br\s*/?>", celulas[1])]
        assert [parte.split(":", 1)[0] for parte in partes] == rotulos, partes
        por_competencia[limpo(celulas[0])] = [parte.split(":", 1)[1].strip() for parte in partes]
    assert list(por_competencia) == ["06/2026", "07/2026", "08/2026", "09/2026", "10/2026", "11/2026", "12/2026"]
    # Abertura e prazo final vêm dos informes já registrados no site (páginas reunidas); a data do cronograma, do
    # cronograma do CNES. Prorrogação sempre com o prazo anterior e o informe que a trouxe.
    assert por_competencia["06/2026"] == ["16/06/2026", "09/07/2026, prorrogado de 07/07/2026 pelo informe de 07/07/2026",
                                          "07/07/2026"]
    assert por_competencia["08/2026"] == ["13/08/2026, informe de 13/08/2026", "08/09/2026", "08/09/2026"]
    assert por_competencia["09/2026"] == ["14/09/2026, informe de 14/09/2026",
                                          "09/10/2026, prorrogado de 07/10/2026 pelo informe de 05/10/2026", "07/10/2026"]
    assert por_competencia["10/2026"] == ["16/10/2026, informe de 16/10/2026", "09/11/2026", "09/11/2026"]
    assert [por_competencia[c][2] for c in ("07/2026", "11/2026", "12/2026")] == ["07/08/2026", "07/12/2026", "08/01/2027"]
    # Competências sem informe registrado não ganham data inventada.
    assert all("informe" in valor.casefold() or "não registrad" in valor.casefold()
               for competencia in ("07/2026", "11/2026", "12/2026") for valor in por_competencia[competencia][:2])
    texto = _body_text(html)
    assert "Situação em 01/11/2026" in texto
    lowered = " ".join(re.sub(r"<[^>]+>", " ", html.split('<section class="article-important-notice', 1)[0]).split()).casefold()
    for proibido in ("passo a passo", "como transmitir", "atras", "todas as farmácias", "toda farmácia",
                     "todos os estabelecimentos devem", "urgente", "nova versão foi", "versão obrigatória", "scnes 4."):
        assert proibido not in lowered, proibido
    # Toda prorrogação com data é atribuída a um informe com data; a tabela traz as duas de 2026, com a data original.
    texto = _body_text(html)
    assert len(re.findall(r"prorrogado de \d{2}/\d{2}/\d{4} pelo informe de \d{2}/\d{2}/\d{4}", texto)) == 2
    for frase in re.split(r"(?<=[.!?])\s+", texto):
        if "prorrog" in frase.casefold() and re.search(r"\d{2}/\d{2}/\d{4}", frase):
            assert re.search(r"informe de \d{2}/\d{2}/\d{4}", frase), frase


def test_guia_sncr_atribui_numeracao_e_prorrogacao_as_fontes():
    texto = _body_text(_html("sncr-e-sngpc-o-que-cada-sistema-controla-na-farmacia"))
    for frase in re.split(r"(?<=[.!?])\s+", texto):
        low = frase.casefold()
        if "16 dígitos" in low or "20 medicamentos" in low:
            assert "manual do sncr" in low or "o mesmo manual" in low or "limite técnico" in low, frase
        if "03/03/2027" in low:
            assert "anvisa" in low or "dou" in low or "diário oficial" in low, frase
    # 03/11/2026: a prorrogação saiu no DOU como RDC nº 1.046/2026; o guia deixa de dizer que ela não havia sido publicada.
    assert ("a RDC nº 1.046, de 29/10/2026, publicada no Diário Oficial da União de 03/11/2026, edição 206, Seção 1, "
            "página 244, deu nova redação ao art. 18 da RDC nº 1.000/2025") in texto
    assert "não havia sido publicada" not in texto and "ainda não foi publicada" not in texto
