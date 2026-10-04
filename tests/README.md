# Testes do site institucional

Suíte em pytest para o site estático da Regularize Consultoria. Os testes leem o HTML do repositório e, quando precisam de navegador, sobem um servidor local e usam o Playwright com Chromium. Nada aqui envia mensagem de WhatsApp nem publica o site.

A raiz dos testes é a pasta `tests/`. O `pytest.ini` na raiz do repositório coloca essa pasta no `pythonpath`, então os módulos importam `support` direto. `tests/support.py` lê o HTML público e ignora `noticias/template-noticia.html`, `whatsapp/index.html` e qualquer caminho em `noticias/a-publicar/`.

## Grupos

| Pasta | O que verifica |
| --- | --- |
| `layout/` | Geometria do rodapé e da rolagem, controles flutuantes, o contrato visual dos cards de notícias, as bordas da coluna lateral das Notícias e os botões flutuantes sobre ela, contraste do texto renderizado e classes sem regra de CSS. |
| `navegacao/` | Contrato do rodapé, links internos, recursos locais, âncoras e ids de todas as páginas, a faixa da Portaria 12.091/2026 e os percursos no navegador. |
| `conteudo/` | Textos, datas, avisos, privacidade, hierarquia de títulos e as regras editoriais de cada notícia. |
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
- `tests/layout/test_noticias_alinhamento.py` mede as bordas dos quatro blocos da coluna lateral das Notícias de 320 a 1920 px, incluindo 639/640, 767/768 e 1023/1024. Empilhados (até 1023 px), eles têm de terminar nas mesmas bordas de "Orientação técnica", dos cards de notícia e de "Sobre o conteúdo"; a partir de 1024 px, a lateral fica na borda esquerda de "Sobre o conteúdo" e a lista na direita. Com cada botão flutuante na altura de cada controle da coluna, o centro do controle continua livre.
- `tests/layout/test_noticias_flutuantes.py` confere que os botões flutuantes (voltar ao topo e WhatsApp) não escondem nada da coluna lateral das Notícias. Empilhada, ela passa sob a coluna fixa, e o `assets/js/pages/noticias.js` marca essa coluna com `inert` enquanto as duas se cruzam (com 1rem de folga); o `pages/noticias.css` recolhe os botões. Em 13 janelas (celular, 639/640, 767/768, meia tela de 940 e 960, 1023/1024 e desktop), o teste reproduz o caso de 960 px com a contagem "54" de ANVISA na altura do WhatsApp, rola com a roda em passos de 40 px para baixo e para cima, percorre a coluna por Tab e Shift+Tab, aplica filtros pelo mouse e pelo teclado e faz uma busca. Também salta de uma vez do fim da página, com a coluna fixa ancorada acima dos créditos pelo `main.js`, até as categorias, e das categorias até o fim; a medida vem logo depois do salto, e o teste confere que houve um único evento de rolagem, para nenhuma rolagem extra esconder um defeito. Por fim, redimensiona a janela para 1440 px e de volta com a coluna sob os botões. Em cada parada, nenhum botão visível pode cobrir nomes e contagens das categorias, campos, textos dos controles ou o anel de foco do controle focado. Também confere que os botões estão visíveis longe da coluna, que o estado troca só na entrada e na saída, que botão recolhido não recebe foco, que o foco de mouse não fica preso num botão oculto, que um botão com foco de teclado não some e que os contatos da página continuam visíveis. As janelas rodam em quatro processos em paralelo.
- `tests/conteudo/test_avisos_globais.py` abre o menu e a faixa de avisos.
- `tests/funcionalidades/test_farmacia_popular_consulta.py` filtra a consulta local, sem enviar formulário externo.
- `tests/layout/test_contraste.py` mede o contraste de todo texto visível em 18 páginas representativas, em 390 e 1440 px, e o texto sobre degradê ou imagem também em 320, 360, 640, 768, 896, 1024 e 1280 px. Também confere o hover dos CTAs coloridos e o conteúdo de cada `<details>` aberto. O método e os limites estão em "Como o contraste é medido".
- `tests/navegacao/test_percursos_navegador.py` segue Home → Serviços → Contato e Home → manual → orçamento → catálogo → POP SNCR, mede onde as âncoras param sob o cabeçalho fixo, navega a vitrine de Manuais por setas e Tab, confere que a coluna lateral das Notícias fica no fluxo da página (presa só se couber inteira, sem rolagem interna) e que, do topo, do meio e do fim da listagem, em telas baixas e com zoom, cada controle dela aparece inteiro abaixo do cabeçalho pela roda do mouse, pelo Tab e pelo Shift+Tab, usa busca, categorias, ordenação e "Ver mais" das notícias e confere o foco do modal do Comunicado. Os links de WhatsApp abrem a página `/whatsapp/`; o redirecionamento para o wa.me é interceptado e conferido, sem enviar mensagem.

### Como o contraste é medido

