import datetime
import decimal
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).parents[1]
SITEMAP_PATH = ROOT / "sitemap.xml"
PUBLIC_URL = "https://www.regularizeconsultorias.com.br/farmacia-popular/"
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

    assert root.tag == f"{{{NAMESPACE}}}urlset"
    assert len(urls) == 77
    assert all(location and location.strip() for location in locations)
    assert len(locations) == len(set(locations))


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


def test_farmacia_popular_has_expected_sitemap_metadata():
    _, urls = _url_elements()
    matches = [url for url in urls if url.findtext("s:loc", namespaces=NS) == PUBLIC_URL]

    assert len(matches) == 1
    assert matches[0].findtext("s:lastmod", namespaces=NS) == "2026-08-06"
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


def test_pops_drogaria_has_expected_sitemap_metadata():
    _, urls = _url_elements()
    matches = [url for url in urls if url.findtext("s:loc", namespaces=NS) == POPS_DROGARIA_URL]

    assert len(matches) == 1
    assert matches[0].findtext("s:lastmod", namespaces=NS) == "2026-08-06"
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
    assert "<main" in page_content.casefold()
    assert "<h1" in page_content.casefold()
    assert len(re.sub(r"<[^>]+>", " ", page_content).split()) > 100
    assert page_path.parent.resolve() == (ROOT / route_path).resolve()
