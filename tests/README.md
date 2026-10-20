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

### Rede

Todo contexto do Chromium nasce por `support.new_context` ou `support.new_page`, com a rota de rede já instalada antes da primeira navegação:

- `127.0.0.1` e `localhost` passam.
- O CSS do Google Fonts vira o `@font-face` da Inter local: o mesmo `assets/fonts/inter-latin-variable-v20.woff2` e os mesmos descritores da home. As medidas de geometria (quebras de linha do rodapé, colunas, botões flutuantes) não dependem mais da rede, e a mesma fonte vale no fonte e no artefato. Se o arquivo faltar, o teste falha na hora.
- Todo o resto é abortado e anotado em `support.BLOCKED_REQUESTS`: AdSense (os 83 artigos têm o script), `wa.me`, redes sociais e páginas oficiais.

Os testes que rodam em subprocesso importam `support` pelo `PYTHONPATH` montado em `support.subprocess_env()`. As sondas das Notícias aceitam `allow=(base,)` para rodar contra o domínio público sem liberar outros hosts.

`tests/navegacao/test_rede_dos_testes.py` cuida dessa garantia:

- Lê o código e falha se algum teste criar contexto direto com `browser.new_context`/`browser.new_page`.
- Abre um artigo com AdSense e confere que o pedido foi abortado, que nada externo terminou de carregar e que a Inter local carregou. Externo é o que não vem da origem servida (esquema, host e porta da base): aqui, o servidor em 127.0.0.1; numa verificação de produção que troque a base, o domínio testado. O resultado conta os acessos por origem.

Com `RC_REDE_LOG=<pasta>`, cada acesso externo tratado (fonte local servida ou pedido bloqueado) vira uma linha JSON com o teste e o processo, num arquivo `rede-<pid>.jsonl` por processo. Use para comprovar uma rodada.

O cabeçalho do pytest (`tests/conftest.py`) diz qual site os testes de navegador serviram: o fonte (working tree) ou o artefato (`PAGES_SITE_DIR`). Também mostra o HEAD e a política de rede.

