# Regras do projeto – site da Regularize Consultoria
- Notícias não têm links externos. A fonte é citada no texto (órgão, ato, data e, quando houver, DOU com edição, seção e página), sem link. O teste tests/conteudo/test_noticias_sem_links_editoriais_externos.py garante isso.
- Comunicados (/comunicado/) podem ter link para fonte oficial, como o Painel de Disponibilidade da Anvisa.
- Nenhum commit ou push sem aprovação explícita do responsável. Prepare, mostre o resultado e espere.

## Notícia consolidada de irregulares: como atualizar

A página `/noticias/anvisa-suspende-medicamento-proibe-produtos-irregulares/` agrupa as medidas por mês, em `<details>`. Outubro de 2026 fica aberto, mostrando só a tabela; os meses anteriores ficam fechados. Em cada mês, a tabela agrupa as linhas pela data do DOU e os detalhes ficam em “Detalhes das resoluções de <mês>”, fechado, com um item recolhido por RE (`<details class="irregulares-re">`, fechado).

- Nova RE: linha na tabela do mês (no grupo da data do DOU: RE, produto ou empresa com link para o item, medida e situação) + item recolhido próprio no mês, com `<summary>` “RE nº X/2026 — produto ou empresa (data do DOU)” e o texto da RE + resumo de duas ou três linhas no topo.
- Mês novo: deixe o mês novo aberto e feche o anterior. Revogação, retificação ou insubsistência entra no item da RE original e na coluna “situação”, sem repetir a resolução em outro quadro.
