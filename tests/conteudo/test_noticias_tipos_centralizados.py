"""Atualização, Informativo, Urgente e Orientação: cores num arquivo só, sem sobreposição.

As cores desses tipos ficavam em cinco lugares (pages/noticias.css, um <style>
dentro da listagem, noticia-detalhe.css, custom.css/custom.min.css e
utilitários de cor no HTML dos artigos), e as sobreposições davam cores
diferentes entre o card grande, o compacto e o artigo. Desde 05/10/2026 elas
ficam só em assets/css/pages/noticias-tipos.css. O teste confere que:

- toda página de notícia e o template carregam esse arquivo, depois dos outros CSS;
- nenhuma outra folha (nem <style> das páginas) dá cor, fundo, borda ou sombra às
  classes de tipo;
- selos, botões e cabeçalhos desses tipos não levam utilitários de cor no HTML;
- a paleta do arquivo tem 4,5:1 entre o texto e cada fundo (normal e hover/foco).
"""
import re

from support import ROOT, parse_html

CENTRAL = ROOT / "assets" / "css" / "pages" / "noticias-tipos.css"
NEWS_PAGES = sorted([ROOT / "noticias" / "index.html", ROOT / "noticias" / "template-noticia.html",
                     *(ROOT / "noticias").glob("*/index.html")])
TYPE_CLASSES = (
    "news-amber-badge", "news-amber-button", "news-amber-card",
    "news-orange-badge", "news-orange-button", "news-orange-card",
    "news-urgent-badge", "news-urgent-button", "news-urgent-card",
    "news-orientacao-badge", "news-orientacao-button", "news-card--orientation",
    "article-badge-atualizacao", "article-hero-atualizacao",
    "article-badge-informativo", "article-hero-informativo",
    "article-badge-urgente", "article-hero-urgente",
    "article-badge-orientacao", "article-hero-orientacao",
)
PAINT = re.compile(r"(?:^|;)\s*(color|background(?:-color|-image)?|border(?:-[a-z]+)?-color|border-color|box-shadow)\s*:", re.I)
COLOR_UTILITY = re.compile(r"^(?:[a-z]+:)*(?:bg|text|from|via|to|border)-(?:amber|orange|yellow|red|white|black|slate|brand|blue|sky|cyan|indigo)(?:-|/|$)")
CSS_LINK = re.compile(r'<link[^>]*href="(/assets/css/[^"?]+)(\?[^"]*)?"[^>]*>')


