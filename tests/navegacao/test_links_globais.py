"""Links internos, recursos locais, âncoras e IDs de todas as páginas públicas.

Lê o HTML do repositório: cada href, src, srcset e og:image local precisa
apontar para um arquivo que existe, cada #fragmento para um id da página de
destino, e nenhuma página repete um id.
"""
from collections import Counter
from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urlsplit

from support import ROOT, public_html_paths


HOST = "www.regularizeconsultorias.com.br"


class _ReferenceParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.references = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        line = self.getpos()[0]
        if attributes.get("id"):
            self.ids.append(attributes["id"])
        for name in ("href", "src", "data-aviso-image-src"):
            if attributes.get(name):
                self.references.append((tag, name, attributes[name].strip(), line))
        for candidate in (attributes.get("srcset") or "").split(","):
            if candidate.strip():
                self.references.append((tag, "srcset", candidate.split()[0], line))
        if tag == "meta" and attributes.get("property") in ("og:image", "og:url") and attributes.get("content"):
            self.references.append((tag, "content", attributes["content"].strip(), line))


def _parse(path):
    parser = _ReferenceParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def _route(path):
    relative = path.relative_to(ROOT).as_posix()
    return "/" + relative[: -len("index.html")] if relative.endswith("index.html") else "/" + relative


def _local_target(route, value):
    """Caminho local de destino, ou None para links externos e esquemas como mailto:."""
    parts = urlsplit(value)
    if parts.scheme in ("http", "https"):
        return (parts.path or "/", parts.fragment) if parts.netloc == HOST else None
    if parts.scheme or value.startswith("//"):
        return None
    if not parts.path:
        return route, parts.fragment
    if parts.path.startswith("/"):
        return parts.path, parts.fragment
    base = route if route.endswith("/") else route.rsplit("/", 1)[0] + "/"
    segments = []
    for segment in (base + parts.path).split("/"):
        if segment == "..":
            segments.pop()
        elif segment != ".":
            segments.append(segment)
    return "/".join(segments), parts.fragment


def _file_for(target_path):
    relative = unquote(target_path).lstrip("/")
    if not relative or target_path.endswith("/"):
        candidate = ROOT / relative / "index.html"
    else:
        candidate = ROOT / relative
    return candidate if candidate.is_file() else None


PAGES = {_route(path): (path, _parse(path)) for path in public_html_paths()}


def test_pages_do_not_repeat_ids():
    for route, (_, parser) in PAGES.items():
        repeated = sorted(name for name, count in Counter(parser.ids).items() if count > 1)
        assert not repeated, f"{route}: ids repetidos {repeated}"


def test_internal_references_resolve_to_existing_files():
    failures = []
    for route, (_, parser) in PAGES.items():
        for tag, attribute, value, line in parser.references:
            target = _local_target(route, value)
            if target is None:
                continue
            target_path, _ = target
            if _file_for(target_path) is None:
                failures.append(f"{route}:{line} <{tag} {attribute}> {value}")
            elif tag == "a" and not target_path.endswith("/") and (ROOT / target_path.lstrip("/")).is_dir():
                failures.append(f"{route}:{line} pasta sem barra final: {value}")
    assert not failures, "\n".join(failures)


def test_fragments_point_to_existing_ids():
    failures = []
    checked = 0
    for route, (_, parser) in PAGES.items():
        for tag, attribute, value, line in parser.references:
            target = _local_target(route, value) if tag == "a" else None
            if not target or not target[1]:
                continue
            target_route = target[0]
            checked += 1
            if target_route not in PAGES:
                failures.append(f"{route}:{line} âncora para página não pública: {value}")
            elif unquote(target[1]) not in PAGES[target_route][1].ids:
                failures.append(f"{route}:{line} âncora sem id de destino: {value}")
    assert checked, "nenhum link com âncora encontrado; o teste perdeu o alvo"
    assert not failures, "\n".join(failures)


def test_whatsapp_links_use_the_redirect_page_with_a_readable_message():
    redirect = (ROOT / "whatsapp" / "index.html").read_text(encoding="utf-8")
    assert "const phone = '5519996275900';" in redirect
    assert "encodeURIComponent(text)" in redirect

    failures = []
    for route, (_, parser) in PAGES.items():
        for tag, _, value, line in parser.references:
            parts = urlsplit(value)
            if tag != "a":
                continue
            if parts.netloc in ("wa.me", "api.whatsapp.com"):
                failures.append(f"{route}:{line} link direto ao WhatsApp, fora de /whatsapp/: {value}")
            elif parts.path == "/whatsapp/" and parts.query:
                texts = parse_qs(parts.query).get("text", [])
                if len(texts) != 1 or not texts[0].strip() or "�" in texts[0]:
                    failures.append(f"{route}:{line} mensagem do WhatsApp ilegível: {value}")
    assert not failures, "\n".join(failures)
