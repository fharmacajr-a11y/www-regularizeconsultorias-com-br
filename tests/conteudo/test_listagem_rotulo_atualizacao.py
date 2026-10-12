"""Listagem de notícias: o card mostra a data editorial válida da matéria, sem prefixo.

Pedido do responsável, no parecer de 11/10/2026 (R1): em /noticias/ o card mostra só a data e, quando conhecida, a
hora. O prefixo "Atualizado em" saiu dos 45 cards que o tinham (regra da revisão v2 do layout comum, 10/10/2026, que
este teste protegia até 11/10/2026). A página da matéria continua com "Publicado em" e "Atualizado em".

Regra da data (R2), lida na própria matéria, sem exceção por matéria:
- publicação P e atualização U: o JSON-LD (datePublished, dateModified) e o <time> visível de "Publicado em" e
  "Atualizado em" caem no mesmo dia; vale a forma mais precisa (com hora quando uma das duas tem hora, só o dia
  quando nenhuma tem); com hora nas duas, o mesmo instante; a hora visível "às HHhMM" confere;
- há atualização quando a matéria a declara (dateModified diferente de datePublished e "Atualizado em" visível) e
  ela é posterior a P; a data válida V é U, senão P;
- o card leva V no texto ("DD/MM/AAAA • HHhMM", ou "DD/MM/AAAA" quando V só tem o dia) e no datetime do <time>;
  data-updated = V só quando V é atualização. A ordem da lista segue V (test_ordenacao_noticias.py).

Em 12/10/2026 a regra mudou dois cards: o do CNES 06/2026 (a matéria declara "Atualizado em 18/07/2026", só o dia,
e o card mostrava a publicação, 07/07/2026 09h00) e o do Alivemed (a matéria declara "Atualizado em 09/07/2026 às
18h52" e o card mostrava a publicação das 12h28; a regra anterior olhava a hora do datePublished do JSON-LD, que ali
só tem o dia). Seis cards tinham data-updated igual à publicação, sem atualização declarada na matéria: o atributo
saiu e o <time> continua com a publicação. 47 cards mostram atualização.
"""
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
NEWS_INDEX_PATH = ROOT / "noticias" / "index.html"
SP = timezone(timedelta(hours=-3))
LOTE_09_10 = {
    "policia-federal-classificacao-produtos-simples-compostos-siproquim": "09/10/2026 • 20h40",
    "sngpc-boas-praticas-evitar-pendencias": "09/10/2026 • 20h39",
    "o-que-e-afe-e-por-que-e-importante": "09/10/2026 • 20h38",
    "crf-responsavel-tecnico-farmacias-drogarias": "09/10/2026 • 20h36",
    "produtos-veterinarios-controle-especial-mapa-portaria-837": "09/10/2026 • 20h36",
    "farmacia-popular-inconsistencias-prescricoes-monitoramento": "09/10/2026 • 20h33",
}
CNES_06 = "cnes-prorroga-transmissor-competencia-06-2026"


def _instante(valor):
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", valor):
        return datetime.fromisoformat(valor + "T00:00:00-03:00")
    momento = datetime.fromisoformat(valor)
    return momento if momento.tzinfo else momento.replace(tzinfo=SP)


def _texto(valor):
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", valor):
        return datetime.fromisoformat(valor).strftime("%d/%m/%Y")
    momento = _instante(valor).astimezone(SP)
    return f"{momento:%d/%m/%Y} • {momento:%Hh%M}"


def _mais_precisa(jsonld, visivel, hora):
    candidatos = [x for x in (jsonld, visivel) if x]
    assert candidatos
    assert len({x[:10] for x in candidatos}) == 1, candidatos
    com_hora = [x for x in candidatos if "T" in x]
    if not com_hora:
        assert hora is None, (candidatos, hora)
        return candidatos[0]
    assert len({_instante(x) for x in com_hora}) == 1, com_hora
    if hora:
        assert f"{_instante(com_hora[0]).astimezone(SP):%Hh%M}" == hora, (com_hora, hora)
    return com_hora[0]


