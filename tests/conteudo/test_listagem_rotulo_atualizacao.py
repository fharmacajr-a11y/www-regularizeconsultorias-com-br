"""Listagem de notícias: a data mostrada no card é a mesma que ordena a lista.

A listagem ordena os cards pela data de ordenação de cada um: data-updated, ou o <time datetime> do card quando não há
data-updated (assets/js/main.js, getCardTimestamp; test_ordenacao_noticias.py). Quando essa data é uma atualização
(dia posterior ao datePublished da matéria; no mesmo dia, só se a publicação tiver hora e a atualização for posterior),
o card mostra "Atualizado em" e a data de ordenação, no texto e no atributo datetime do <time>. Assim uma matéria antiga
atualizada não aparece no topo com a data de publicação, como acontecia com as sete atualizadas no lote de conteúdo de
09/10/2026. Não há exceção: em todo card de atualização, texto, datetime e data de ordenação coincidem (o datetime do
card de "Alteração cadastral" passou da publicação para a atualização na revisão v2 do layout comum, 10/10/2026). A data
de publicação original fica na página da matéria (datePublished e "Publicado em"); a desse card é protegida em
test_ordenacao_noticias.py.
"""
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
NEWS_INDEX_PATH = ROOT / "noticias" / "index.html"
SP = timezone(timedelta(hours=-3))
ROTULO = '<span class="leading-snug text-center sm:text-left">Atualizado em <span class="whitespace-nowrap"><time '
LOTE_09_10 = {
    "policia-federal-classificacao-produtos-simples-compostos-siproquim": "09/10/2026 • 20h40",
    "sngpc-boas-praticas-evitar-pendencias": "09/10/2026 • 20h39",
    "o-que-e-afe-e-por-que-e-importante": "09/10/2026 • 20h38",
    "crf-responsavel-tecnico-farmacias-drogarias": "09/10/2026 • 20h36",
    "produtos-veterinarios-controle-especial-mapa-portaria-837": "09/10/2026 • 20h36",
    "farmacia-popular-adequacao-materiais-periodo-eleitoral": "09/10/2026 • 20h35",
    "farmacia-popular-inconsistencias-prescricoes-monitoramento": "09/10/2026 • 20h33",
}


def _dt(s):
    d = datetime.fromisoformat(s)
    return (d if d.tzinfo else d.replace(tzinfo=SP)).astimezone(SP)


def _eh_atualizacao(s, p):
    ds, dp = _dt(s), _dt(p)
    if ds.date() != dp.date():
        return ds.date() > dp.date()
    return "T" in p and ds > dp


def _cards():
    html = NEWS_INDEX_PATH.read_text(encoding="utf-8")
    cards = re.findall(r'(<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>)', html, re.DOTALL)
    assert len(cards) == 83
    for card in cards:
        slug = re.search(r'href="/noticias/([^"/]+)/"', card).group(1)
        tm = re.search(r'<time datetime="([^"]+)"[^>]*>([^<]*)</time>', card)
        up = re.search(r'\bdata-updated="([^"]+)"', card)
        pagina = (ROOT / "noticias" / slug / "index.html").read_text(encoding="utf-8")
        pub = re.search(r'"datePublished"\s*:\s*"([^"]+)"', pagina).group(1)
        yield slug, card, tm, (up.group(1) if up else tm.group(1)), pub


def test_card_mostra_a_data_que_ordena_e_rotula_atualizacao():
    falhas = []
    rotulados = 0
    for slug, card, tm, ordem, pub in _cards():
        d = _dt(ordem)
        esperado = f"{d:%d%m%Y}{d:%H%M}"
        if _eh_atualizacao(ordem, pub):
            rotulados += 1
            if ROTULO not in card:
                falhas.append((slug, "sem rótulo"))
            if re.sub(r"\D", "", tm.group(2)) != esperado:
                falhas.append((slug, "texto", tm.group(2), ordem))
            if tm.group(1) != ordem:
                falhas.append((slug, "datetime", tm.group(1), ordem))
        elif "Atualizado em" in card:
            falhas.append((slug, "rótulo numa publicação"))
    assert not falhas, falhas
    assert rotulados == 44


def test_materias_do_lote_de_09_10_mostram_a_atualizacao():
    vistos = {}
    for slug, card, tm, ordem, pub in _cards():
        if slug in LOTE_09_10:
            vistos[slug] = tm.group(2)
            assert ROTULO in card
            assert tm.group(1) == ordem
    assert vistos == LOTE_09_10
