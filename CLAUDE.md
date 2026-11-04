# Regras do projeto – site da Regularize Consultoria
- Notícias não têm links externos. A fonte é citada no texto (órgão, ato, data e, quando houver, DOU com edição, seção e página), sem link. O teste tests/conteudo/test_noticias_sem_links_editoriais_externos.py garante isso.
- Comunicados (/comunicado/) podem ter link para fonte oficial, como o Painel de Disponibilidade da Anvisa.
- Nenhum commit ou push sem aprovação explícita do responsável. Prepare, mostre o resultado e espere.

## Notícia consolidada de irregulares: como atualizar

A página `/noticias/anvisa-suspende-medicamento-proibe-produtos-irregulares/` agrupa as medidas por mês, em `<details>`. Novembro de 2026 fica aberto, mostrando só a tabela; os meses anteriores ficam fechados. Em cada mês, a tabela agrupa as linhas pela data do DOU e os detalhes ficam em “Detalhes das resoluções de <mês>”, fechado, com um item recolhido por RE (`<details class="irregulares-re">`, fechado).

- Nova RE: linha na tabela do mês (no grupo da data do DOU: RE, produto ou empresa com link para o item, medida e situação) + item recolhido próprio no mês, com `<summary>` “RE nº X/2026 — produto ou empresa (data do DOU)” e o texto da RE + resumo de duas ou três linhas no topo.
- Mês novo: deixe o mês novo aberto e feche o anterior. Revogação, retificação ou insubsistência entra no item da RE original e na coluna “situação”, sem repetir a resolução em outro quadro.

## Conferência de atos do MAPA

Os ofícios-circulares do MAPA não saem sempre na mesma página. Em toda conferência de atos do MAPA, abra as duas e anote o “Atualizado em” e os números dos ofícios do ano:

- “Legislação – Alimentação Animal”: https://www.gov.br/agricultura/pt-br/assuntos/insumos-agropecuarios/insumos-pecuarios/alimentacao-animal/legislacao-alimentacao-animal
- “Memorandos, Ofícios e Ofícios circulares” (Produtos veterinários > Legislação): https://www.gov.br/agricultura/pt-br/assuntos/insumos-agropecuarios/insumos-pecuarios/produtos-veterinarios/legislacao-1/memorandos-e-oficios

O Ofício-Circular nº 75/2026, sobre a Portaria SDA/MAPA nº 1.617/2026, saiu só na segunda.

## Resumo do topo das notícias

Piloto de 04/11/2026 em três notícias (SNCR, irregulares e MAPA). O bloco “Resumo da notícia” (`data-noticia-resumo`) fica logo abaixo do cartão de datas, antes do corpo, com três pontos, cada um em duas ou três linhas e sem link: o que mudou, desde quando e o que a farmácia (ou a empresa) deve fazer. O botão “Ouvir resumo” lê o bloco com a voz do próprio navegador.

- Toda atualização de uma notícia com resumo revisa o resumo no mesmo commit: o texto visível, a versão falada (`data-leitura`) e o `<time>` de “Conferido com a atualização de”, igual ao `dateModified`. Sem isso, tests/conteudo/test_noticias_resumo.py falha.
- A versão falada diz o mesmo que o item, com as siglas soletradas (“R D C”, “S N C R”) e os números e as datas por extenso, sem algarismo, “nº” ou barra.