- `tests/layout/test_rodape_espaco.py` abre as páginas num processo separado, varia a largura e mede o rodapé no fim da rolagem. O processo separado evita o loop do Playwright deixado pela consulta da Farmácia Popular.
- `tests/layout/test_whatsapp_flutuante_global.py` confere posição fixa, tamanho, se o botão não cobre texto e se a coluna continua na janela no fim da página.
- `tests/layout/test_noticias_cards.py` confere a ordenação visual dos cards, com a precisão da data de cada um (data só com o dia conta como 00h00 de Brasília; empate mantém a ordem do HTML), e que nem a posição nem o filtro, a busca ou a ordenação trocam o formato do card (modelo único desde 12/10/2026).
- `tests/layout/test_noticias_cards_modelo_unico.py` lê os estilos calculados dos elementos equivalentes de cada card visível de /noticias/ (card, linha de selos, selo, categoria, data, título, resumo e botão; as cores ficam fora, porque são do tipo e da categoria) em treze janelas de 320 a 1440 px, quatro delas com a barra de rolagem clássica nos limites, e nos estados de carga, "Ver mais notícias", filtro, filtro com "Ver mais", busca e ordem "Mais velha". A união dos estados tem de ter um único estilo por elemento. Também exige card sem "Atualizado em" ou "Publicado em", título e resumo inteiros, nenhuma rolagem horizontal e o anel de foco do botão visível nos cinco primeiros e num card revelado.
- `tests/layout/test_noticias_cards_faixa.py` confere que título e resumo dos cards da listagem ficam fora da faixa dos botões flutuantes, nos cinco primeiros e nos revelados (um só modelo de card desde 12/10/2026), em dez janelas de 360 a 1440 px (incluindo 640, 767/768 e 1359/1360). Clica em "Ver mais notícias", leva cada linha real do texto (`Range.getClientRects`) à faixa do WhatsApp e à do voltar ao topo, rolando pelo que os retângulos pedem, e exige 8 px de folga até o botão, com 0,5 px de tolerância numérica. Linha que não alcança a faixa fica como não aplicável, com o motivo, e não conta como aprovada. Também confere que a reserva é a do modelo único (8 px exatos abaixo de 1280 px) e zera a partir de 1360 px, que nenhum card visível perde o formato compacto e que o CTA do card do caso de origem em 768 px e o do primeiro card em 360 px abrem a matéria certa.
- `tests/layout/test_institucional_faixa_controles.py` confere que o texto e os alvos clicáveis da Home e de Serviços não passam sob voltar ao topo e WhatsApp, em oito janelas de 320 a 1280 px (incluindo 639/640) e em 320, 890, 1024 e 1360 px com a barra de rolagem clássica do Chromium, porque as media queries usam a largura da janela e o layout usa a largura útil. Junta as palavras de cada nó de texto do `<main>` (`Range.getClientRects`, sem SVG) em linhas e mede as caixas de todos os links e botões do `<main>`, inclusive os cards-link de serviços e os cards da vitrine de Manuais; linhas e caixas são recortadas pelos ancestrais com overflow, então só conta a parte exposta. Leva cada linha e cada caixa ao centro de cada controle visível, rolando pelo que os retângulos pedem, e falha com qualquer interseção de área positiva; não há tolerância. Na vitrine, confere que a janela do carrossel termina antes da coluna e percorre os estados horizontais: cada posição de encaixe em cada altura que leva uma linha ou um card à faixa de um controle, avanço até o fim e retorno pelas setas, foco de cada card pelo teclado (Tab e Shift+Tab, com o card inteiro na janela) e rolagem pela roda do mouse, medindo também os quadros intermediários do movimento. Em 375 × 667 exige que cada linha dos cards Polícia Federal (Home) e SNCR (Serviços), os casos da Fase 1O, passe pela faixa dos dois controles. Também confere o tamanho e a posição fixa dos controles, a ausência de rolagem horizontal da página e de linha fora da caixa do próprio bloco. Só o rodapé, comum a todas as páginas, fica fora.
- `tests/layout/test_sobre_equipe_faixa_controles.py` confere o mesmo para Sobre e Equipe: texto (títulos, parágrafos, listas, nomes e qualificações) e caixas de links e botões do `<main>` fora de voltar ao topo e WhatsApp, em dezesseis janelas de 320 a 1440 px, nos limites das regras de página (359/360 px úteis, 639/640, 699/700, 819/820, 1023/1024, 1279/1280), e em oito janelas com a barra de rolagem clássica. Usa o mesmo método do teste anterior (palavras por `Range.getClientRects`, sem SVG nem o título `.sr-only`, caixas por `getClientRects`, recorte pelo overflow e descarte de fragmentos menores que 0,5 px) e falha com qualquer interseção de área positiva. Também mede a passagem do voltar ao topo nos `scrollY` até 300 (a caixa dele mesmo invisível, porque a transição só muda a opacidade) e a chegada ao rodapé, a cada 40 px nos últimos 400 px. Exige os quatro casos do parecer da Fase 1Q pelas mesmas palavras e pela mesma caixa: "Ser referência nacional em consultoria de" (Sobre) e "O atendimento da Regularize é distribuído entre" (Equipe) em 375 × 667, e a caixa inteira de "Conhecer os Serviços" do CTA final das duas páginas em 640 × 800. Confere ainda o tamanho e a posição fixa dos controles, a ausência de rolagem horizontal, de linha fora do bloco, de palavra recortada por overflow e de ellipsis ou line-clamp. O `sobre.css` passou a ter `?v=` e entrou em `VERSIONED_ASSETS` de `tests/seo/test_versao_assets.py`.
- `tests/layout/test_layout_comum_faixa_controles.py` cobre as demais estruturas e o rodapé comum: Home, Serviços, Comunicado, Farmácia Popular, listagem de notícias, catálogo e dois manuais, Contato, Política de Privacidade e matérias das três combinações de CSS, em cinco janelas de 320 a 1280 px, três com a barra de rolagem clássica e quatro telas baixas em paisagem (568x320, 667x375, 740x360 e 812x375), em que o herói e o começo da página entram no alcance da coluna. Como a coluna de voltar ao topo e WhatsApp não muda de posição horizontal, exige que cada linha de texto do `<main>` e do rodapé que ela alcança termine pelo menos 8 px antes dela, e que cada caixa clicável alcançável termine antes dela com folga de pelo menos max(8 px, contorno de foco, sombra visível), com contorno e sombra lidos no estado `:focus-visible` real e no repouso. O alcance é vertical e considera a ancoragem do `main.js`: cada controle varre, no documento, da posição de repouso (scrollY 0 para o WhatsApp, acima de 300 para o voltar ao topo) até a posição real dele no fim da página, ancorada ou não; os créditos do rodapé e o fechamento do Comunicado, abaixo da parada, não são alcançados. No fim real da página, com a coluna ancorada ou fixa, nada do `<main>` e do rodapé pode encostar nela. Também exige que nenhuma palavra do H1 passe da caixa do título (o caso de "estabelecimentos" em 320 px) nem seja partida entre linhas fora de um hífen opcional (`&shy;`), que os cards de "Por que escolher" da Home não fiquem sob a coluna e que a seta seguinte da vitrine cumpra o critério de foco, e confere o tamanho e a posição dos controles e a ausência de rolagem horizontal. Na listagem de notícias, a coluna de filtros fica fora porque `assets/js/pages/noticias.js` recolhe os botões enquanto ela passa. O `manuais-e-pops.css` passou a ter `?v=` e entrou em `VERSIONED_ASSETS`. Os títulos com palavra mais larga que a caixa estreita (largura útil abaixo de 375 px) têm um hífen opcional no HTML, que só vale nessa faixa (`hyphens: manual` por media query e container query; `hyphens: none` acima); o texto sem o hífen opcional é o mesmo.
- `tests/layout/test_catalogo_manuais_resumos.py` abre o catálogo de Manuais e POPs em treze janelas (seis sem barra de 320 a 1440 px, três com a barra de rolagem clássica e quatro telas baixas) como carrega, expandido por "Ver mais documentos" pelo teclado e recolhido de novo. Em cada card exibido, mede a área exposta de cada palavra (`Range.getClientRects` recortado pelos ancestrais com overflow hidden ou clip, incluído o próprio parágrafo) e exige o resumo inteiro, inclusive a última palavra, com altura natural (sem limite de linhas), todo o texto do card exposto, cada linha 8 px antes da coluna de voltar ao topo e WhatsApp, as caixas clicáveis e o botão do catálogo com folga para o contorno de foco e a sombra, e expansão e recolhimento coerentes, sem rolagem horizontal. Conteúdo de contêiner rolável (tabela, janela de carrossel) é alcançado pela rolagem e não conta como oculto; um par de calibração (bloco rolável e bloco com line-clamp) confere essa separação. Entrou na revisão v2 do layout comum, quando o limite de três linhas do resumo saiu.
- `tests/layout/test_noticias_alinhamento.py` mede as bordas dos quatro blocos da coluna lateral das Notícias de 320 a 1920 px, incluindo 639/640, 767/768 e 1023/1024. Empilhados (até 1023 px), eles têm de terminar nas mesmas bordas de "Orientação técnica", dos cards de notícia e de "Sobre o conteúdo"; a partir de 1024 px, a lateral fica na borda esquerda de "Sobre o conteúdo" e a lista na direita. Com cada botão flutuante na altura de cada controle da coluna, o centro do controle continua livre.
- `tests/layout/test_noticias_flutuantes.py` confere que os botões flutuantes (voltar ao topo e WhatsApp) não escondem nada da coluna lateral das Notícias. Empilhada, ela passa sob a coluna fixa, e o `assets/js/pages/noticias.js` marca essa coluna com `inert` enquanto as duas se cruzam (com 1rem de folga); o `pages/noticias.css` recolhe os botões. Em 13 janelas (celular, 639/640, 767/768, meia tela de 940 e 960, 1023/1024 e desktop), o teste reproduz o caso de 960 px com a contagem "54" de ANVISA na altura do WhatsApp, rola com a roda em passos de 40 px para baixo e para cima, percorre a coluna por Tab e Shift+Tab, aplica filtros pelo mouse e pelo teclado e faz uma busca. Também salta de uma vez do fim da página, com a coluna fixa ancorada acima dos créditos pelo `main.js`, até as categorias, e das categorias até o fim; a medida vem logo depois do salto, e o teste confere que houve um único evento de rolagem, para nenhuma rolagem extra esconder um defeito. Por fim, redimensiona a janela para 1440 px e de volta com a coluna sob os botões. Em cada parada, nenhum botão visível pode cobrir nomes e contagens das categorias, campos, textos dos controles ou o anel de foco do controle focado. Também confere que os botões estão visíveis longe da coluna, que o estado troca só na entrada e na saída, que botão recolhido não recebe foco, que o foco de mouse não fica preso num botão oculto, que um botão com foco de teclado não some e que os contatos da página continuam visíveis. As janelas rodam em quatro processos em paralelo.
- `tests/conteudo/test_avisos_globais.py` abre o menu e a faixa de avisos.
- `tests/conteudo/test_listagem_rotulo_atualizacao.py` (estático) exige que cada card da listagem mostre a data editorial válida da própria matéria, sem prefixo (desde 12/10/2026 o card não mostra "Atualizado em"; a página da matéria continua com "Publicado em" e "Atualizado em"). Regra, sem exceção por matéria: a data válida é a atualização que a matéria declara (`dateModified` diferente de `datePublished` e "Atualizado em" visível, posterior à publicação), senão a publicação; vale a forma mais precisa entre o JSON-LD e o `<time>` visível; o card leva essa data no texto ("DD/MM/AAAA • HHhMM", ou "DD/MM/AAAA" quando ela só tem o dia) e no `datetime`, e `data-updated` só quando ela é uma atualização. Cobre as sete matérias atualizadas no lote de 09/10/2026 e o card do CNES 06/2026, cuja atualização só tem o dia. A ordem é protegida em `tests/conteudo/test_ordenacao_noticias.py`.
- `tests/funcionalidades/test_farmacia_popular_consulta.py` filtra a consulta local, sem enviar formulário externo.
- `tests/layout/test_noticias_cta_contraste.py` mede o selo e o botão dos cards dos quatro tipos (Atualização, Informativo, Urgente e Orientação) na carga, em "Ver mais", na busca, na categoria e na ordenação, em 390, 960, 1023, 1024 e 1440 px: 4,5:1 em normal, hover e foco de teclado, as cores de `assets/css/pages/noticias-tipos.css` iguais em todos os cenários, a pílula e o anel visível no foco e o mesmo artigo de cada tipo, oculto na carga, com o mesmo formato em "Ver mais", na busca e na categoria (modelo único desde 12/10/2026). Sem exceções de contraste.
- `tests/layout/test_noticias_hero_geometria.py` confere a folga externa dos cabeçalhos dos artigos (Proposta A: 1.5rem abaixo de 640 px, 2rem entre 640 e 767 px e 2.75rem a partir de 768 px). Detecta e rejeita a folga antiga (2.5rem, 3rem e 5rem), valida os quatro tipos e as duas famílias de CSS com títulos curtos e longos, e assegura ausência de rolagem horizontal e sobreposição.
- `tests/conteudo/test_noticias_tipos_centralizados.py` (estático) exige as cores dos quatro tipos só em `assets/css/pages/noticias-tipos.css`, carregado por último em toda página de notícia e no template; nenhuma outra folha ou `<style>` pinta as classes de tipo; selos, botões e cabeçalhos desses tipos sem utilitários de cor; e a paleta com 4,5:1 entre o texto e cada fundo.
- `tests/layout/test_contraste.py` mede o contraste de todo texto visível em 20 páginas representativas, em 390 e 1440 px, e o texto sobre degradê ou imagem também em 320, 360, 640, 768, 896, 1024 e 1280 px. Também confere o hover dos CTAs coloridos e o conteúdo de cada `<details>` aberto. O método e os limites estão em "Como o contraste é medido".
- `tests/navegacao/test_percursos_navegador.py` segue Home → Serviços → Contato e Home → manual → orçamento → catálogo → POP SNCR, mede onde as âncoras param sob o cabeçalho fixo, navega a vitrine de Manuais por setas e Tab, confere que a coluna lateral das Notícias fica no fluxo da página (presa só se couber inteira, sem rolagem interna) e que, do topo, do meio e do fim da listagem, em telas baixas e com zoom, cada controle dela aparece inteiro abaixo do cabeçalho pela roda do mouse, pelo Tab e pelo Shift+Tab, usa busca, categorias, ordenação e "Ver mais" das notícias e confere o foco do modal do Comunicado. Os links de WhatsApp abrem a página `/whatsapp/`; o redirecionamento para o wa.me é interceptado e conferido, sem enviar mensagem.
- `tests/navegacao/test_noticias_tab_rapido.py` aperta Tab sem pausa do topo da listagem de notícias até o link do 1º card, em 960x900, 1440x900 e 390x844, com o CSS real e sem desligar a rolagem suave. Espera a página parar e exige o link com o foco, inteiro na janela, abaixo da navbar e sem nada sobre o centro dele. Com `scroll-behavior: smooth` no `html` (base.css até 19/10/2026), a rolagem até o fim da coluna lateral continuava depois do foco e deixava o link fora da tela em 960 e 1440. Desde essa correção o `base.css` tem `?v=` e está em `VERSIONED_ASSETS`.
- `tests/navegacao/test_ancora_fonte_lenta.py` abre `/comunicado/#instabilidade-anvisa-2026-10-19` em 390x844 e 1280x900 com a Inter entregue por um servidor local com 300 e 800 ms de atraso, espera a página parar e a fonte carregar e exige o card a no máximo 24 px abaixo do cabeçalho, inteiro na janela, e o `html` sem rolagem suave. Com `scroll-behavior: smooth` no `custom.min.css` (até 20/10/2026), o destino era calculado com a fonte de reserva e o card parava 358 px (390) e 160 px (1280) abaixo do cabeçalho, como ao vivo depois do deploy de 64beb17. Os demais testes servem a Inter na hora e não reproduzem isso.
- `tests/navegacao/test_menu_mobile.py` usa o menu mobile na home (`components.css`) e no Comunicado (`custom.min.css`) em paisagem de celular, em retrato, em 899 px e com zoom de 200%: abre pelo botão, alcança cada destino pela roda sobre o menu e por Tab, ativa Notícias, Contato e AVISOS, fecha por Escape e pelo botão, redimensiona e gira a tela com o menu aberto e abre no fim da página. Guarda o estado de voltar ao topo e WhatsApp antes de abrir, no início e no fim da página, e confere que, fechado pelo botão ou por Escape, cada um volta como estava (visível, clicável, mesma posição, coluna ancorada ou não, sem rolar a página); com o menu aberto, nenhum deles fica visível ou clicável. Em 899 px passa a 900 e volta com o menu aberto e o foco em Contato: navegação desktop, nenhum foco oculto, estado do botão e do menu de acordo e flutuantes de volta. Os controles são achados pelo nome e pelo destino. Em todas as páginas com o cabeçalho, mede a altura dele fechado, o menu aberto dentro da janela e o botão livre no fim da página. O zoom de 400% fica de fora: ali a faixa e a linha principal ocupam 87% da janela (pendência à parte).

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
- Por padrão o teste mede com a fonte de reserva: a rota de rede também aborta as fontes externas (`fonts="block"`). A quebra das linhas muda; a borda esquerda das linhas, que é onde ficam as pontas dos degradês horizontais, não. Com `CONTRASTE_FONTE_EFETIVA=1` entra a Inter local, o mesmo arquivo que as páginas usam (ver "Conferência com a fonte efetiva").
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

O teste de contraste roda por padrão com a fonte de reserva no lugar da Inter. Na validação da publicação, repita o contraste com a Inter, sobre a saída do build:

```powershell
$env:PAGES_SITE_DIR = "$env:TEMP\rcp\site"
$env:CONTRASTE_FONTE_EFETIVA = "1"
python -m pytest tests/layout/test_contraste.py -rs
Remove-Item Env:CONTRASTE_FONTE_EFETIVA, Env:PAGES_SITE_DIR
```

Desde 04/10/2026 a Inter vem do arquivo local (`assets/fonts/inter-latin-variable-v20.woff2`) pela rota de rede dos testes, sem acesso ao Google Fonts. Foi essa conferência que achou, em 03/10/2026, o rótulo "Tipos de estabelecimento" de `/sobre/` saindo do card em 320 px: com a Inter, "ESTABELECIMENTO" não cabia e a última letra cruzava a borda (4,34:1). O hífen opcional (`estabele&shy;cimento`) resolveu, e no build final da rodada de acessibilidade os três modos passaram com a Inter.
