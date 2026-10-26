"""Faixa regulatória, cabeçalho e rodapé iguais aos da home em todas as páginas publicadas (desde 23/10/2026).

Até 23/10/2026 havia 18 variantes de cabeçalho e 21 de rodapé. A maioria era só de marcação (atributos em outra
ordem, entidades, espaços), mas 22 páginas publicadas, entre elas a /politica-de-privacidade/ e a
/farmacia-popular/, tinham a coluna "Contato" do rodapé sem os ícones de telefone, e-mail e Instagram; 20 tinham os
links do rodapé sem a transição de cor e 15 o AVISOS ou o botão do menu sem o efeito ao passar o mouse; 5 tinham
texto diferente no rodapé; 6, outro desenho do ícone do Instagram; e 5, a seta da faixa regulatória sem a classe.

O teste lê os três blocos da home (index.html), aplica o item ativo de cada página e compara com o da página, com
os espaços normalizados. O item ativo usa as classes que as páginas já usavam:
- /sobre/ e /equipe/: Sobre; /servicos/: Serviços; /manuais-e-pops/ e as páginas de manual: Manuais e POPs;
  /farmacia-popular/: Farmácia Popular; /noticias/ e as notícias: Notícias; /contato/: Contato;
- home, /comunicado/ e /politica-de-privacidade/: nenhum.
Na /comunicado/ o AVISOS do menu do celular fica logo depois do <nav>, fora dele: o main.js marca com .active o link
da página atual dentro de #navbar nav, e #navbar nav a.active (components.css e custom.min.css) pintaria de azul o
texto do botão vermelho. É o item ativo dessa página. O modelo de notícia (noticias/template-noticia.html) fica de
fora, como em tests/conteudo/test_privacidade.py: é página técnica, com noindex e sem o link da Política de
Privacidade no rodapé.
"""
import re

import pytest

from support import ROOT, public_html_paths


NAV_D = 'class="text-sm font-medium text-slate-700 hover:text-brand transition-colors duration-200"'
NAV_D_ATIVO = 'class="text-sm font-medium text-brand transition-colors duration-200"'
NAV_M = 'class="block px-3 py-2.5 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-100 transition-colors"'
NAV_M_ATIVO = 'class="block px-3 py-2.5 rounded-lg text-sm font-medium text-brand bg-slate-50 transition-colors"'
BLOCOS = {
    "faixa": re.compile(r'<aside class="site-regulatory-banner"[^>]*>.*?</aside>', re.S),
    "cabeçalho": re.compile(r'<header\b[^>]*\bid="navbar"[^>]*>.*?</header>', re.S),
    "rodapé": re.compile(r"<footer\b[^>]*>.*?</footer>", re.S),
}
PAGINAS = public_html_paths()


def _ativo(rel):
    if rel in ("sobre/index.html", "equipe/index.html"):
        return "/sobre/"
    if rel == "servicos/index.html":
        return "/servicos/"
    if rel.startswith("manuais-e-pops/"):
        return "/manuais-e-pops/"
    if rel == "farmacia-popular/index.html":
        return "/farmacia-popular/"
    if rel.startswith("noticias/"):
        return "/noticias/"
    if rel == "contato/index.html":
        return "/contato/"
    return None


def _normaliza(html):
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    html = re.sub(r"\s+", " ", html)
    return re.sub(r">\s+<", "><", html).strip()


def _blocos(path):
    source = path.read_text(encoding="utf-8")
    achados = {nome: padrao.findall(source) for nome, padrao in BLOCOS.items()}
    for nome, lista in achados.items():
        assert len(lista) == 1, f"{path.relative_to(ROOT)}: {len(lista)} blocos de {nome}"
    return {nome: _normaliza(lista[0]) for nome, lista in achados.items()}


HOME = _blocos(ROOT / "index.html")


def _cabecalho_esperado(rel):
    cabecalho = HOME["cabeçalho"]
    alvo = _ativo(rel)
    if alvo:
        for padrao, ativo in ((NAV_D, NAV_D_ATIVO), (NAV_M, NAV_M_ATIVO)):
            link = f'<a href="{alvo}" {padrao}>'
            assert cabecalho.count(link) == 1, (rel, link)
            cabecalho = cabecalho.replace(link, f'<a href="{alvo}" {ativo}>')
    if rel == "comunicado/index.html":
        avisos = re.search(r'<a href="/comunicado/" class="mt-2 [^"]*">.*?</a>(?=</nav>)', cabecalho).group(0)
        cabecalho = cabecalho.replace(avisos + "</nav>", "</nav>" + avisos)
    return cabecalho


def test_home_tem_os_seis_itens_do_menu_sem_item_ativo():
    assert HOME["cabeçalho"].count(NAV_D) == 6
    assert HOME["cabeçalho"].count(NAV_M) == 6
    assert NAV_D_ATIVO not in HOME["cabeçalho"] and NAV_M_ATIVO not in HOME["cabeçalho"]


@pytest.mark.parametrize("path", PAGINAS, ids=[p.relative_to(ROOT).as_posix() for p in PAGINAS])
def test_faixa_cabecalho_e_rodape_iguais_aos_da_home(path):
    rel = path.relative_to(ROOT).as_posix()
    blocos = _blocos(path)
    assert blocos["faixa"] == HOME["faixa"], f"{rel}: faixa regulatória diferente da home"
    assert blocos["rodapé"] == HOME["rodapé"], f"{rel}: rodapé diferente do da home"
    esperado = _cabecalho_esperado(rel)
    assert blocos["cabeçalho"] == esperado, f"{rel}: cabeçalho diferente do da home (item ativo {_ativo(rel)})"
    # Um item ativo só, no menu do computador e no do celular, e só nas páginas de seção.
    ativos = blocos["cabeçalho"].count(NAV_D_ATIVO) + blocos["cabeçalho"].count(NAV_M_ATIVO)
    assert ativos == (2 if _ativo(rel) else 0), rel


def test_rodape_da_politica_de_privacidade_tem_os_icones_do_contato():
    rodape = _blocos(ROOT / "politica-de-privacidade" / "index.html")["rodapé"]
    contato = rodape[rodape.index(">Contato</h2>"):]
    itens = re.findall(r'<li class="flex items-center gap-3">(.*?)</li>', contato)
    hrefs = ("/whatsapp/", "mailto:fharmaca2013@hotmail.com", "https://www.instagram.com/regularizeconsultoriarc/")
    assert len(itens) == len(hrefs)
    for item, href in zip(itens, hrefs):
        assert item.startswith('<svg class="w-4 h-4 text-brand-light flex-shrink-0"'), href
        assert f'href="{href}"' in item, href
