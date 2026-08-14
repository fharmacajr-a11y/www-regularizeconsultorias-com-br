import re
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEWS_INDEX_PATH = ROOT / "noticias" / "index.html"
ALTERACAO_CADASTRAL_URL = "https://www.regularizeconsultorias.com.br/noticias/alteracao-cadastral-farmacia-popular-regularizacao/"
PORTARIA_URL = "https://www.regularizeconsultorias.com.br/noticias/farmacia-popular-portaria-12091-2026-novas-regras/"

def test_news_index_sorting_rule_and_attributes():
    html = NEWS_INDEX_PATH.read_text(encoding="utf-8")

    article_match = re.search(r'(<article[^>]*?data-title="Alteração cadastral no Farmácia Popular exige atenção para evitar pendências no programa"[^>]*?>.*?)</article>', html, re.DOTALL)
    assert article_match is not None, "Article not found in HTML"
    article_html = article_match.group(1)

    assert 'data-updated="2026-08-14T09:04:41-03:00"' in article_html, "data-updated attribute missing or incorrect"
    assert '<time datetime="2026-05-22T23:30:00-03:00"' in article_html, "Original datePublished was falsified in the <time> tag"

def test_news_index_itemlist_ordering():
    html = NEWS_INDEX_PATH.read_text(encoding="utf-8")
    json_pattern = re.compile(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', re.DOTALL)

    items = []
    for match in json_pattern.finditer(html):
        try:
            data = json.loads(match.group(1))
            if data.get("@type") == "CollectionPage" and "mainEntity" in data:
                main_entity = data["mainEntity"]
                if main_entity.get("@type") == "ItemList" and "itemListElement" in main_entity:
                    items = main_entity["itemListElement"]
                    break
        except Exception:
            pass

    assert items, "ItemList is empty"
    urls = [item.get("url") for item in items]

    assert urls[0] == ALTERACAO_CADASTRAL_URL, "Alteracao Cadastral should be at position 1 in JSON-LD"
    assert PORTARIA_URL in urls, "Portaria is missing from JSON-LD"
    assert urls.index(PORTARIA_URL) > urls.index(ALTERACAO_CADASTRAL_URL), "Portaria should appear after Alteracao Cadastral"
