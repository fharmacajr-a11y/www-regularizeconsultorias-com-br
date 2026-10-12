"""Selos do herói das matérias dentro da largura útil, sem rolagem horizontal, a 320 px.

O herói de cada matéria tem uma linha de selos (tipo da matéria e categoria) logo acima do H1. Na
2ª entrega, a varredura com a barra de rolagem clássica achou duas matérias em que os dois selos,
numa linha flex-nowrap, passavam da largura útil a 320x568 (305 px úteis) e faziam a página rolar
na horizontal: "ATUALIZAÇÃO" + "MINISTÉRIO DA SAÚDE" (procedimentos hemoterápicos, 3 px) e
"INFORMATIVO" + "VIGILÂNCIA SANITÁRIA" (boletim do SNVS, 6 px). Nas duas, a linha passou a
quebrar (flex-wrap) quando os selos não cabem lado a lado; nenhum selo foi encurtado nem teve a
fonte reduzida. O modelo de notícia recebeu a mesma classe.

O teste abre as 83 matérias a 320x568 sem e com a barra clássica (sem --hide-scrollbars) e exige,
em cada uma, que a página não role na horizontal e que cada selo termine dentro da largura útil,
com 0,5 px de tolerância para o arredondamento subpixel.

Fora do critério (registrado no relatório da 3ª entrega, sem alteração): a 320 px, em outras
matérias, o segundo selo entra no padding direito da linha, que é a reserva da coluna de voltar ao
topo e WhatsApp, sem rolagem horizontal. A coluna fica fixa no pé da janela e a linha de selos, no
topo do herói, então eles não se encontram; os testes de faixa dos controles cobrem o herói em
telas baixas.
"""
import json
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from support import ROOT, SITE_DIR, subprocess_env


TOL = 0.5
PORTAS_RECUSADAS = {5060, 5061, 6000, 6566, 6665, 6666, 6667, 6668, 6669, 6697, 10080}
MATERIAS = sorted(
    "/" + p.parent.relative_to(ROOT).as_posix() + "/"
    for p in (ROOT / "noticias").glob("*/index.html")
    if "a-publicar" not in p.parts
)

PROBE = r"""
import json
import sys
from playwright.sync_api import sync_playwright
import support

base, paginas, barra = sys.argv[1], json.loads(sys.argv[2]), sys.argv[3] == "1"
MEDIR = r'''
() => {
  const linha = document.querySelector('main > article > header .max-w-4xl > div.mb-4');
  if (!linha) return null;
  const q = linha.getBoundingClientRect(), cs = getComputedStyle(linha);
  const direita = q.right - parseFloat(cs.paddingRight);
  const selos = [...linha.children].map(c => { const r = c.getBoundingClientRect();
    return {texto: c.textContent.trim(), r: r.right, t: r.top, fs: getComputedStyle(c).fontSize}; });
  return {util: document.documentElement.clientWidth, rolagemX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    direitaConteudo: direita, selos, linhas: new Set(selos.map(s => Math.round(s.t))).size};
}
'''
saida = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, ignore_default_args=["--hide-scrollbars"] if barra else None)
    context = support.new_context(browser, viewport={"width": 320, "height": 568}, device_scale_factor=1)
    page = context.new_page()
    for pagina in paginas:
        page.goto(base + pagina, wait_until="load")
        page.evaluate("async () => { await document.fonts.ready; }")
        saida.append({"pagina": pagina, "barra": barra, "medida": page.evaluate(MEDIR)})
    context.close()
    browser.close()
print(json.dumps(saida))
"""


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass


def _servidor():
    while True:
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_Quiet, directory=str(SITE_DIR)))
        if server.server_port not in PORTAS_RECUSADAS:
            return server
        server.server_close()


@pytest.fixture(scope="module")
def selos():
    server = _servidor()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    metade = len(MATERIAS) // 2
    grupos = [(MATERIAS[:metade], False), (MATERIAS[metade:], False), (MATERIAS[:metade], True), (MATERIAS[metade:], True)]
    try:
        processos = [
            subprocess.Popen([sys.executable, "-c", PROBE, base, json.dumps(paginas), "1" if barra else "0"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                             env=subprocess_env())
            for paginas, barra in grupos
        ]
        saidas = [processo.communicate(timeout=900) for processo in processos]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    resultado = []
    for processo, (stdout, stderr) in zip(processos, saidas):
        assert processo.returncode == 0, stderr[-4000:]
        resultado.extend(json.loads(stdout))
    return resultado


def test_todas_as_materias_medidas_com_e_sem_barra(selos):
    assert len(MATERIAS) == 83
    assert len(selos) == 2 * len(MATERIAS)
    for r in selos:
        assert r["medida"] and len(r["medida"]["selos"]) >= 2, r["pagina"]
        if r["barra"]:
            assert r["medida"]["util"] == 305, (r["pagina"], "a barra clássica não apareceu")


def test_selos_dentro_da_largura_util_sem_rolagem_horizontal(selos):
    falhas = []
    for r in selos:
        m = r["medida"]
        fora = [(s["texto"], round(s["r"] - m["util"], 2)) for s in m["selos"] if s["r"] > m["util"] + TOL]
        if m["rolagemX"] > 0 or fora:
            falhas.append((r["pagina"], "barra" if r["barra"] else "sem barra", m["rolagemX"], fora))
    assert falhas == [], "\n".join(map(str, falhas))
