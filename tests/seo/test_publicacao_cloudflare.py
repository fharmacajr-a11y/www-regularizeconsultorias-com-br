"""O que a Cloudflare Pages publica (scripts/montar_site_cloudflare.py).

O comando de build da Cloudflare monta a pasta publicada com o mesmo filtro do
Jekyll no GitHub Pages, sem o CNAME e com o _headers. Sem um 404.html na raiz,
a Cloudflare Pages trataria o site como aplicação de página única e responderia
qualquer endereço inexistente com a home e status 200.
"""
import importlib.util
import re

from support import ROOT


SCRIPT = ROOT / "scripts" / "montar_site_cloudflare.py"
_spec = importlib.util.spec_from_file_location("montar_site_cloudflare", SCRIPT)
montar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(montar)

FORA_DO_SITE = (
    "CLAUDE.md",
    "CNAME",
    "_config.yml",
    "_headers",
    ".gitignore",
    "pytest.ini",
    "tailwind.config.js",
    "noticias/template-noticia.html",
    "tests/support.py",
    "scripts/montar_site_cloudflare.py",
)
NO_SITE = (
    "index.html",
    "404.html",
    "ads.txt",
    "robots.txt",
    "sitemap.xml",
    "whatsapp/index.html",
    "data/farmacia-popular/metadados.json",
    "assets/fonts/OFL.txt",
)


def test_build_uses_the_jekyll_filter_without_cname():
    files = set(montar.site_files())
    for relative in NO_SITE:
        assert relative in files, f"{relative} ficaria fora do site"
    for relative in FORA_DO_SITE:
        assert relative not in files, f"{relative} seria publicado"
    assert not any(path.startswith(("tests/", "scripts/", "noticias/a-publicar")) for path in files)
    patterns = montar.exclude_patterns()
    for relative in montar.tracked_files():
        expected = montar.published(relative, patterns) and relative != "CNAME"
        assert (relative in files) == expected, relative


def test_404_page_exists_and_is_noindex():
    html = (ROOT / "404.html").read_text(encoding="utf-8")
    assert re.search(r'<meta name="robots" content="noindex"', html)
    assert 'rel="canonical"' not in html
    assert "adsbygoogle" not in html, "a política do AdSense não aceita anúncio em página de erro"
    for href in re.findall(r'(?:href|src)="([^"#]+)"', html):
        assert href.startswith(("/", "https://", "mailto:")), f"404.html precisa de caminho absoluto: {href}"


def _header_rules():
    rules, current = {}, None
    for line in (ROOT / "_headers").read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith((" ", "\t")):
            current = line.strip()
            rules[current] = {}
        else:
            name, value = line.strip().split(":", 1)
            rules[current][name.strip().lower()] = value.strip()
    return rules


def test_security_headers_for_the_whole_site():
    headers = _header_rules()["/*"]
    assert headers["strict-transport-security"].startswith("max-age=31536000")
    assert "preload" not in headers["strict-transport-security"]
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "SAMEORIGIN"
    assert headers["content-security-policy"] == "frame-ancestors 'self'", (
        "CSP de scripts quebraria o AdSense e os scripts embutidos nas páginas"
    )
    assert headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in headers["permissions-policy"]


def test_pages_dev_address_stays_out_of_search():
    assert _header_rules()["https://:project.pages.dev/*"] == {"x-robots-tag": "noindex"}