- Região: as linhas dos nós de texto do próprio elemento (`Range.getClientRects`), sem os espaços das pontas e recortadas pelos ancestrais com `overflow`. Padding, bordas, ícones, espaçamento entre blocos e controles filhos ficam fora por construção. Os botões flutuantes ficam fora da coleta e ocultos na captura. Um elemento pintado por cima do texto (imagem, fundo, pseudo-elemento), achado por `elementsFromPoint` com `pointer-events` liberado, reprova como sobreposição.
- Fundo: a janela ganha a altura da página, o texto fica invisível só pelo `-webkit-text-fill-color` (sem mexer em `color`, layout ou fundos) e a captura dá o fundo já composto: degradês, imagens e camadas transparentes. Contam todos os pixels com centro na região, sem percentil e sem amostragem. Vale o pior pixel; a mensagem de falha diz que fração da região ficou abaixo do mínimo.
- Fundo sólido: quando a captura coincide com as cores CSS dos ancestrais (até 1,5 por canal), a conta também é feita com a composição CSS em ponto flutuante e vale o menor dos dois valores. Quando não coincide (imagem ou camada atrás que não é ancestral), vale só a captura.
- Texto: a cor computada pelo navegador, com o alfa multiplicado pela opacidade dos ancestrais e composta sobre cada cor de fundo. Os pixels do próprio texto, com antialiasing, nunca entram na conta.
- Placeholder: entra quando está visível (campo vazio e ativo), com a cor, a opacidade e a fonte de `getComputedStyle(campo, '::placeholder')`. Ele não tem nó de texto: a região é a caixa de conteúdo do campo, na largura do texto medida com essa fonte, e a captura o esconde como o resto do texto.
- Limiar: 4,5:1, ou 3:1 para texto grande (24 px, ou 14 pt = 56/3 px com peso 700 ou mais). A comparação usa o valor sem arredondar, e a mensagem trunca (4,499 aparece como 4,49).
- O teste confere as próprias premissas: a altura da página e a posição de cada linha não mudam com a janela alta, e esconder o texto não move nada.

Limites:

- A captura é em sRGB, 8 bits por canal, com `--force-color-profile=srgb`; sobre degradê e imagem o fundo carrega esse arredondamento (meio nível por canal) e o pontilhado que o Chromium aplica aos degradês. Monitores e perfis de cor reais variam.
- As fontes externas são bloqueadas para o teste não depender de rede: as páginas carregam a Inter do Google Fonts e, no teste, usam a fonte de reserva. A quebra das linhas muda; a borda esquerda das linhas, que é onde ficam as pontas dos degradês horizontais, não. Com `CONTRASTE_FONTE_EFETIVA=1` o teste deixa a Inter carregar e mede com a fonte de produção (ver "Conferência com a fonte efetiva").
- Larguras fora das listadas não são medidas; sobre degradê, a posição do texto muda continuamente com a largura. As escolhidas são as dos breakpoints, as menores telas e 896 px, onde o container dos artigos deixa de ocupar a janela.
- A opacidade de ancestral é tratada como alfa do texto. Isso é exato quando o grupo com opacidade não tem fundo próprio, que é o caso do site hoje (nenhum texto medido tem opacidade abaixo de 1).
- Ficam de fora: o valor digitado em campos de formulário, o placeholder de campo desabilitado ou já preenchido, texto gerado por `::before`/`::after`, texto dentro de SVG, texto `aria-hidden` ou com opacidade abaixo de 0,1, controles desabilitados, estados de foco e hover fora dos CTAs listados, e o que só aparece por interação além dos `<details>`.
- A sobreposição só é procurada em três pontos de cada linha (10%, 50% e 90% da largura).
- A largura do placeholder vem do `measureText` do canvas; numa `<textarea>`, a altura é estimada pelo número de linhas.

Se o Chromium não estiver instalado, esses testes falham na abertura do navegador. O comando `python -m playwright install chromium` resolve essa dependência.

Os servidores desses testes usam `support.SITE_DIR`: o próprio repositório ou, com `PAGES_SITE_DIR`, a saída do build do GitHub Pages (ver Publicação).

## Tailwind

O `assets/css/tailwind.min.css` é gerado pelo Tailwind 3.4.17, a versão que reproduz byte a byte o arquivo de 22/05/2026 (commit `9e513e9`). O `tailwind.config.js` varre o HTML e o JavaScript de `assets/js/`. Depois de usar uma classe nova no HTML ou no JavaScript, gere de novo na raiz do repositório e atualize o `?v=` do `tailwind.min.css` em todas as páginas:

```powershell
npx tailwindcss@3.4.17 -c tailwind.config.js -i assets/css/tailwind-input.css -o assets/css/tailwind.min.css --minify
```

`tests/layout/test_classes_css.py` falha quando uma classe do HTML ou do JavaScript não tem regra em nenhum CSS do site. As exceções são os ganchos sem estilo próprio listados no teste.

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

### Conferência com a fonte efetiva

O teste de contraste roda sem rede, com a fonte de reserva no lugar da Inter. Na validação da publicação, repita o contraste com a fonte que o site usa de fato, sobre a saída do build:

```powershell
$env:PAGES_SITE_DIR = "$env:TEMP\rcp\site"
$env:CONTRASTE_FONTE_EFETIVA = "1"
python -m pytest tests/layout/test_contraste.py -rs
Remove-Item Env:CONTRASTE_FONTE_EFETIVA, Env:PAGES_SITE_DIR
```

Precisa de acesso a `fonts.googleapis.com` e `fonts.gstatic.com`. Foi essa conferência que achou, em 03/10/2026, o rótulo "Tipos de estabelecimento" de `/sobre/` saindo do card em 320 px: com a Inter, "ESTABELECIMENTO" não cabia e a última letra cruzava a borda (4,34:1). O hífen opcional (`estabele&shy;cimento`) resolveu, e no build final da rodada de acessibilidade os três modos passaram com a Inter.
