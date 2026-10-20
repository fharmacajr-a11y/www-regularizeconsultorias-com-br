"""POP SNCR: frase sobre as Perguntas e Respostas da integração ao SNCR (lote 2 do SNCR, 20/10/2026).

Mudança mínima na página pública do POP: uma frase com a data das Perguntas e Respostas (16/10/2026), o registro de
utilização pelo farmacêutico no portal web do SNCR (pergunta 49) e o que a pergunta 50 diz sobre PDV e ERP, sem
link externo e sem os itens deixados para outra atualização.
"""
import re
from pathlib import Path


ROOT = Path(__file__).parents[2]
POP_PATH = ROOT / "manuais-e-pops" / "pop-sncr" / "index.html"
SITEMAP_PATH = ROOT / "sitemap.xml"
URL = "https://www.regularizeconsultorias.com.br/manuais-e-pops/pop-sncr/"
SENTENCE = (
    "Nas Perguntas e Respostas sobre a integração dos sistemas de prescrição eletrônica ao SNCR, publicadas pela "
    "Anvisa em 16/10/2026, o registro de utilização da receita eletrônica é feito exclusivamente pelo farmacêutico, "
    "no portal web do SNCR, e a pergunta 50 informa que, no conjunto de funcionalidades previstas até 30/09/2026, não "
    "há previsão de endpoint para integração com sistemas de ponto de venda (PDV) ou ERPs de farmácias."
)


def _plain(fragment):
    return " ".join(re.sub(r"<[^>]+>", " ", fragment).split())


def _main(html):
    return re.search(r"<main>(.*?)</main>", html, re.DOTALL).group(1)


def test_pop_sncr_cites_the_integration_qa_in_one_sentence():
    html = POP_PATH.read_text(encoding="utf-8")
    main = _main(html)
    paragraphs = [_plain(item) for item in re.findall(r"<p\b[^>]*>.*?</p>", main, re.DOTALL)]

    assert [item for item in paragraphs if "Perguntas e Respostas" in item] == [SENTENCE]
    assert _plain(main).count("Perguntas e Respostas") == 1
    # Fica na seção dos temas, logo antes do parágrafo dos POPs para Drogarias.
    themes = main[main.index("Temas abordados no procedimento"):main.index("</section>", main.index("Temas abordados no procedimento"))]
    assert SENTENCE in _plain(themes)
    assert _plain(themes).index(SENTENCE) < _plain(themes).index("Para organizar outros procedimentos da unidade")
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
    assert f"<loc>{URL}</loc>\n    <lastmod>2026-10-20</lastmod>" in sitemap
