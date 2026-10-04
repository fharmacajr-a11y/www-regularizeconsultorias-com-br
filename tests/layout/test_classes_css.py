"""Classes do HTML e do JavaScript sem regra de CSS.

O tailwind.min.css é gerado a partir do HTML e do JavaScript (tailwind.config.js);
uma classe nova sem regenerar o arquivo não tem efeito na página. O teste lê os
seletores de todos os CSS do site e dos <style> de cada página, desfaz os escapes
(\\2c , \\:, \\/ ...) e confere que toda classe usada tem regra. As exceções são
ganchos sem estilo próprio, usados por JavaScript, testes ou CSS de página.
"""
import re

from support import ROOT, public_html_paths


CSS_FILES = (
    [ROOT / "assets/css/tailwind.min.css", ROOT / "assets/css/base.css",
     ROOT / "assets/css/components.css", ROOT / "assets/css/custom.min.css"]
    + sorted((ROOT / "assets/css/pages").glob("*.css"))
)
HOOKS = {
    "aviso-badge",
    "aviso-tipo",
    "comunicado-historico__body",
    "comunicado-historico__icon",
    "contact-hero-content",
    "contact-hero-section",
    "manuals-catalog-button-label",
    "manuals-hero-content",
    "manuals-hero-section",
}
HOOK_PREFIXES = ("manuals-page-",)
SELECTOR_CLASS = re.compile(r"\.((?:\\[0-9a-fA-F]{1,6}[ \t]?|\\[^0-9a-fA-F\n]|[\w-])+)")
JS_CLASSES = re.compile(
    r"(?:className\s*=|classList\.(?:add|remove|toggle|contains)\(|setAttribute\('class',)\s*'([^']+)'"
)


def _unescape(name):
    name = re.sub(r"\\([0-9a-fA-F]{1,6})[ \t]?", lambda match: chr(int(match.group(1), 16)), name)
    return re.sub(r"\\(.)", r"\1", name)


def _defined_classes(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    names = set()
    for selectors in re.findall(r"([^{}]+)\{", css):
        if not selectors.strip().startswith("@"):
            names.update(_unescape(match) for match in SELECTOR_CLASS.findall(selectors))
    return names


SITE_CLASSES = set().union(*(_defined_classes(path.read_text(encoding="utf-8")) for path in CSS_FILES))


def _is_hook(name):
    return name in HOOKS or name.startswith(HOOK_PREFIXES)


def test_every_class_in_the_html_has_a_css_rule():
    missing = {}
    for path in public_html_paths():
        html = path.read_text(encoding="utf-8")
        page_classes = set().union(set(), *(
            _defined_classes(style) for style in re.findall(r"<style[^>]*>(.*?)</style>", html, re.DOTALL)
        ))
        for attribute in re.findall(r'class="([^"]*)"', html):
            for name in attribute.split():
                if name not in SITE_CLASSES and name not in page_classes and not _is_hook(name):
                    missing.setdefault(name, []).append(path.relative_to(ROOT).as_posix())
    assert not missing, "\n".join(
        f"{name}: {len(paths)} página(s), ex. {paths[0]} — regenere o tailwind.min.css (tests/README.md)"
        for name, paths in sorted(missing.items())
    )


def test_every_class_toggled_by_javascript_has_a_css_rule():
    toggled = set()
    for path in sorted((ROOT / "assets/js").rglob("*.js")):
        for value in JS_CLASSES.findall(path.read_text(encoding="utf-8")):
            toggled.update(value.split())
    assert toggled, "nenhuma classe encontrada no JavaScript; o teste perdeu o alvo"
    missing = sorted(name for name in toggled if name not in SITE_CLASSES and not _is_hook(name))
    assert not missing, f"classes do JavaScript sem regra: {missing}"


def test_hooks_really_have_no_rule_of_their_own():
    styled = sorted(name for name in HOOKS if name in SITE_CLASSES)
    assert not styled, f"saíram da lista de ganchos por já terem regra: {styled}"
