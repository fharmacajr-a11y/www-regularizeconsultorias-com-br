"""POP SNCR: a página de produto não afirma o que o material vendido não traz.

A Matriz 08, revisão de 13/10/2026, prevê o registro da utilização pelo colaborador autorizado,
sob supervisão farmacêutica. A frase da P49/P50, que dizia que o registro é exclusivamente do
farmacêutico, saiu dos temas. O item novo descreve a transição das RCE e RET eletrônicas sem
numeração, sem link externo e sem os itens deixados para outra atualização.
"""
import re
from pathlib import Path


ROOT = Path(__file__).parents[2]
POP_PATH = ROOT / "manuais-e-pops" / "pop-sncr" / "index.html"
SITEMAP_PATH = ROOT / "sitemap.xml"
URL = "https://www.regularizeconsultorias.com.br/manuais-e-pops/pop-sncr/"
P49_P50_SENTENCE = (
    "Nas Perguntas e Respostas sobre a integração dos sistemas de prescrição eletrônica ao SNCR, publicadas pela "
    "Anvisa em 16/10/2026, o registro de utilização da receita eletrônica é feito exclusivamente pelo farmacêutico, "
    "no portal web do SNCR, e a pergunta 50 informa que, no conjunto de funcionalidades previstas até 30/09/2026, não "
    "há previsão de endpoint para integração com sistemas de ponto de venda (PDV) ou ERPs de farmácias."
)
CONSULTA = "Consulta no SNCR e registro de utilização."
TRANSICAO = (
    "Transição das RCE e RET eletrônicas sem numeração e registro das datas indicadas pelas fontes oficiais."
)


def _plain(fragment):
    return " ".join(re.sub(r"<[^>]+>", " ", fragment).split())


def _main(html):
    return re.search(r"<main>(.*?)</main>", html, re.DOTALL).group(1)


def _themes(main):
    start = main.index("Temas abordados no procedimento")
    return main[start:main.index("</section>", start)]


def test_pop_sncr_themes_follow_the_sold_material_and_omit_the_p49_claim():
    html = POP_PATH.read_text(encoding="utf-8")
    main = _main(html)
    themes = _themes(main)
    items = [_plain(item) for item in re.findall(r"<div>(.*?)</div>", themes, re.DOTALL)]

    assert P49_P50_SENTENCE not in html
    assert "exclusivamente pelo farmacêutico" not in html
    assert "pergunta 50" not in _plain(main)
    assert TRANSICAO in items
    assert items.index(TRANSICAO) == items.index(CONSULTA) + 1
    assert re.findall(r'href="(https?://[^"]+)"', main) == []


def test_pop_sncr_leaves_out_held_items_and_updates_the_sitemap():
    html = POP_PATH.read_text(encoding="utf-8")
    visible = _plain(html)
    for term in ("16 dígitos", "16 digitos", "14 para 16", "mais de um medicamento", "P47", "pergunta 47"):
        assert term not in html and term not in visible, term
    for claim in ("sem API PDV/ERP até", "até 30/09/2026, não haverá", "não haverá API"):
        assert claim not in visible, claim
    sitemap = SITEMAP_PATH.read_text(encoding="utf-8")
    assert sitemap.count(f"<loc>{URL}</loc>") == 1
    assert f"<loc>{URL}</loc>\n    <lastmod>2026-10-21</lastmod>" in sitemap
