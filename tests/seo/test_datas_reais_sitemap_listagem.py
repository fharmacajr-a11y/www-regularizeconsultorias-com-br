"""Datas reais e coerentes entre página, listagem e sitemap (conferência final dos 126, bloco C, 11/10/2026).

O lastmod do sitemap e o dateModified das páginas acompanham mudanças reais de conteúdo, não manutenção de layout,
troca de componente global (selos de avisos, versão de script) nem título de uma matéria relacionada citada no bloco de
notícias relacionadas. Três frentes, cada uma com a prova no próprio teste:

1. Matérias (83): o lastmod é o dia (America/Sao_Paulo) do dateModified quando a matéria tem atualização (dateModified
   posterior ao datePublished), senão o dia do datePublished. Em 11/10/2026, a única divergência era
   /noticias/farmacia-popular-cuidados-cadastro-documentacao/: lastmod 2026-10-07, vindo de 9287979, que só trocou o
   título de um card de notícias relacionadas; a matéria não tem atualização desde a publicação (28/04/2026) e o lastmod
   voltou a 2026-04-28, o valor anterior a 9287979.
2. Card da Now Foods: a matéria foi revista em 01/06/2026 15h55 (82eb097, quadro "Atualização: novos alertas sobre
   suplementos irregulares"), data exibida na página e no lastmod desde o lote de conteúdo de 09/10/2026; o card da
   listagem passou a mostrar essa atualização (data-updated; desde 12/10/2026 sem o prefixo "Atualizado em", só a
   data e a hora, parecer de 11/10/2026, R1). A posição não muda: pela data da atualização ele continua entre os
   cards de 02/06/2026 e de 28/04/2026.
3. Páginas institucionais (pendência D1): o lastmod é o dia da última mudança real do texto do <main>
   (scripts da conferência: datas_conteudo_principal.py), com o trecho que a comprova:
   / 2026-10-08 (f47fc13: descrição de PF/CRC e CLF); /equipe/ 2026-10-08 (f47fc13: "Ministério da Agricultura e
   Pecuária" no lugar de "Agricultura, Pecuária e Abastecimento");    /contato/ 2026-10-12 (retirada do item "Tempo de resposta — Até 30 minutos"; a lista de
   órgãos com SNGPC, de ddd55d1, permanece); /sobre/ 2026-06-06 (bb2f618: o primeiro card de princípios passou de "Missão" a "Visão"; a mudança de
   03/10, 6f926d6, foi só um título sr-only de acessibilidade). /servicos/, a quinta página da pendência D1 (decisão D1
   da Fase 1O v2), já está em 2026-10-09 desde o lote de conteúdo (bef7417: termos do bloco Farmácia Popular e item do
   bloco CNES, frente G07).
"""
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parents[2]
SITEMAP = ROOT / "sitemap.xml"
NEWS_INDEX = ROOT / "noticias" / "index.html"
BASE = "https://www.regularizeconsultorias.com.br"
SP = timezone(timedelta(hours=-3))
NOW_FOODS = "anvisa-apreende-medicamentos-irregulares-now-foods"
NOW_FOODS_UPDATED = "2026-06-01T15:55:00-03:00"
CADASTRO = "farmacia-popular-cuidados-cadastro-documentacao"


def _lastmods():
    return dict(re.findall(r"<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>", SITEMAP.read_text(encoding="utf-8")))


def _dt(value):
    moment = datetime.fromisoformat(value)
    return (moment if moment.tzinfo else moment.replace(tzinfo=SP)).astimezone(SP)


def _is_update(modified, published):
    m, p = _dt(modified), _dt(published)
    if m.date() != p.date():
        return m.date() > p.date()
    return "T" in published and m > p


def _cards():
    html = NEWS_INDEX.read_text(encoding="utf-8")
    return re.findall(r"(<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>)", html, re.DOTALL)


