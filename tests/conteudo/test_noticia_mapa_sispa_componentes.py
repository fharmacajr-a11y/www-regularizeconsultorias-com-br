"""Notícia do SISPA: atualização de 19/10/2026 sobre o cadastro de componentes.

O Comunicado nº 1, de 16/10/2026, da Coordenação-Geral de Agrotóxicos e Afins (CGAA/DSV/SDA/MAPA), publicado
no DOU de 19/10/2026, edição 197, Seção 3, página 3, suspende temporariamente o cadastro de componentes no SISPA
enquanto o módulo passa por adequações. A migração dos produtos técnicos prossegue, e os prazos de componentes
da Portaria SDA/MAPA nº 1.631/2026 serão revistos e republicados, sem data no ato. O parágrafo usa o nome do ato
como está no DOU e cita o DOU de 19/10, Seção 3, sem link (regra de 20/10/2026), não anuncia fim da
suspensão nem novo prazo e não se confunde com o "COMUNICADO SISPA N.º 1/2026" da página do sistema.
"""
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
SLUG = "mapa-sispa-registro-agrotoxicos"
ARTICLE = ROOT / "noticias" / SLUG / "index.html"
INDEX = ROOT / "noticias" / "index.html"
SITEMAP = ROOT / "sitemap.xml"
ROUTE = f"/noticias/{SLUG}/"
PUBLIC_URL = f"https://www.regularizeconsultorias.com.br{ROUTE}"
PUBLISHED = "2026-06-22T09:20:00-03:00"
# Publicação de 20/10/2026: "Atualizado em" é o instante real do commit. O rótulo do parágrafo fica em 19/10/2026,
# a data do DOU.
UPDATED = "2026-10-20T10:12:00-03:00"
UPDATED_DAY = f"{datetime.fromisoformat(UPDATED):%d/%m/%Y}"
UPDATED_CLOCK = f"{datetime.fromisoformat(UPDATED):%Hh%M}"
# Link retirado em 20/10/2026 (notícias sem links externos); não pode voltar.
DOU_URL = "https://www.in.gov.br/web/dou/-/comunicado-n-1-de-16-de-outubro-de-2026-738998299"
UPDATE_PARAGRAPH = (
    "<p><strong>Atualização em 19/10/2026:</strong> o Comunicado nº 1, de 16/10/2026, da Coordenação-Geral de "
    "Agrotóxicos e Afins do MAPA (DOU de 19/10, Seção 3), suspendeu temporariamente o cadastro de componentes no "
    "SISPA. A migração de produtos técnicos continua. Os prazos referentes aos componentes serão revistos e "
    "republicados pelo MAPA, sem nova data definida até o momento.</p>"
)


def _html():
    return ARTICLE.read_text(encoding="utf-8")


def _body(html):
    start = html.index('<section class="article-body">')
    return html[start:html.index("</section>", start)]


