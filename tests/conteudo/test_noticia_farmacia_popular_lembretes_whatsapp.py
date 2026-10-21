"""Esclarecimento sobre lembretes do Farmácia Popular pelo WhatsApp, com card na listagem e aviso em Comunicados.

Fontes conferidas em 17/10/2026: o comunicado do Ministério da Saúde de 29/05/2025 sobre os avisos por WhatsApp e pela
caixa postal do Gov.br, lido na reprodução do Conselho Federal de Farmácia (as páginas da Agência Gov e do Ministério
estavam fora do ar ou atrás de login); a página da Ouvidoria-Geral do SUS (telefone 136) e a página do Programa
Farmácia Popular. O anúncio de 2025 não comprova envios em outubro de 2026 nem autentica mensagens recebidas; por isso a
matéria é uma orientação, sem alerta de golpe, urgência ou anúncio de campanha nova, e sem links externos.
As datas editoriais (17/10/2026 às 09h50) são o momento real de criação da matéria, não a data do anúncio.
"""
import json
import re
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).parents[2]
SLUG = "farmacia-popular-esclarecimento-lembretes-whatsapp"
ROUTE = f"/noticias/{SLUG}/"
PAGE_PATH = ROOT / "noticias" / SLUG / "index.html"
INDEX_PATH = ROOT / "noticias" / "index.html"
COMUNICADO_PATH = ROOT / "comunicado" / "index.html"
SITEMAP_PATH = ROOT / "sitemap.xml"
PUBLIC_URL = f"https://www.regularizeconsultorias.com.br{ROUTE}"
PUBLISHED = "2026-10-17T09:50:43-03:00"
NOTICE_AT = "2026-10-17T09:50:00-03:00"
TITLE = "Farmácia Popular: esclarecimento sobre lembretes enviados pelo WhatsApp"
DESCRIPTION = ("O anúncio de 2025 sobre lembretes do Farmácia Popular pelo WhatsApp e pelo Gov.br não autentica mensagens "
               "recebidas. Veja como conferir a origem.")
KEYWORDS = "Farmácia Popular, WhatsApp, lembretes, Gov.br, Ministério da Saúde, Ouvidoria-Geral do SUS"
GENERIC_OG_PATH = ROOT / "assets" / "img" / "og" / "noticias.jpg"
GENERIC_OG_URL = "https://www.regularizeconsultorias.com.br/assets/img/og/noticias.jpg"
ADSENSE_SRC = "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2993532924249779"
# Texto-base aprovado, frase a frase.
BASE_SENTENCES = (
    "Em maio de 2025, o Ministério da Saúde anunciou o envio de lembretes pelo WhatsApp e pela caixa postal do aplicativo "
    "Gov.br para beneficiários do Farmácia Popular, com o objetivo de incentivar a continuidade dos tratamentos.",
    "A existência dessa iniciativa não confirma a autenticidade de qualquer mensagem recebida.",
    "O nome, a foto do perfil e um texto parecido com o comunicado oficial, isoladamente, não comprovam quem enviou.",
    "Antes de responder ou acessar links, procure os canais oficiais por conta própria.",
    "Não forneça senhas nem códigos de verificação em resposta à mensagem e não faça pagamentos para liberar medicamentos "
    "do programa.",
    "Em caso de dúvida, procure orientações pela Ouvidoria-Geral do SUS, no telefone 136.",
    "Este esclarecimento não autentica mensagens individuais nem classifica como golpe um envio que não foi verificado.",
)
# Nada de alerta, urgência, campanha nova, critério sem fonte, dados de clientes ou orientação sobre tratamento.
FORBIDDEN = (
    "urgente", "alerta", "atenção:", "cuidado com o golpe", "é golpe", "são golpes", "golpistas", "fraude", "nova campanha",
    "campanha", "em outubro de 2026", "dois meses", "2 meses", "sem retirada", "retirada", "retiradas", "3 retiradas",
    "270 mil", "hipertens", "diabet", "interromp", "suspenda", "pare de", "altere", "alterar o tratamento", "dose",
    "selo azul", "selo de verificado", "print", "captura de tela", "0800", "whatsapp oficial", "número oficial",
)


def _html():
    return PAGE_PATH.read_text(encoding="utf-8")


def _text(html):
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def _body(html):
    start = html.index('<section class="article-body">')
    return _text(html[start:html.index("</section>", start)])


def _editorial(html):
    # Cabeçalho, herói e corpo, sem o aviso institucional, o rodapé e as notícias relacionadas.
    return html.split('<section class="article-important-notice', 1)[0]


