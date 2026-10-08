"""Títulos da listagem fluem na largura do card.

A quebra incondicional não pode voltar no destaque nem no compacto.
A reserva da coluna fixa é uma regra do componente, não de uma matéria,
de uma posição ou de um título curto. O teste não exige uma ou duas linhas.
"""
import re

from support import ROOT


LISTING = ROOT / "noticias" / "index.html"
CSS = ROOT / "assets" / "css" / "pages" / "noticias.css"
CARD = re.compile(r'<article class="news-card\b.*?</article>', re.S)
H2 = re.compile(r"<h2\b[^>]*>(.*?)</h2>", re.S)
SUMMARY = re.compile(r"<p\b[^>]*>(.*?)</p>", re.S)


def _cards():
    html = LISTING.read_text(encoding="utf-8")
    return CARD.findall(html)


def test_nenhum_titulo_ou_resumo_tem_quebra_incondicional():
    cards = _cards()
    assert len(cards) == 83
    featured = [card for card in cards if "news-card-compact" not in card.split(">", 1)[0]]
    compact = [card for card in cards if "news-card-compact" in card.split(">", 1)[0]]
    assert len(featured) == 5
    assert len(compact) == 78
    for card in cards:
        title = re.search(r'data-title="([^"]*)"', card).group(1)
        h2 = H2.search(card).group(1)
        summary = SUMMARY.search(card).group(1)
        assert "<br" not in h2.casefold()
        assert "<br" not in summary.casefold()
        visible = " ".join(re.sub(r"<[^>]+>", " ", h2).split())
        assert visible == title
        assert "…" not in visible and "..." not in visible


def test_hero_modular_reserva_a_faixa_do_botao():
    css = (ROOT / "assets" / "css" / "pages" / "noticia-detalhe.css").read_text(encoding="utf-8")
    assert ".article-hero-atualizacao :is(h1, p)" in css
    assert "line-clamp" not in css
    linked = []
    for page in (ROOT / "noticias").rglob("index.html"):
        text = page.read_text(encoding="utf-8")
        if "noticia-detalhe.css" not in text:
            continue
        linked.append(text)
        assert "noticia-detalhe.css?v=20261007-hero-1" in text
        assert "noticia-detalhe.css?v=20261005-tipos-1" not in text
    assert len(linked) == 29


def test_reserva_da_coluna_e_do_componente():
    css = CSS.read_text(encoding="utf-8")
    assert "#news-article-list .news-card :is(h2, p)" in css
    assert "line-clamp" not in css
    assert "-webkit-line-clamp" not in css
    assert "text-overflow" not in css
    assert "nth-child" not in css
    assert ".news-card-compact h2" in css
    compact = css.split(".news-card-compact h2", 1)[1].split("}", 1)[0]
    assert "1.25rem" in compact
    assert "max-width: 1359px" in css
    assert "max-width: 640px" in css