def test_lastmod_de_cada_materia_e_o_dia_da_ultima_atualizacao_declarada():
    lastmods = _lastmods()
    paginas = sorted(p for p in (ROOT / "noticias").glob("*/index.html") if "a-publicar" not in p.parts)
    assert len(paginas) == 84
    falhas = []
    for pagina in paginas:
        html = pagina.read_text(encoding="utf-8")
        published = re.search(r'"datePublished"\s*:\s*"([^"]+)"', html).group(1)
        modified = re.search(r'"dateModified"\s*:\s*"([^"]+)"', html)
        modified = modified.group(1) if modified else published
        reference = modified if _is_update(modified, published) else published
        url = f"{BASE}/noticias/{pagina.parent.name}/"
        if lastmods.get(url) != _dt(reference).date().isoformat():
            falhas.append((pagina.parent.name, lastmods.get(url), reference))
    assert falhas == []
    assert lastmods[f"{BASE}/noticias/{CADASTRO}/"] == "2026-04-28"


def test_card_da_now_foods_mostra_a_atualizacao_real_sem_mudar_de_posicao():
    cards = _cards()
    assert len(cards) == 84
    own = [card for card in cards if f'href="/noticias/{NOW_FOODS}/"' in card]
    assert len(own) == 1
    card = own[0]
    opening = card.split(">", 1)[0]
    page = (ROOT / "noticias" / NOW_FOODS / "index.html").read_text(encoding="utf-8")
    assert f'"dateModified": "{NOW_FOODS_UPDATED}"' in page or f'"dateModified":"{NOW_FOODS_UPDATED}"' in page
    assert f'Atualizado em:</span> <time datetime="{NOW_FOODS_UPDATED}">01/06/2026</time> às 15h55' in page
    assert f'data-updated="{NOW_FOODS_UPDATED}"' in opening
    assert f'<time datetime="{NOW_FOODS_UPDATED}" class="leading-none">01/06/2026 • 15h55</time>' in card
    assert "Atualizado em" not in card
    assert "26/05/2026 • 22h00" not in card
    assert f"<loc>{BASE}/noticias/{NOW_FOODS}/</loc>\n    <lastmod>2026-06-01</lastmod>" in SITEMAP.read_text(encoding="utf-8")
    position = cards.index(card)
    before = re.search(r'\bdata-updated="([^"]+)"', cards[position - 1].split(">", 1)[0])
    before = before.group(1) if before else re.search(r'<time datetime="([^"]+)"', cards[position - 1]).group(1)
    after = re.search(r'\bdata-updated="([^"]+)"', cards[position + 1].split(">", 1)[0])
    after = after.group(1) if after else re.search(r'<time datetime="([^"]+)"', cards[position + 1]).group(1)
    assert _dt(before).date().isoformat() == "2026-06-02"
    assert _dt(after).date().isoformat() == "2026-04-28"
    assert position == 80


def test_lastmod_das_paginas_institucionais_segue_a_ultima_mudanca_real_do_texto():
    lastmods = _lastmods()
    esperado = {
        f"{BASE}/": ("2026-10-08", "index.html",
                     "Licenças e regularização (CRC e CLF) para empresas e estabelecimentos que operam com produtos químicos controlados"),
        f"{BASE}/equipe/": ("2026-10-08", "equipe/index.html", "junto ao Ministério da Agricultura e Pecuária"),
        f"{BASE}/contato/": ("2026-10-12", "contato/index.html", "M.A.P.A, SNCR, SNGPC, Polícia Federal"),
        f"{BASE}/servicos/": ("2026-10-09", "servicos/index.html",
                              "Conferência da coerência entre o CNES e outros cadastros do estabelecimento, como Farmácia Popular"),
    }
    for url, (dia, arquivo, trecho) in esperado.items():
        assert lastmods[url] == dia, url
        html = (ROOT / arquivo).read_text(encoding="utf-8")
        main = re.search(r"<main\b[^>]*>(.*)</main>", html, re.S).group(1)
        assert trecho in " ".join(re.sub(r"<[^>]+>", " ", main).split()), (url, trecho)
    contato = (ROOT / "contato" / "index.html").read_text(encoding="utf-8")
    assert "Até 30 minutos" not in contato
    assert "Tempo de resposta" not in contato
    assert lastmods[f"{BASE}/sobre/"] == "2026-06-06"
    sobre = (ROOT / "sobre" / "index.html").read_text(encoding="utf-8")
    titulos = re.findall(r'<h3 class="text-lg font-bold text-slate-900 mb-3 text-center sm:text-left">([^<]+)</h3>', sobre)
    assert titulos == ["Visão", "Missão", "Valores"]
