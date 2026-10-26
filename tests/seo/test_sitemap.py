import datetime
import decimal
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from support import public_html_paths


ROOT = Path(__file__).parents[2]
SITEMAP_PATH = ROOT / "sitemap.xml"
PUBLIC_URL = "https://www.regularizeconsultorias.com.br/farmacia-popular/"
NEWS_INDEX_URL = "https://www.regularizeconsultorias.com.br/noticias/"
COMUNICADO_URL = "https://www.regularizeconsultorias.com.br/comunicado/"
PORTARIA_NEWS_URL = "https://www.regularizeconsultorias.com.br/noticias/farmacia-popular-portaria-12091-2026-novas-regras/"
POPS_DROGARIA_URL = "https://www.regularizeconsultorias.com.br/manuais-e-pops/pops-drogaria/"
NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"
NS = {"s": NAMESPACE}


def _url_elements():
    root = ET.parse(SITEMAP_PATH).getroot()
    return root, root.findall("s:url", NS)


class _MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonicals = []
        self.robots = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag.casefold() == "link" and "canonical" in attributes.get("rel", "").casefold().split():
            self.canonicals.append(attributes.get("href", ""))
        if tag.casefold() == "meta" and attributes.get("name", "").casefold() == "robots":
            self.robots.append(attributes.get("content", ""))


def test_sitemap_is_valid_xml_with_unique_urls():
    root, urls = _url_elements()
    locations = [url.findtext("s:loc", namespaces=NS) for url in urls]
    public_canonicals = set()
    for path in public_html_paths():
        parser = _MetadataParser()
        parser.feed(path.read_text(encoding="utf-8"))
        assert len(parser.canonicals) == 1, path.relative_to(ROOT)
        public_canonicals.add(parser.canonicals[0])

    assert root.tag == f"{{{NAMESPACE}}}urlset"
    assert all(location and location.strip() for location in locations)
    assert len(locations) == 106
    assert len(locations) == len(set(locations))
    assert set(locations) == public_canonicals


def test_sitemap_urls_and_metadata_follow_the_protocol():
    _, urls = _url_elements()
    allowed_frequencies = {"always", "hourly", "daily", "weekly", "monthly", "yearly", "never"}

    for url in urls:
        location = url.findtext("s:loc", namespaces=NS)
        parsed = urlsplit(location)
        lastmod = url.findtext("s:lastmod", namespaces=NS)
        changefreq = url.findtext("s:changefreq", namespaces=NS)
        priority_text = url.findtext("s:priority", namespaces=NS)

        assert parsed.scheme == "https"
        assert parsed.netloc == "www.regularizeconsultorias.com.br"
        assert parsed.path.endswith("/")
        assert not parsed.query
        assert not parsed.fragment
        assert not parsed.path.endswith(".html")
        assert lastmod is not None and re.fullmatch(r"\d{4}-\d{2}-\d{2}", lastmod)
        datetime.date.fromisoformat(lastmod)
        assert changefreq in allowed_frequencies
        priority = decimal.Decimal(priority_text)
        assert decimal.Decimal("0.0") <= priority <= decimal.Decimal("1.0")

        route_path = parsed.path.strip("/")
        page_path = ROOT / route_path / "index.html" if route_path else ROOT / "index.html"
        relative_path = page_path.relative_to(ROOT).as_posix()
        assert page_path.is_file(), f"Sitemap URL sem arquivo local: {relative_path}"

        parser = _MetadataParser()
        parser.feed(page_path.read_text(encoding="utf-8"))
        assert all(
            "noindex" not in content.casefold() for content in parser.robots
        ), f"noindex em URL do sitemap: {relative_path}"
        assert all(
            "nofollow" not in content.casefold() for content in parser.robots
        ), f"nofollow em URL do sitemap: {relative_path}"
        if parser.canonicals:
            assert location in parser.canonicals, (
                f"Canonical divergente em URL do sitemap: {relative_path}"
            )


def test_farmacia_popular_has_expected_sitemap_metadata():
    _, urls = _url_elements()
    matches = [url for url in urls if url.findtext("s:loc", namespaces=NS) == PUBLIC_URL]

    assert len(matches) == 1
    # 13/10/2026: a página ganhou o link visível da fonte oficial. A base de vagas continua a de 09/10/2026.
    # 16/10/2026: correção do conteúdo apresentado sem JavaScript (explicações no lugar do carregamento).
    assert matches[0].findtext("s:lastmod", namespaces=NS) == "2026-10-16"
    assert matches[0].findtext("s:changefreq", namespaces=NS) == "monthly"
    assert matches[0].findtext("s:priority", namespaces=NS) == "0.9"