def _news_article(html):
    schemas = re.findall(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', html, re.DOTALL)
    return [item for item in map(json.loads, schemas) if item.get("@type") == "NewsArticle"]


def _active_notices():
    html = COMUNICADO_PATH.read_text(encoding="utf-8")
    lista = html[html.index('id="avisos-lista"'):html.index("Histórico / encerrados")]
    return re.findall(r"<article\b[^>]*>.*?</article>", lista, re.DOTALL)


def test_page_identity_dates_type_and_newsarticle():
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
    assert news[0]["articleSection"] == "FARMÁCIA POPULAR"
    assert news[0]["datePublished"] == PUBLISHED
    assert news[0]["dateModified"] == PUBLISHED
    assert news[0]["keywords"] == KEYWORDS
    assert f'<meta property="article:published_time" content="{PUBLISHED}" />' in html
    assert f'<meta property="article:modified_time" content="{PUBLISHED}" />' in html
    assert f'Publicado em:</span> <time datetime="{PUBLISHED}">17/10/2026</time> às 09h50' in html
    # Matéria nova: sem "Atualizado em".
    assert "Atualizado em" not in html
    # Orientação, categoria Farmácia Popular, órgão Ministério da Saúde.
    assert '<header class="article-hero-orientacao ' in html
    assert 'article-badge-orientacao inline-flex items-center rounded-full px-2.5 py-1 whitespace-nowrap">Orientação</span>' in html
    assert "article-hero-atualizacao" not in html and "article-hero-informativo" not in html
    assert html.count("category-chip--farmacia-popular") == 3
    assert "category-chip--cnes" not in html
    assert 'Órgão regulador:</span><span class="category-chip regulator-chip category-chip--farmacia-popular' in html
    assert '"name":"Lembretes do Farmácia Popular"' in html
    assert 'aria-current="page">Lembretes do Farmácia Popular</li>' in html


def test_base_text_attribution_and_scope():
    body = _body(_html())

    for sentence in BASE_SENTENCES:
        assert body.count(sentence) == 1, sentence
    # Atribuição textual: o comunicado de 2025 e onde ele foi lido; as páginas oficiais consultadas.
    assert ("O anúncio consta de comunicado do Ministério da Saúde de 29 de maio de 2025, reproduzido no mesmo dia pelo "
            "Conselho Federal de Farmácia.") in body
    assert ("Fontes: comunicado do Ministério da Saúde de 29/05/2025 sobre os avisos do Farmácia Popular, conforme a "
            "reprodução do Conselho Federal de Farmácia; páginas da Ouvidoria-Geral do SUS e do Programa Farmácia Popular "
            "no portal do Ministério da Saúde, consultadas em 17/10/2026.") in body
    # O anúncio de 2025 não comprova envios atuais.
    assert "O comunicado é de 2025 e, por si só, não indica se os envios continuam nem em que formato ocorrem atualmente." in body
    # O único telefone é o 136 da Ouvidoria-Geral do SUS; os demais números são as datas citadas.
    assert set(re.findall(r"\d+", body)) == {"2025", "29", "05", "17", "10", "2026", "136"}
    # O horário editorial não é atribuído ao anúncio.
    assert "09h50" not in body


def test_no_scam_alert_urgency_new_campaign_or_unsupported_claims():
    lowered = _text(_editorial(_html())).casefold()
    for claim in FORBIDDEN:
        assert claim not in lowered, claim
    # "golpe" só aparece na frase que recusa a classificação.
    assert lowered.count("golpe") == 1
    assert "nem classifica como golpe um envio que não foi verificado" in lowered


def test_no_external_links_and_no_exception():
    html = _html()
    main = html[html.index("<main>"):html.index("</main>")]
    start = html.index('<section class="article-body">')
    body = html[start:html.index("</section>", start)]

    assert re.findall(r'href="([^"]+)"', body) == []
    assert re.findall(r'href="(https?://[^"]+)"', main) == []


def test_institutional_notice_related_news_and_whatsapp_text():
    html = _html()
    notice = html[html.index('<section class="article-important-notice'):]
    related = html[html.index('<section class="article-related-news"'):]

    assert html.count('<section class="article-important-notice mt-10">') == 1
    assert "A Regularize Consultoria é uma empresa privada e independente." in _text(notice.split("</section>", 1)[0])
    assert "Programa Farmácia Popular" in _text(notice.split("</section>", 1)[0])
    for href in ("/noticias/farmacia-popular-adequacao-materiais-periodo-eleitoral/",
                 "/noticias/farmacia-popular-portaria-12091-2026-novas-regras/",
                 "/noticias/farmacia-popular-cuidados-cadastro-documentacao/"):
        assert f'href="{href}"' in related
        assert (ROOT / href.strip("/") / "index.html").is_file()
    assert "Vim%20pela%20notícia%20sobre%20os%20lembretes%20do%20Farmácia%20Popular%20pelo%20WhatsApp." in html


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
    opening = card.split(">", 1)[0]
    assert 'data-category="farmacia-popular"' in opening
    assert "data-updated" not in opening
    assert f'data-title="{TITLE}"' in opening and f">{TITLE}</h2>" in card
    assert f'data-summary="{DESCRIPTION}"' in opening
    assert f'data-keywords="{KEYWORDS}"' in opening
    assert "whatsapp" in opening and "ouvidoria-sus" in opening
    assert "golpe" not in card.casefold()
    assert f'<time datetime="{PUBLISHED}" class="leading-none">17/10/2026 • 09h50</time>' in card
    assert ">Orientação</span>" in card and "Ler orientação" in card
    assert "news-card--orientation" in opening and "news-card-compact" in opening
    assert ">FARMÁCIA POPULAR</span>" in card
    # Resumo curto do card.
    summary = re.search(r'<p class="text-slate-500 text-sm leading-relaxed mb-4">([^<]+)</p>', card).group(1)
    assert len(summary) <= 160 and "canais oficiais" in summary
    # A posição vem da data: era o card mais recente da listagem.
    # 20/10/2026, 10h12: os cards do consolidado de produtos irregulares e do SISPA sobem para a 1ª e a 2ª posições; os que ficavam entre eles descem uma.
    # 20/10/2026, 13h00: o card do SNCR, atualizado no lote 2, sobe para a 1ª posição; os que ficavam à frente dele descem uma.
    assert cards.index(card) == 3
    items = re.findall(r'\{"@type":"ListItem","position":(\d+),"url":"([^"]+)"\}', html)
    assert [int(p) for p, _ in items] == list(range(1, 86))
    assert items[3][1] == PUBLIC_URL
    assert html.count(f'"url":"{PUBLIC_URL}"') == 1
    assert '<span>Todos</span><span class="text-xs text-slate-400">85</span>' in html
    assert '<span>FARMÁCIA POPULAR</span><span class="text-xs text-slate-400">11</span>' in html
    assert len([c for c in cards if 'data-category="farmacia-popular"' in c.split(">", 1)[0]]) == 11
    assert "85 notícias encontradas" in html


def test_comunicado_informative_notice_is_active_first_and_internal():
    articles = _active_notices()
    own = [a for a in articles if f'href="{ROUTE}"' in a]

    # 19/10/2026, 15h40: o aviso da instabilidade nos sistemas da Anvisa é o ativo mais recente; os demais descem uma posição.
    # 20/10/2026: o aviso da instabilidade passa ao histórico; este volta a ser o ativo mais recente.
    assert len(articles) == 7
    assert len(own) == 1 and articles.index(own[0]) == 0
    notice = own[0]
    opening = notice.split(">", 1)[0]
    text = _text(notice)
    assert 'data-status="informativo"' in opening and 'data-category="farmacia-popular"' in opening
    assert f'data-effective-at="{NOTICE_AT}"' in opening
    assert 'data-updated-at="17/10/2026 às 09h50"' in opening
    assert {"border-orange-200", "bg-orange-50"} <= set(re.search(r'class="([^"]+)"', opening).group(1).split())
    assert "INFORMATIVO" in text and "URGENTE" not in text
    assert f'<time datetime="{NOTICE_AT}">17/10/2026 • 09h50</time>' in notice
    assert "Farmácia Popular: confira a origem de mensagens pelo WhatsApp" in text
    assert "Esse anúncio não autentica mensagens recebidas." in text
    assert "confira a origem pelos canais oficiais, procurados por conta própria" in text
    assert "telefone 136" in text
    assert "Leia o esclarecimento sobre os lembretes" in text
    assert "comunicado-cta comunicado-cta--informativo" in notice
    assert re.findall(r'href="([^"]+)"', notice) == [ROUTE]
    lowered = text.casefold()
    for claim in ("golpe", "fraude", "urgente", "campanha", "dois meses", "retirada"):
        assert claim not in lowered, claim


def test_sitemap_lists_the_new_url_once_with_current_lastmods():
    sitemap = SITEMAP_PATH.read_text(encoding="utf-8")

    assert sitemap.count("<loc>") == 106
    assert sitemap.count(f"<loc>{PUBLIC_URL}</loc>") == 1
    assert re.search(rf"<loc>{re.escape(PUBLIC_URL)}</loc>\s*<lastmod>2026-10-17</lastmod>", sitemap)
    # 20/10/2026: a listagem reordenou dois cards. 21/10/2026: reordenou o card de produtos irregulares.
    assert re.search(r"<loc>https://www\.regularizeconsultorias\.com\.br/noticias/</loc>\s*<lastmod>2026-10-21</lastmod>", sitemap)
    # 19/10/2026: o comunicado ganhou o aviso da instabilidade nos sistemas da Anvisa; 20/10/2026: o aviso foi encerrado.
    assert re.search(r"<loc>https://www\.regularizeconsultorias\.com\.br/comunicado/</loc>\s*<lastmod>2026-10-20</lastmod>", sitemap)
    # A URL nova entra logo depois da listagem, como as demais matérias novas.
    locs = re.findall(r"<loc>([^<]+)</loc>", sitemap)
    assert locs[locs.index("https://www.regularizeconsultorias.com.br/noticias/") + 1] == PUBLIC_URL
