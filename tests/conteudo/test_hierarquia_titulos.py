"""Estrutura de títulos de todas as páginas públicas.

Cada página tem um único h1, nenhum título fica vazio e, ao descer de nível, não
se pula nenhum (h1 → h3, h2 → h4). Títulos só para leitores de tela (sr-only)
contam: eles existem para fechar essa estrutura sem mudar a aparência.
"""
from support import ROOT, parse_html, public_html_paths


LEVELS = {f"h{level}": level for level in range(1, 7)}


def _headings(path):
    return [
        (LEVELS[node.tag], " ".join(node.text_content().split()))
        for node in parse_html(path).descendants()
        if node.tag in LEVELS
    ]


def test_every_page_has_one_h1_and_no_empty_heading():
    for path in public_html_paths():
        headings = _headings(path)
        relative = path.relative_to(ROOT).as_posix()
        assert [level for level, _ in headings].count(1) == 1, relative
        assert all(text for _, text in headings), f"{relative}: título vazio"


def test_heading_levels_do_not_skip_when_going_deeper():
    failures = []
    for path in public_html_paths():
        previous = 0
        for level, text in _headings(path):
            if previous and level > previous + 1:
                failures.append(f"{path.relative_to(ROOT).as_posix()}: h{previous} → h{level} em '{text[:60]}'")
            previous = level
    assert not failures, "\n".join(failures)
