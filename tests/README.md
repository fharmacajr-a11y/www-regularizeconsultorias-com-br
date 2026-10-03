# Testes do site institucional

Suíte em pytest para o site estático da Regularize Consultoria. Os testes leem o HTML do repositório e, quando precisam de navegador, sobem um servidor local e usam o Playwright com Chromium. Nada aqui envia mensagem de WhatsApp nem publica o site.

A raiz dos testes é a pasta `tests/`. O `pytest.ini` na raiz do repositório coloca essa pasta no `pythonpath`, então os módulos importam `support` direto. `tests/support.py` lê o HTML público e ignora `noticias/template-noticia.html`, `whatsapp/index.html` e qualquer caminho em `noticias/a-publicar/`.

## Grupos

| Pasta | O que verifica |
| --- | --- |
| `layout/` | Geometria do rodapé e da rolagem, controles flutuantes e o contrato visual dos cards de notícias. |
| `navegacao/` | Contrato do rodapé, links internos, recursos locais, âncoras e ids de todas as páginas, a faixa da Portaria 12.091/2026 e os percursos no navegador. |
| `conteudo/` | Textos, datas, avisos, privacidade e as regras editoriais de cada notícia. |
| `seo/` | `sitemap.xml`, JSON-LD público, o registro do `ads.txt`, a versão `?v=` dos CSS/JS versionados e o que o GitHub Pages publica. |
| `funcionalidades/` | Consulta de Farmácia Popular no navegador, integridade das bases e o importador de vagas. |

`layout/test_rodape_espaco.py` mede padding, vão abaixo do último crédito, sobreposição dos botões, rolagem horizontal e o eixo dos blocos centralizados. A comparação vertical usa a mesma página em 1440 px. Não é uma busca de texto no CSS. Todas as páginas públicas também passam pela checagem de rolagem horizontal em 320 e 360 px.

A referência visual é o commit `331a974`, último rodapé aprovado antes do vão do `fd53409`. Nele, os créditos e o fechamento do comunicado ocupam a largura útil toda do container. O teste exige as mesmas bordas e, na home e no comunicado, as mesmas quebras de linha medidas nesse commit em cada largura. Um bloco estreitado falha mesmo quando continua centralizado. No fim da página, nenhum controle pode ficar a menos de 5 px da coluna flutuante, o alcance do anel de foco dela. O modo `historico` abre e fecha pelo teclado o último histórico do comunicado em 320, 360, 390 e 414 px e confere cada quadro pintado: ancorada, a coluna fica 16 px acima de uma das paradas. A tabela `REFERENCE_LINES` não se regenera sozinha. Só mude esses números depois de aprovar visualmente um novo rodapé.

## Dependências

Na raiz do repositório, com o Python que já executa a suíte:

```powershell
python -m pip install pytest playwright pillow openpyxl
python -m playwright install chromium
```

São as bibliotecas que os testes já importam: pytest, Playwright, Pillow e openpyxl. Não há arquivo de requisitos separado.

## Executar

Na raiz do repositório:

```powershell
python -m pytest
```

Um grupo ou um teste:

```powershell
python -m pytest tests/layout
python -m pytest tests/layout/test_rodape_espaco.py --tb=short
```

O pytest descobre os arquivos `test_*.py` dentro das cinco pastas. A saída termina com a contagem de aprovados, falhas e skips. Uma falha mostra o nome do teste. Para repetir só esse caso, use o caminho impresso, por exemplo `tests/layout/test_rodape_espaco.py::test_footer_clearance_matches_the_wide_layout`.

## Testes de navegador

Eles entram no comando principal. Não há relatório HTML.

- `tests/layout/test_rodape_espaco.py` abre as páginas num processo separado, varia a largura e mede o rodapé no fim da rolagem. O processo separado evita o loop do Playwright deixado pela consulta da Farmácia Popular.
- `tests/layout/test_whatsapp_flutuante_global.py` confere posição fixa, tamanho, se o botão não cobre texto e se a coluna continua na janela no fim da página.
- `tests/layout/test_noticias_cards.py` confere a ordenação visual dos cards.
- `tests/conteudo/test_avisos_globais.py` abre o menu e a faixa de avisos.
- `tests/funcionalidades/test_farmacia_popular_consulta.py` filtra a consulta local, sem enviar formulário externo.
- `tests/navegacao/test_percursos_navegador.py` segue Home → Serviços → Contato e Home → manual → orçamento → catálogo → POP SNCR, mede onde as âncoras param sob o cabeçalho fixo, navega a vitrine de Manuais por setas e Tab, usa busca, categorias, ordenação e "Ver mais" das notícias e confere o foco do modal do Comunicado. Os links de WhatsApp abrem a página `/whatsapp/`; o redirecionamento para o wa.me é interceptado e conferido, sem enviar mensagem.

Se o Chromium não estiver instalado, esses testes falham na abertura do navegador. O comando `python -m playwright install chromium` resolve essa dependência.

Os servidores desses testes usam `support.SITE_DIR`: o próprio repositório ou, com `PAGES_SITE_DIR`, a saída do build do GitHub Pages (ver Publicação).

## Publicação

O GitHub Pages publica a branch `main` pelo build do Jekyll, com o workflow `pages-build-deployment` e a action `actions/jekyll-build-pages` (imagem `ghcr.io/actions/jekyll-build-pages:v1.0.13`, github-pages 232, Jekyll 3.10.0). Nenhum arquivo do site tem front matter, então o Jekyll só copia os arquivos. O `_config.yml` desliga o tema padrão (`theme: null`; sem isso o build acrescenta `assets/css/style.css`) e lista o que fica fora do site e continua no repositório: `tests/`, `scripts/`, `pytest.ini`, `tailwind.config.js`, `noticias/template-noticia.html` e `noticias/a-publicar/`. Arquivos e pastas iniciados por `.` ou `_` já ficam fora. Não recrie o `.nojekyll`: ele desliga o Jekyll e volta a publicar essa lista.

`tests/seo/test_publicacao_pages.py` reproduz o filtro e confere que páginas, imagens, dados e PDFs continuam publicados. O último teste do arquivo confere a saída real do build e fica como skipped até ela existir.

### Build local e verificação da saída

O script monta a árvore que seria commitada agora (sem mexer no índice do Git) e roda a mesma imagem do GitHub Pages com Docker. Use uma pasta temporária de caminho curto, fora do repositório. No Windows, com o Docker dentro do WSL:

```powershell
python scripts/gerar_site_pages.py $env:TEMP\rcp --wsl Ubuntu-24.04
$env:PAGES_SITE_DIR = "$env:TEMP\rcp\site"
python -m pytest -rs
Remove-Item Env:PAGES_SITE_DIR
```

No Linux ou no macOS, com Docker local: `python scripts/gerar_site_pages.py /tmp/rcp` e `PAGES_SITE_DIR=/tmp/rcp/site python -m pytest -rs`.

O log do build fica em `rcp/build.log`. Se o `docker pull` falhar (no WSL, o daemon pode não resolver `ghcr.io`), o script baixa a imagem pela API do registro, confere os digests e usa `docker load`. Com `PAGES_SITE_DIR`, os testes de HTML continuam lendo o repositório; todos os testes de navegador servem a saída do build, e o teste do artefato compara cada arquivo publicado com o working tree (ignorando só CRLF/LF).