def _data_valida(slug):
    html = (ROOT / "noticias" / slug / "index.html").read_text(encoding="utf-8")
    publicado = re.search(r'"datePublished"\s*:\s*"([^"]+)"', html).group(1)
    modificado = re.search(r'"dateModified"\s*:\s*"([^"]+)"', html)
    modificado = modificado.group(1) if modificado else None

    def visivel(rotulo):
        achado = re.search(rotulo + r':</span>\s*<time datetime="([^"]+)">[^<]+</time>(?:\s*às\s*(\d{2}h\d{2}))?', html)
        return (achado.group(1), achado.group(2)) if achado else (None, None)

    p = _mais_precisa(publicado, *visivel("Publicado em"))
    u_visivel, u_hora = visivel("Atualizado em")
    declarada = modificado is not None and modificado != publicado
    assert declarada == (u_visivel is not None), (slug, modificado, publicado, u_visivel)
    if not declarada:
        return p, False
    u = _mais_precisa(modificado, u_visivel, u_hora)
    assert _instante(u) > _instante(p), (slug, u, p)
    return u, True


def _cards():
    html = NEWS_INDEX_PATH.read_text(encoding="utf-8")
    cards = re.findall(r'(<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>)', html, re.DOTALL)
    assert len(cards) == 83
    for card in cards:
        slug = re.search(r'href="/noticias/([^"/]+)/"', card).group(1)
        tempos = re.findall(r'<time datetime="([^"]+)"[^>]*>([^<]*)</time>', card)
        assert len(tempos) == 1, (slug, tempos)
        atualizado = re.search(r'\bdata-updated="([^"]+)"', card.split(">", 1)[0])
        yield slug, card, tempos[0], (atualizado.group(1) if atualizado else None)


def test_card_mostra_a_data_valida_da_materia_sem_prefixo():
    falhas = []
    atualizacoes = 0
    for slug, card, (datetime_card, texto), atualizado in _cards():
        valida, e_atualizacao = _data_valida(slug)
        atualizacoes += e_atualizacao
        if datetime_card != valida:
            falhas.append((slug, "datetime", datetime_card, valida))
        if texto != _texto(valida):
            falhas.append((slug, "texto", texto, _texto(valida)))
        if atualizado != (valida if e_atualizacao else None):
            falhas.append((slug, "data-updated", atualizado, valida if e_atualizacao else None))
        if "Atualizado em" in card or "Publicado em" in card:
            falhas.append((slug, "prefixo no card"))
    assert not falhas, falhas
    assert atualizacoes == 47


def test_materias_do_lote_de_09_10_mostram_a_atualizacao():
    vistos = {}
    for slug, card, (datetime_card, texto), atualizado in _cards():
        if slug in LOTE_09_10:
            vistos[slug] = texto
            assert atualizado == datetime_card
    assert vistos == LOTE_09_10


def test_atualizacao_so_com_o_dia_fica_so_com_o_dia_no_card():
    """CNES 06/2026: o caso do parecer. A regra geral acima decide; aqui fica a prova do resultado."""
    cards = list(_cards())
    posicao, (slug, card, (datetime_card, texto), atualizado) = next(
        (i, item) for i, item in enumerate(cards) if item[0] == CNES_06)
    assert (datetime_card, texto, atualizado) == ("2026-07-18", "18/07/2026", "2026-07-18")
    assert "09h00" not in card and "07/07/2026" not in card
    # Ordem: o dia 18/07/2026 vem depois do card de 24/07/2026 e antes do de 17/07/2026 às 19h00.
    assert cards[posicao - 1][2][0] == "2026-07-24T15:18:00-03:00"
    assert cards[posicao + 1][2][0] == "2026-07-17T19:00:00-03:00"
