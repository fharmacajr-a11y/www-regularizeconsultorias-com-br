"""Matéria da competência 10/2026 do CNES (informe de 16/10/2026), com card na listagem e aviso em Comunicados.

Fonte: página de informes do CNES (https://cnes2.datasus.gov.br/Mod_Mensagem_Abertura1.asp), consulta de 16/10/2026:
"Informamos que o Módulo Transmissor do CNES encontra-se aberto para envio da competência 10/2026 pelo período de
16/10/2026 a 09/11/2026", informe dirigido aos gestores, sem hora. Era o informe mais recente da página.
As datas editoriais (16/10/2026 às 20h06) são o momento real de criação da matéria, não o horário do informe.
"""
import json
import re
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).parents[2]
SLUG = "cnes-competencia-10-2026-prazo-transmissao"
ROUTE = f"/noticias/{SLUG}/"
PAGE_PATH = ROOT / "noticias" / SLUG / "index.html"
INDEX_PATH = ROOT / "noticias" / "index.html"
COMUNICADO_PATH = ROOT / "comunicado" / "index.html"
SITEMAP_PATH = ROOT / "sitemap.xml"
PUBLIC_URL = f"https://www.regularizeconsultorias.com.br{ROUTE}"
PUBLISHED = "2026-10-16T20:06:35-03:00"
NOTICE_AT = "2026-10-16T20:06:00-03:00"
TITLE = "CNES abre competência 10/2026 com envio até 9 de novembro"
DESCRIPTION = ("Informe do CNES de 16/10/2026 comunicou aos gestores a abertura do Módulo Transmissor para a competência "
               "10/2026, com envio de 16/10/2026 a 09/11/2026.")
GENERIC_OG_PATH = ROOT / "assets" / "img" / "og" / "noticias.jpg"
GENERIC_OG_URL = "https://www.regularizeconsultorias.com.br/assets/img/og/noticias.jpg"
ADSENSE_SRC = "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2993532924249779"
# O informe trata só da abertura do transmissor: nada de versão do sistema, atraso, acesso autenticado ou obrigação geral.
FORBIDDEN = (
    "nova versão foi", "nova versão do cnes desktop foi", "versão obrigatória", "está disponível a versão",
    "foi disponibilizada a versão", "scnes 4.", "atras", "prorrog", "acesso autenticado", "testamos", "conseguimos acessar",
    "todas as farmácias", "toda farmácia", "todos os estabelecimentos devem", "passo a passo", "como transmitir",
    "urgente",
)


def _html():
    return PAGE_PATH.read_text(encoding="utf-8")


def _text(html):
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def _body(html):
    start = html.index('<section class="article-body">')
    return _text(html[start:html.index("</section>", start)])


def _editorial(html):
    # Cabeçalho, herói e corpo; as notícias relacionadas citam legitimamente a prorrogação de 09/2026.
    return html.split('<section class="article-important-notice', 1)[0]