def _rules(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return re.findall(r"([^{}]+)\{([^{}]*)\}", css)


def _type_selector(selector):
    """A regra mira uma classe de tipo (fora de :not(...))?"""
    without_not = re.sub(r":not\([^()]*(?:\([^()]*\))?[^()]*\)", "", selector)
    return any(re.search(rf"\.{name}(?![\w-])", without_not) for name in TYPE_CLASSES)


def _luminance(hexcolor):
    channels = [int(hexcolor[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _ratio(a, b):
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def test_every_news_page_and_the_template_load_the_central_file_last():
    missing = []
    for page in NEWS_PAGES:
        html = page.read_text(encoding="utf-8")
        head = html[: html.index("</head>")]
        links = CSS_LINK.findall(head)
        names = [href for href, _ in links]
        if "/assets/css/pages/noticias-tipos.css" not in names:
            missing.append(f"{page.relative_to(ROOT)}: sem noticias-tipos.css")
        elif names[-1] != "/assets/css/pages/noticias-tipos.css":
            missing.append(f"{page.relative_to(ROOT)}: noticias-tipos.css não é o último CSS ({names})")
    assert len(NEWS_PAGES) > 80
    assert not missing, "\n".join(missing[:20])


def test_no_other_stylesheet_paints_the_type_classes():
    offenders = []
    sheets = [p for p in (ROOT / "assets" / "css").rglob("*.css") if p != CENTRAL and p.name != "tailwind.min.css"]
    sources = [(p.relative_to(ROOT).as_posix(), p.read_text(encoding="utf-8-sig")) for p in sheets]
    for page in NEWS_PAGES:
        for block in re.findall(r"<style[^>]*>(.*?)</style>", page.read_text(encoding="utf-8"), re.S):
            sources.append((f"{page.relative_to(ROOT).as_posix()} <style>", block))
    for name, css in sources:
        for selector, body in _rules(css):
            if not _type_selector(selector):
                continue
            # O foco branco sobre fundos escuros (components/custom) só troca o contorno.
            if ":focus-visible" in selector and not PAINT.search(body.replace("outline-color", "outline")):
                continue
            if PAINT.search(body):
                offenders.append(f"{name}: {' '.join(selector.split())[:120]}")
    assert not offenders, "cor de tipo fora de noticias-tipos.css:\n" + "\n".join(offenders)


def _walk(node):
    yield node
    for child in getattr(node, "children", []):
        yield from _walk(child)


def test_type_badges_buttons_and_headers_have_no_color_utilities():
    """Selos, botões e cabeçalhos achados pelo papel (não pela classe nova)."""
    offenders, checked = [], 0
    expected = {
        "news-amber-card": ("news-amber-badge", "news-amber-button"),
        "news-orange-card": ("news-orange-badge", "news-orange-button"),
        "news-urgent-card": ("news-urgent-badge", "news-urgent-button"),
        "news-card--orientation": ("news-orientacao-badge", "news-orientacao-button"),
    }
    for card in _walk(parse_html(ROOT / "noticias" / "index.html")):
        classes = set(getattr(card, "attrs", {}).get("class", "").split())
        kind = next((k for k in expected if k in classes), None)
        if getattr(card, "tag", None) != "article" or not kind:
            continue
        spans = [n for n in _walk(card) if getattr(n, "tag", None) == "span"]
        links = [n for n in _walk(card) if getattr(n, "tag", None) == "a" and n.attrs.get("href", "").startswith("/noticias/")]
        for node, semantic in ((spans[0], expected[kind][0]), (links[-1], expected[kind][1])):
            checked += 1
            node_classes = node.attrs.get("class", "").split()
            bad = [c for c in node_classes if COLOR_UTILITY.match(c)]
            if bad or semantic not in node_classes:
                offenders.append(f"noticias/index.html {links[-1].attrs.get('href')}: {semantic}? {node_classes}")
    hero = re.compile(r"<main>\s*<article>\s*<header\s+class=\"([^\"]*)\"(.*?)</header>", re.S)
    badge = re.compile(r'<span class="([^"]*)">\s*(Atualização|ATUALIZAÇÃO|Informativo|INFORMATIVO|Urgente|URGENTE|Orientação|ORIENTAÇÃO)\s*</span>')
    for page in NEWS_PAGES:
        if page.name != "index.html" or page.parent.name == "noticias":
            continue
        match = hero.search(page.read_text(encoding="utf-8"))
        found = match and badge.search(match.group(2))
        if not found:
            continue
        tag_text = found.group(2).lower()
        if tag_text.startswith("atualiza"):
            kind = "atualizacao"
        elif tag_text.startswith("informativo"):
            kind = "informativo"
        elif tag_text.startswith("urgente"):
            kind = "urgente"
        else:
            kind = "orientacao"
        for node_classes, semantic in ((match.group(1).split(), f"article-hero-{kind}"), (found.group(1).split(), f"article-badge-{kind}")):
            checked += 1
            bad = [c for c in node_classes if COLOR_UTILITY.match(c) or re.match(r"^bg-gradient-to-", c)]
            if bad or semantic not in node_classes:
                offenders.append(f"{page.relative_to(ROOT)}: {semantic}? {node_classes}")

    # Cabeçalho e selo ativos do template-noticia.html (ignorando comentários)
    tpl_raw = (ROOT / "noticias" / "template-noticia.html").read_text(encoding="utf-8")
    tpl_clean = re.sub(r"<!--.*?-->", "", tpl_raw, flags=re.S)
    tpl_match = hero.search(tpl_clean)
    assert tpl_match, "cabeçalho ativo não encontrado em template-noticia.html (fora de comentários)"
    tpl_found = badge.search(tpl_match.group(2))
    assert tpl_found, "selo de tipo ativo não encontrado no cabeçalho de template-noticia.html (fora de comentários)"
    tpl_hero_classes = tpl_match.group(1).split()
    tpl_badge_classes = tpl_found.group(1).split()
    checked += 2
    if "article-hero-informativo" not in tpl_hero_classes:
        offenders.append(f"template-noticia.html: esperado article-hero-informativo no cabeçalho ativo, obtido {tpl_hero_classes}")
    if "article-badge-informativo" not in tpl_badge_classes:
        offenders.append(f"template-noticia.html: esperado article-badge-informativo no selo ativo, obtido {tpl_badge_classes}")
    bad_tpl_hero = [c for c in tpl_hero_classes if COLOR_UTILITY.match(c) or re.match(r"^bg-gradient-to-", c)]
    bad_tpl_badge = [c for c in tpl_badge_classes if COLOR_UTILITY.match(c)]
    if bad_tpl_hero:
        offenders.append(f"template-noticia.html cabeçalho com utilitários: {bad_tpl_hero}")
    if bad_tpl_badge:
        offenders.append(f"template-noticia.html selo com utilitários: {bad_tpl_badge}")

    assert checked > 330, checked
    assert not offenders, "\n".join(offenders[:20])


def test_central_palette_keeps_the_text_readable():
    css = CENTRAL.read_text(encoding="utf-8")
    values = dict(re.findall(r"--(tipo-[a-z-]+):\s*(#[0-9a-fA-F]{6})", css))
    text_dark = values["tipo-texto"]
    text_light = values["tipo-texto-claro"]
    for key in ("tipo-atualizacao", "tipo-atualizacao-forte", "tipo-informativo", "tipo-informativo-forte"):
        assert _ratio(text_dark, values[key]) >= 4.5, f"{key} {values[key]} com texto {text_dark}: {_ratio(text_dark, values[key]):.2f}:1"
    for key in ("tipo-urgente", "tipo-urgente-forte", "tipo-orientacao", "tipo-orientacao-forte"):
        assert _ratio(text_light, values[key]) >= 4.5, f"{key} {values[key]} com texto {text_light}: {_ratio(text_light, values[key]):.2f}:1"


def test_template_documents_the_type_classes():
    html = (ROOT / "noticias" / "template-noticia.html").read_text(encoding="utf-8")
    for name in ("article-hero-atualizacao", "article-badge-atualizacao", "article-hero-informativo", "article-badge-informativo",
                 "article-hero-urgente", "article-badge-urgente", "article-hero-orientacao", "article-badge-orientacao",
                 "news-amber-button", "news-orange-button", "news-urgent-button", "news-orientacao-button"):
        assert name in html, name


def test_unauthorized_color_utility_is_detected_in_memory_copy():
    """Confirma que o detector rejeita classes indevidas (incluindo azul e variantes) em cópias em memória."""
    sample_classes = ["article-hero-informativo", "py-10", "sm:py-12", "md:py-20"]
    assert not [c for c in sample_classes if COLOR_UTILITY.match(c) or re.match(r"^bg-gradient-to-", c)]

    # Classes indevidas (incluindo azul e variantes sky, cyan, indigo, bem como border e gradientes)
    unauthorized = [
        "bg-blue-600", "text-blue-500", "border-blue-400",
        "bg-sky-500", "text-cyan-600", "bg-indigo-700",
        "bg-amber-500", "text-orange-600", "bg-red-600",
        "from-blue-600", "via-sky-400", "to-indigo-800",
        "bg-gradient-to-r",
    ]
    for bad_class in unauthorized:
        mutated = sample_classes + [bad_class]
        detected = [c for c in mutated if COLOR_UTILITY.match(c) or re.match(r"^bg-gradient-to-", c)]
        assert detected == [bad_class], f"Classe indevida {bad_class} deveria ter sido detectada, mas obteve {detected}"

    badge_classes = ["article-badge-informativo", "inline-flex", "items-center", "rounded-full", "px-2.5", "py-1", "whitespace-nowrap"]
    assert not [c for c in badge_classes if COLOR_UTILITY.match(c)]
    for bad_class in ("bg-blue-600", "text-blue-900", "bg-sky-400", "text-indigo-700", "border-blue-500"):
        detected = [c for c in (badge_classes + [bad_class]) if COLOR_UTILITY.match(c)]
        assert detected == [bad_class], f"Selo com {bad_class} deveria ter sido detectado"

    # Injeção em cópia em memória do HTML do cabeçalho
    dirty_html = '<header class="article-hero-informativo bg-blue-600 py-10"><span class="article-badge-informativo text-sky-500">Informativo</span></header>'
    match = re.search(r'<header\s+class="([^"]*)"(?:.*?)<span class="([^"]*)">\s*Informativo\s*</span>', dirty_html, re.S)
    assert match
    bad_hero = [c for c in match.group(1).split() if COLOR_UTILITY.match(c)]
    bad_badge = [c for c in match.group(2).split() if COLOR_UTILITY.match(c)]
    assert bad_hero == ["bg-blue-600"]
    assert bad_badge == ["text-sky-500"]