def test_farmacia_popular_public_page_matches_canonical():
    route_path = urlsplit(PUBLIC_URL).path.strip("/")
    page_path = ROOT / route_path / "index.html"
    assert page_path.is_file()

    parser = _MetadataParser()
    parser.feed(page_path.read_text(encoding="utf-8"))

    assert PUBLIC_URL in parser.canonicals
    assert all(not canonical.endswith(".html") for canonical in parser.canonicals)
    assert all("noindex" not in content.casefold() for content in parser.robots)
    assert page_path.parent.resolve() == (ROOT / route_path).resolve()


def test_portaria_news_news_index_and_comunicado_have_expected_sitemap_metadata():
    _, urls = _url_elements()
    by_location = {url.findtext("s:loc", namespaces=NS): url for url in urls}

    # 13/10/2026: a listagem reordenou três matérias. 16/10/2026: o aviso PF de 15/10 passou ao histórico do comunicado.
    # 16/10/2026, 20h06: a listagem ganhou o card do CNES 10/2026.
    # 17/10/2026, 09h50: a listagem ganhou o card do esclarecimento do Farmácia Popular.
    # 20/10/2026, 10h12: a listagem reordenou os cards de produtos irregulares e do SISPA, atualizados no mesmo dia.
    # 21/10/2026, 17h45: a listagem reordenou o card de produtos irregulares (RE nº 4.140/2026).
    # 22/10/2026: a listagem reordenou os cards de produtos irregulares e do SNCR, atualizados no mesmo lote.
    # 26/10/2026: a listagem reordenou os cards do MAPA 1.617 e do período eleitoral, atualizados no mesmo lote.
    assert by_location[NEWS_INDEX_URL].findtext("s:lastmod", namespaces=NS) == "2026-10-26"
    # 17/10/2026, 09h50: Comunicados ganhou o aviso informativo do Farmácia Popular.
    # 19/10/2026, 15h40: Comunicados ganhou o aviso informativo da instabilidade nos sistemas da Anvisa.
    # 20/10/2026: o aviso da instabilidade na Anvisa passou ao histórico.
    # 26/10/2026: os avisos do MAPA (marco de 23/10) e do período eleitoral do Farmácia Popular passaram ao histórico.
    assert by_location[COMUNICADO_URL].findtext("s:lastmod", namespaces=NS) == "2026-10-26"
    assert by_location[PORTARIA_NEWS_URL].findtext("s:lastmod", namespaces=NS) == "2026-10-09"
    assert by_location[PORTARIA_NEWS_URL].findtext("s:changefreq", namespaces=NS) == "monthly"
    assert by_location[PORTARIA_NEWS_URL].findtext("s:priority", namespaces=NS) == "0.8"


def test_pops_drogaria_has_expected_sitemap_metadata():
    _, urls = _url_elements()
    matches = [url for url in urls if url.findtext("s:loc", namespaces=NS) == POPS_DROGARIA_URL]

    assert len(matches) == 1
    assert matches[0].findtext("s:lastmod", namespaces=NS) == "2026-09-04"
    assert matches[0].findtext("s:changefreq", namespaces=NS) == "monthly"
    assert matches[0].findtext("s:priority", namespaces=NS) == "0.7"

    route_path = urlsplit(POPS_DROGARIA_URL).path.strip("/")
    page_path = ROOT / route_path / "index.html"
    assert page_path.is_file()

    page_content = page_path.read_text(encoding="utf-8")
    parser = _MetadataParser()
    parser.feed(page_content)

    assert POPS_DROGARIA_URL in parser.canonicals
    assert all("noindex" not in canonical.casefold() for canonical in parser.canonicals)
    assert all("noindex" not in content.casefold() for content in parser.robots)
    assert all("nofollow" not in content.casefold() for content in parser.robots)
    assert "<main" in page_content.casefold()
    assert "<h1" in page_content.casefold()
    assert len(re.sub(r"<[^>]+>", " ", page_content).split()) > 100
    assert page_path.parent.resolve() == (ROOT / route_path).resolve()
