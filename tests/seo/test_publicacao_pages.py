"""O que o GitHub Pages publica.

O site sai da branch main pelo build do Jekyll, sem layouts nem tema: nenhum
arquivo tem front matter, então o Jekyll só copia. O _config.yml tira do site
os testes, scripts, configurações de build e rascunhos, que continuam no
repositório. Os primeiros testes reproduzem o filtro do Jekyll (caminhos com
"." ou "_" no início e a lista exclude). O último confere a saída real do
build, gerada por scripts/gerar_site_pages.py e indicada em PAGES_SITE_DIR;
sem ela, fica como skipped.
"""
import re
import subprocess
from fnmatch import fnmatch
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

import pytest

from support import ROOT, SITE_DIR, public_html_paths


CONFIG_PATH = ROOT / "_config.yml"
NOT_PUBLISHED = (
    "tests/README.md",
    "tests/support.py",
    "tests/seo/test_publicacao_pages.py",
    "scripts/importar-vagas-farmacia-popular.py",
    "pytest.ini",
    "tailwind.config.js",
    "noticias/template-noticia.html",
    "noticias/a-publicar/rascunho/index.html",
    ".gitignore",
    "tests/__pycache__/support.cpython-313.pyc",
)
PUBLISHED = (
    "index.html",
    "CNAME",
    "ads.txt",
    "robots.txt",
    "sitemap.xml",
    "whatsapp/index.html",
    "data/farmacia-popular/metadados.json",
    "data/farmacia-popular/vagas-2026-09-03.json",
    "assets/fonts/OFL.txt",
)


def _exclude_patterns():
    text = CONFIG_PATH.read_text(encoding="utf-8")
    block = re.search(r"^exclude:\n((?:[ \t]+-[^\n]*\n?)+)", text, re.MULTILINE)
    assert block is not None, "_config.yml sem lista exclude"
    return [line.split("-", 1)[1].strip().strip("'\"") for line in block.group(1).splitlines()]


def _published(relative_path, patterns):
    """Mesmo critério do Jekyll 3: partes iniciadas por . _ # ~ e a lista exclude."""
    if any(part[:1] in "._#~" for part in relative_path.split("/")):
        return False
    return not any(fnmatch(relative_path, pattern) or relative_path.startswith(pattern) for pattern in patterns)


def _site_files():
    """Arquivos do repositório, sem as pastas locais ocultas (.git, .venv, .vscode)."""
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT).as_posix()
        if path.is_file() and not any(part.startswith(".") for part in relative.split("/")[:-1]):
            yield relative


def test_jekyll_runs_and_only_copies_files():
    assert CONFIG_PATH.is_file()
    assert not (ROOT / ".nojekyll").exists(), ".nojekyll desliga o Jekyll e publica a lista exclude"
    assert re.search(r"^theme:\s*null\s*$", CONFIG_PATH.read_text(encoding="utf-8"), re.MULTILINE), (
        "sem theme: null, o tema padrão do GitHub Pages acrescenta assets/css/style.css"
    )
    patterns = _exclude_patterns()
    for relative in _site_files():
        if not _published(relative, patterns):
            continue
        with open(ROOT / relative, "rb") as handle:
            head = handle.read(6).removeprefix(b"\xef\xbb\xbf")
        assert not head.startswith(b"---"), f"{relative}: front matter faria o Jekyll processar o arquivo"
        assert not relative.endswith((".md", ".markdown", ".scss", ".sass")), (
            f"{relative}: o Jekyll converteria este arquivo publicado"
        )


def test_tests_scripts_and_drafts_stay_out_of_the_site():
    patterns = _exclude_patterns()
    for relative in NOT_PUBLISHED:
        assert not _published(relative, patterns), f"{relative} seria publicado"
    for relative in _site_files():
        if relative.startswith(("tests/", "scripts/")) or relative.endswith((".py", ".pyc", ".ini")):
            assert not _published(relative, patterns), f"{relative} seria publicado"


class _ResourceParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        values = [attributes.get(name) for name in ("href", "src")]
        values += [item.split()[0] for item in (attributes.get("srcset") or "").split(",") if item.strip()]
        for value in values:
            parts = urlsplit(value or "")
            if not parts.scheme and parts.path.startswith("/") and not value.startswith("//"):
                path = unquote(parts.path).lstrip("/")
                self.paths.append(path + "index.html" if not path or path.endswith("/") else path)


def test_pages_assets_data_and_downloads_stay_published():
    patterns = _exclude_patterns()
    for relative in PUBLISHED:
        assert (ROOT / relative).is_file(), relative
        assert _published(relative, patterns), f"{relative} sairia do site"

    namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    for location in ET.parse(ROOT / "sitemap.xml").getroot().findall("s:url/s:loc", namespace):
        relative = urlsplit(location.text).path.lstrip("/") + "index.html"
        assert _published(relative, patterns), f"{relative} está no sitemap e sairia do site"

    for path in public_html_paths():
        parser = _ResourceParser()
        parser.feed(path.read_text(encoding="utf-8"))
        for relative in parser.paths:
            assert _published(relative, patterns), (
                f"{path.relative_to(ROOT).as_posix()} usa {relative}, que sairia do site"
            )

    for relative in _site_files():
        if relative.endswith((".pdf", ".json", ".webp", ".png", ".jpg", ".woff2", ".css", ".js")):
            if relative != "tailwind.config.js" and not relative.startswith(("tests/", "scripts/")):
                assert _published(relative, patterns), f"{relative} sairia do site"


def _publishable_tree():
    """Arquivos que entrariam num commit agora: rastreados e novos não ignorados."""
    listed = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT, capture_output=True, check=True,
    ).stdout.decode("utf-8").split("\0")
    return {path for path in listed if path and (ROOT / path).is_file()}


@pytest.mark.skipif(
    SITE_DIR == ROOT,
    reason="build do GitHub Pages não executado: gere com scripts/gerar_site_pages.py e defina PAGES_SITE_DIR",
)
def test_generated_site_is_the_publishable_tree_without_exclusions():
    patterns = _exclude_patterns()
    expected = {path for path in _publishable_tree() if _published(path, patterns)}
    generated = {path.relative_to(SITE_DIR).as_posix() for path in SITE_DIR.rglob("*") if path.is_file()}

    assert not generated - expected, f"o build acrescentou arquivos: {sorted(generated - expected)}"
    assert not expected - generated, f"o build deixou de fora: {sorted(expected - generated)}"
    assert not generated & set(NOT_PUBLISHED), sorted(generated & set(NOT_PUBLISHED))
    assert set(PUBLISHED) <= generated, sorted(set(PUBLISHED) - generated)

    # O checkout do GitHub entrega LF; o working tree no Windows pode ter CRLF.
    normalized = lambda path: path.read_bytes().replace(b"\r\n", b"\n")
    changed = sorted(path for path in expected if normalized(SITE_DIR / path) != normalized(ROOT / path))
    assert not changed, f"conteúdo alterado pelo build: {changed[:10]}"