def _text(html):
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def _article_jsonld(html):
    for block in re.findall(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', html, re.DOTALL):
        data = json.loads(block)
        if data.get("@type") == "NewsArticle":
            return data
    raise AssertionError("NewsArticle ausente")


def test_update_paragraph_opens_the_body_with_the_exact_text():
    html = _html()
    body = _body(html)
    paragraphs = re.findall(r"<p>.*?</p>", body, re.DOTALL)

    assert html.count(UPDATE_PARAGRAPH) == 1
    assert paragraphs[0] == UPDATE_PARAGRAPH
    # O texto anterior da matéria continua logo depois, sem alteração.
    assert paragraphs[1].startswith("<p>O Ministério da Agricultura e Pecuária lançou o Sistema Unificado")
    assert "<h2>O que é o SISPA</h2>" in body and "<h2>A adaptação exige análise técnica</h2>" in body


def test_update_paragraph_keeps_the_scope_and_the_name_of_the_dou_notice():
    text = _text(_body(_html()))
    lowered = text.casefold()

    # Nome do ato como está no DOU, sem a sigla composta.
    assert "o Comunicado nº 1, de 16/10/2026, da Coordenação-Geral de Agrotóxicos e Afins do MAPA" in text
    assert "CGAA" not in text and "DSV/SDA" not in text
    assert "suspendeu temporariamente o cadastro de componentes no SISPA" in text
    assert "A migração de produtos técnicos continua" in text
    assert "serão revistos e republicados pelo MAPA, sem nova data definida até o momento" in text
    # Sem fim da suspensão, sem novo prazo e sem a data calculada fora do ato.
    for claim in ("23/11", "23 de novembro", "fim da suspensão", "suspensão terminou", "suspensão encerrada",
                  "novo prazo", "prazo final", "retomad", "restabelecid"):
        assert claim.casefold() not in lowered, claim
    # O comunicado publicado no próprio SISPA é outro documento.
    for other in ("COMUNICADO SISPA", "N.º 1/2026", "Comunicado SISPA"):
        assert other not in text, other


def test_update_is_declared_in_metadata_and_visible_dates():
    html = _html()
    article = _article_jsonld(html)

    assert article["datePublished"] == PUBLISHED
    assert article["dateModified"] == UPDATED
    assert datetime.fromisoformat(UPDATED) > datetime.fromisoformat(PUBLISHED)
    assert f'<time datetime="{PUBLISHED}">22/06/2026</time> às 09h20' in html
    assert f'<time datetime="{UPDATED}">{UPDATED_DAY}</time> às {UPDATED_CLOCK}' in html
    meta = html[html.index('<div class="article-meta-block">'):]
    meta = meta[:meta.index("</div>")]
    assert meta.index("Publicado em:") < meta.index("Atualizado em:") < meta.index("Autor:")
    # O tipo da matéria não muda.
    assert "article-badge-informativo" in html and "article-badge-atualizacao" not in html


def test_no_external_link_the_dou_is_cited_in_the_text():
    html = _html()
    main = html[html.index("<main>"):html.index("</main>")]

    assert re.findall(r'href="(https?://[^"]+)"', main) == []
    assert re.findall(r"<a\b[^>]*>", _body(html)) == []
    assert DOU_URL not in html and "Íntegra do Comunicado" not in html
    assert "(DOU de 19/10, Seção 3)" in _text(_body(html))
    assert "http" not in _text(_body(html))


def test_listing_card_moves_by_the_update_stamp_and_sitemap_follows():
    index = INDEX.read_text(encoding="utf-8")
    sitemap = SITEMAP.read_text(encoding="utf-8")
    cards = re.findall(r"<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>", index, re.DOTALL)
    own = [card for card in cards if f'href="{ROUTE}"' in card]

    assert index.count(f'href="{ROUTE}"') == 1 and len(own) == 1
    card = own[0]
    opening = card.split(">", 1)[0]
    # Mesmo carimbo da matéria de produtos irregulares, que vem antes na listagem.
    # 20/10/2026, 13h00: o card do SNCR, atualizado no lote 2, vem à frente dos dois.
    # 26/10/2026, 08h30: as matérias do MAPA 1.617 e do período eleitoral, atualizadas, sobem para a 1ª e a 2ª posições; as que ficavam acima delas descem duas (até a 6ª) ou uma (da 8ª à 35ª).
    assert cards.index(card) == 4
    assert f'data-updated="{UPDATED}"' in opening
    assert f'<time datetime="{UPDATED}" class="leading-none">{UPDATED_DAY} • {UPDATED_CLOCK}</time>' in card
    assert ">Informativo</span>" in card and "Ler notícia" in card
    assert 'href="http' not in card
    keywords = re.search(r'data-keywords="([^"]*)"', opening).group(1)
    assert keywords == ("MAPA, SISPA, Agrotóxicos, Sistemas oficiais, Cadastro de componentes, Produtos técnicos, "
                        "Comunicado nº 1/2026, 19/10/2026")
    items = re.findall(r'\{"@type":"ListItem","position":(\d+),"url":"([^"]+)"\}', index)
    assert items[4] == ("5", PUBLIC_URL)
    assert index.count(f'"url":"{PUBLIC_URL}"') == 1
    assert sitemap.count(f"<loc>{PUBLIC_URL}</loc>") == 1
    assert f"<loc>{PUBLIC_URL}</loc>\n    <lastmod>{UPDATED[:10]}</lastmod>" in sitemap
