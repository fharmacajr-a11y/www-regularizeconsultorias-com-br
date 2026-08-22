from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).parents[1]
NEWS_PATH = ROOT / "noticias" / "credenciamento-farmacia-popular-municipios-com-vagas" / "index.html"
NEWS_INDEX_PATH = ROOT / "noticias" / "index.html"
SITEMAP_PATH = ROOT / "sitemap.xml"
URL = "https://www.regularizeconsultorias.com.br/noticias/credenciamento-farmacia-popular-municipios-com-vagas/"
PUBLISHED = "2026-05-22T23:30:00-03:00"
UPDATED = "2026-08-22T12:09:22-03:00"


def test_credenciamento_news_uses_the_current_municipalities_list():
    html = NEWS_PATH.read_text(encoding="utf-8")

    assert f'"datePublished": "{PUBLISHED}"' in html
    assert f'"dateModified": "{UPDATED}"' in html
    assert datetime.fromisoformat(UPDATED) > datetime.fromisoformat(PUBLISHED)
    assert "Versão da lista utilizada nesta notícia: 20/08/2026" in html
    assert "1.206 municípios" in html
    assert "1.780 vagas totais" in html
    assert "10 preenchidas" in html
    assert "1.770 disponíveis" in html
    assert "data-news-update-callout" in html
    assert "ATUALIZAÇÃO" in html
    assert 'href="./farmacia-popular-municipios-vagas-20-08-2026.pdf"' in html
    assert 'href="./farmacia-popular-municipios-vagas-28-07-2026.pdf"' not in html


def test_credenciamento_news_is_unique_and_current_in_listing_and_sitemap():
    news_index = NEWS_INDEX_PATH.read_text(encoding="utf-8")
    sitemap = SITEMAP_PATH.read_text(encoding="utf-8")

    assert news_index.count('href="/noticias/credenciamento-farmacia-popular-municipios-com-vagas/"') == 1
    assert f'data-updated="{UPDATED}"' in news_index
    assert "22/08/2026 • 12h09" in news_index
    assert sitemap.count(f"<loc>{URL}</loc>") == 1
    assert f"<loc>{URL}</loc>\n    <lastmod>2026-08-22</lastmod>" in sitemap