def _news_article(html):
    schemas = re.findall(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', html, re.DOTALL)
    return [item for item in map(json.loads, schemas) if item.get("@type") == "NewsArticle"]


def test_page_identity_dates_and_newsarticle():
    html = _html()
    news = _news_article(html)

    assert f'<link rel="canonical" href="{PUBLIC_URL}" />' in html
    assert f'<meta property="og:url" content="{PUBLIC_URL}" />' in html
    assert f"<title>{TITLE} | Regularize Consultoria</title>" in html
    assert html.count("<h1") == 1 and f">{TITLE}</h1>" in html
    assert html.count(f'content="{DESCRIPTION}"') == 3
    assert len(news) == 1
    assert news[0]["headline"] == TITLE
    assert news[0]["description"] == DESCRIPTION
    assert news[0]["url"] == PUBLIC_URL
    assert news[0]["articleSection"] == "CNES"
    assert news[0]["datePublished"] == PUBLISHED
    assert news[0]["dateModified"] == PUBLISHED
    assert news[0]["keywords"] == "CNES, DATASUS, competência 10/2026, Módulo Transmissor, Ministério da Saúde"
    assert f'<meta property="article:published_time" content="{PUBLISHED}" />' in html
    assert f'<meta property="article:modified_time" content="{PUBLISHED}" />' in html
    assert f'Publicado em:</span> <time datetime="{PUBLISHED}">16/10/2026</time> às 20h06' in html
    # Matéria nova: sem "Atualizado em".
    assert "Atualizado em" not in html
    assert 'article-badge-atualizacao inline-flex items-center rounded-full px-2.5 py-1 whitespace-nowrap">Atualização</span>' in html
    assert '"name":"CNES competência 10/2026"' in html
    assert 'aria-current="page">CNES competência 10/2026</li>' in html


def test_informe_attribution_period_and_distinctions():
    body = _body(_html())

    assert "Em informe publicado em 16 de outubro de 2026 e dirigido aos gestores, o CNES comunicou" in body
    assert "Módulo Transmissor encontra-se aberto para o envio da competência 10/2026" in body
    assert "16/10/2026 a 09/11/2026" in body
    assert "esse era o informe mais recente, sem orientação posterior sobre a competência 10/2026" in body
    # Competência, início do envio e prazo final, cada um com o seu papel.
    assert "Competência: 10/2026." in body
    assert "Início do envio: 16/10/2026, data em que o informe comunica a abertura do Módulo Transmissor." in body
    assert "Prazo final: 09/11/2026." in body
    assert "O informe não indica horário de abertura nem de encerramento." in body
    assert "A competência 10/2026 identifica o período de referência a que a base enviada corresponde; não é uma data de envio." in body
    assert "é o último dia do período informado para o envio pelo transmissor" in body
    assert "a data não deve ser interpretada como uma determinação uniforme de que cada estabelecimento realize diretamente a transmissão" in body
    assert "não significa, por si só, que uma nova versão do sistema tenha sido publicada" in body
    assert "O prazo final informado para a competência 10/2026 é 09/11/2026, conforme o informe de 16/10/2026." in body
    # O horário editorial não é atribuído ao informe.
    assert "20h06" not in body


def test_no_unsupported_claims_or_guide():
    lowered = _text(_editorial(_html())).casefold()
    for claim in FORBIDDEN:
        assert claim not in lowered, claim
    assert not re.search(r"\b4\.8\.\d+\b", _html())
    assert "09/2026" not in _editorial(_html())


def test_only_internal_links_in_the_editorial_text():
    html = _html()
    start = html.index('<section class="article-body">')
    body = html[start:html.index("</section>", start)]
    hrefs = re.findall(r'href="([^"]+)"', body)
    assert hrefs == ["/noticias/cnes-continua-obrigatorio-sncr-afe-farmacias/"]


def test_related_news_keep_previous_competences():
    html = _html()
    related = html[html.index('<section class="article-related-news"'):]
    assert 'href="/noticias/cnes-competencia-09-2026-prazo-transmissao/"' in related
    assert 'href="/noticias/cnes-competencia-08-2026-prazo-transmissao/"' in related
    assert "CNES prorrogou envio da competência 09/2026 até 9 de outubro" in related
    assert "CNES abriu competência 08/2026 com transmissão informada até 8 de setembro" in related


def test_temporary_generic_og_and_adsense_once():
    html = _html()
    head = html.split("</head>", 1)[0]

    assert html.count(f'<meta property="og:image" content="{GENERIC_OG_URL}" />') == 1
    assert html.count(f'<meta name="twitter:image" content="{GENERIC_OG_URL}" />') == 1
    assert _news_article(html)[0]["image"] == GENERIC_OG_URL
    with Image.open(GENERIC_OG_PATH) as image:
        assert image.format == "JPEG" and image.size == (1200, 630)
    assert html.count("adsbygoogle.js") == 1
    assert head.count(f'<script async src="{ADSENSE_SRC}"\n     crossorigin="anonymous"></script>') == 1
    assert "<ins" not in html


def test_news_index_card_itemlist_and_counters():
    html = INDEX_PATH.read_text(encoding="utf-8")
    cards = re.findall(r"<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>", html, re.DOTALL)
    own = [card for card in cards if f'href="{ROUTE}"' in card]

    assert len(cards) == 85
    assert html.count(f'href="{ROUTE}"') == 1
    assert len(own) == 1
    card = own[0]
    assert 'data-category="cnes"' in card
    assert "data-updated" not in card.split(">", 1)[0]
    assert f'data-title="{TITLE}"' in card and f">{TITLE}</h2>" in card
    assert f'data-summary="{DESCRIPTION}"' in card
    assert f'<time datetime="{PUBLISHED}" class="leading-none">16/10/2026 • 20h06</time>' in card
    assert ">Atualização</span>" in card and "Ler atualização" in card
    assert "news-amber-card" in card and "news-card-compact" in card.split(">", 1)[0]
    # A posição vem da data. 17/10/2026, 09h50: o card do esclarecimento do Farmácia Popular entra na 1ª posição da listagem; os demais descem uma.
    assert cards.index(card) == 1
    items = re.findall(r'\{"@type":"ListItem","position":(\d+),"url":"([^"]+)"\}', html)
    assert [int(p) for p, _ in items] == list(range(1, 86))
    assert items[1][1] == PUBLIC_URL
    assert html.count(f'"url":"{PUBLIC_URL}"') == 1
    assert '<span>Todos</span><span class="text-xs text-slate-400">85</span>' in html
    assert '<span>CNES</span><span class="text-xs text-slate-400">6</span>' in html
    assert "85 notícias encontradas" in html


def test_comunicado_informative_notice_is_active_and_third():
    html = COMUNICADO_PATH.read_text(encoding="utf-8")
    lista = html[html.index('id="avisos-lista"'):html.index("Histórico / encerrados")]
    articles = re.findall(r"<article\b[^>]*>.*?</article>", lista, re.DOTALL)
    own = [a for a in articles if f'href="{ROUTE}"' in a]

    # 17/10/2026, 09h50: o aviso do Farmácia Popular sobre lembretes é o ativo mais recente; o do CNES passa ao 2º.
    # 19/10/2026, 15h40: o aviso da instabilidade nos sistemas da Anvisa entra em 1º; o do CNES passa ao 3º.
    assert len(own) == 1 and articles.index(own[0]) == 2
    notice = own[0]
    opening = notice.split(">", 1)[0]
    text = _text(notice)
    assert 'data-status="informativo"' in opening and 'data-category="cnes"' in opening
    assert f'data-effective-at="{NOTICE_AT}"' in opening
    assert 'data-updated-at="16/10/2026 às 20h06"' in opening
    assert "INFORMATIVO" in text and "URGENTE" not in text
    assert f'<time datetime="{NOTICE_AT}">16/10/2026 • 20h06</time>' in notice
    assert "CNES: envio da competência 10/2026 aberto até 9 de novembro" in text
    assert "Em informe de 16/10/2026, o CNES comunicou aos gestores" in text
    assert "16/10/2026 a 09/11/2026" in text
    assert "O informe não indica horário de encerramento." in text
    assert "Leia a notícia sobre a competência 10/2026" in text
    assert re.findall(r'href="([^"]+)"', notice) == [ROUTE]
    assert "toda farmácia" not in text.casefold() and "prorrog" not in text.casefold()


def test_sitemap_lists_the_new_url_once():
    sitemap = SITEMAP_PATH.read_text(encoding="utf-8")

    assert sitemap.count("<loc>") == 106
    assert sitemap.count(f"<loc>{PUBLIC_URL}</loc>") == 1
    assert re.search(rf"<loc>{re.escape(PUBLIC_URL)}</loc>\s*<lastmod>2026-10-16</lastmod>", sitemap)
    # 17/10/2026: a listagem ganhou o card do esclarecimento do Farmácia Popular.
    assert re.search(r"<loc>https://www\.regularizeconsultorias\.com\.br/noticias/</loc>\s*<lastmod>2026-10-17</lastmod>", sitemap)
