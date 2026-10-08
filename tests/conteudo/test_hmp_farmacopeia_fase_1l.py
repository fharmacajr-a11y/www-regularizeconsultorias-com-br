"""Alcance da Fase 1L: migração do HMP e prazos da Farmacopeia.

A mesma função lê a página real e a cópia mutada em memória.
"""
import re

from support import ROOT


HMP = ROOT / "noticias" / "anvisa-hmp-solicita-medicamentos-produtos-biologicos" / "index.html"
FARM = ROOT / "noticias" / "novos-compendios-farmacopeia-brasileira-entram-em-vigor" / "index.html"

OPERATIONAL = (
    "precisa conferir",
    "revisar seus fluxos",
    "revisar responsabilidades",
    "antes de realizar peticionamentos",
    "antes de qualquer envio",
    "mapear os produtos",
    "revisar especificações",
    "registrar as decisões",
    "identificar quais compêndios",
    "deve conferir",
)


def _body(html):
    match = re.search(r'<section class="article-body">(.*?)</section>', html, re.S)
    assert match, "corpo da matéria ausente"
    text = re.sub(r"<[^>]+>", " ", match.group(1))
    return " ".join(text.split())


def _paragraphs(html):
    section = re.search(r'<section class="article-body">(.*?)</section>', html, re.S)
    assert section, "corpo da matéria ausente"
    parts = re.findall(r"<p\b[^>]*>(.*?)</p>", section.group(1), re.S)
    return [" ".join(re.sub(r"<[^>]+>", " ", part).split()) for part in parts]


_CLAUSE = re.compile(r"(?<=[;?!])\s+|(?<=\.)\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕ])")
_UNIVERSAL = re.compile(r"todo o asp|todos os assuntos|todos os processos")
_YEAR = re.compile(r"\bum ano\b")
_YEAR_BROAD = re.compile(r"todos os textos|toda a farmacopeia|todos os compêndios|para todos\b")
_YEAR_BOUND = re.compile(r"não se estende|não vale para todos|não alcança todos|alcance de cada")


def _clauses(paragraph):
    """Divide o parágrafo em orações. Não corta número, 'art.' nem 'nº'."""
    return [part.strip() for part in _CLAUSE.split(paragraph) if part.strip()]


def _universal_limited(clause):
    """A negativa precisa governar a própria afirmação universal."""
    match = _UNIVERSAL.search(clause)
    if not match:
        return True
    before = clause[: match.start()]
    after = clause[match.end() : match.end() + 60]
    if re.search(r"\b(?:não|nem|nenhum)\b", before):
        return True
    return bool(re.search(r"\bnão (?:foi|foram|está|estão|migrou|migraram|abrange|alcança|significa|inclui)\b", after))


def _year_limited(clause):
    """'somente' ou 'desintegração' em outra oração não limita o prazo de um ano."""
    if not _YEAR.search(clause):
        return True
    if _YEAR_BOUND.search(clause):
        return True
    if _YEAR_BROAD.search(clause):
        return False
    return bool(re.search(r"somente|desintegração", clause))


def findings(html):
    """Problemas de alcance no corpo. Conjunto vazio quando o texto permanece delimitado."""
    body = _body(html)
    folded = body.casefold()
    found = set()

    for phrase in OPERATIONAL:
        if phrase in folded:
            found.add("operacional")
    if "mailto:" in folded or re.search(r"https?://", body, re.I):
        found.add("enlace_externo")

    for paragraph in _paragraphs(html):
        for original_clause in _clauses(paragraph):
            clause = original_clause.casefold()
            if _UNIVERSAL.search(clause) and not _universal_limited(clause):
                found.add("migracao_universal")
            if "1.025" in clause and re.search(r"\b180\b", clause) and not re.search(
                r"não traz|não prevê|não reproduz|sem prazo", clause
            ):
                found.add("prazo_1025")
            if _YEAR.search(clause) and not _year_limited(clause):
                found.add("ano_ampliado")

    return found


def _with_sentence(html, sentence):
    return html.replace(
        '<section class="article-body">',
        '<section class="article-body"><p>' + sentence + "</p>",
        1,
    )


def test_paginas_reais_permanecem_delimitadas():
    hmp = HMP.read_text(encoding="utf-8")
    farm = FARM.read_text(encoding="utf-8")
    assert findings(hmp) == set()
    assert findings(farm) == set()
    assert "03/11/2025" in hmp and "28/05/2026" in hmp and "janeiro de 2026" in hmp
    assert "HMP - formato CTD" in hmp
    assert "RDC nº 73/2016" in hmp and "RDC nº 913/2024" in hmp
    assert "vigentes desde julho de 2026" in farm
    assert "entram em vigor" not in re.search(r"<h1\b[^>]*>.*?</h1>", farm, re.S).group(0).casefold()
    assert "MG5.1.4.1-01" in farm
    assert "28/12/2026" not in farm
    assert "datePublished" in farm and '"datePublished": "2026-07-06"' in farm
    assert '"dateModified": "2026-10-07T15:07:04-03:00"' in farm
    assert "A atualização de outubro não reabre a vigência" not in farm
    assert "não marca um novo começo" not in farm
    assert "Precisa avaliar o impacto regulatório?" in farm
    assert '"datePublished": "2026-06-04T22:30:00-03:00"' in hmp
    assert '"dateModified": "2026-10-07T13:29:23-03:00"' in hmp


def test_mutacao_em_memoria_e_rejeitada_pela_mesma_funcao():
    hmp = HMP.read_text(encoding="utf-8")
    farm = FARM.read_text(encoding="utf-8")
    cases = (
        (hmp, "Todo o ASP foi desativado e todos os assuntos migraram.", "migracao_universal"),
        (hmp, "A empresa precisa conferir o histórico antes de realizar peticionamentos.", "operacional"),
        (farm, "A RDC nº 1.025/2026 concede 180 dias para todos os compêndios.", "prazo_1025"),
        (farm, "O prazo de um ano vale para todos os textos da Farmacopeia.", "ano_ampliado"),
        (hmp, "Todo o ASP foi desativado; isso não altera o cadastro da empresa.", "migracao_universal"),
        (farm, "O prazo de um ano vale para todos os textos da Farmacopeia; somente o modo de publicação muda.", "ano_ampliado"),
        (farm, "A consulta fica em https://www.gov.br/anvisa/pt-br/assuntos/farmacopeia/farmacopeia-brasileira.", "enlace_externo"),
        (hmp, "Escreva para o setor em mailto:exemplo@example.com.", "enlace_externo"),
        (hmp, "O cadastro não foi alterado. Todo o ASP foi desativado.", "migracao_universal"),
        (farm, "O prazo de um ano vale para todos os textos da Farmacopeia. Esse aviso não se estende às outras notícias.", "ano_ampliado"),
    )
    for source, sentence, expected in cases:
        found = findings(_with_sentence(source, sentence))
        assert expected in found, (expected, found)
        assert findings(source) == set()
