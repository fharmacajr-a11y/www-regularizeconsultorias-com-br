/* =================================================================
   Notícias: faixa de filtros abaixo de 1024 px
   Abaixo de 1024 px a coluna de filtros (pesquisa e faixa de categorias e
   ordenação, pages/noticias.css) vem antes da lista, como no HTML.
   1. Botão focado inteiro na faixa. O Chromium só rola a faixa até o botão
      focado quando ele está todo fora dela: um botão cortado pela borda, sob
      o esmaecido, ficava como estava. Com nearest e o scroll-padding-inline
      da faixa, ele aparece inteiro, antes do esmaecido.
   2. Resultado do filtro à vista. Com a faixa no pé da janela, uma categoria
      ou a ordenação mudava a lista abaixo da dobra, sem nada à vista. Depois
      do clique (pelo mouse, pelo toque ou por Enter e Espaço), se o topo do
      1º card não aparece na janela, a página rola de uma vez até a faixa
      ficar logo abaixo do cabeçalho (o scroll-padding-top do html), com o 1º
      card logo depois dela. O foco continua no botão usado. O ouvinte fica na
      faixa e recebe o clique depois do ouvinte do próprio botão no main.js,
      que já atualizou a lista.
   A partir de 1024 px a faixa não rola, a lista fica ao lado da coluna e
   nada muda. Sem JavaScript a faixa continua visível e rola pelo dedo.
   Até 21/10/2026 este arquivo recolhia voltar ao topo e WhatsApp enquanto
   eles passavam pela coluna, que vinha depois da lista. Agora a pesquisa e a
   faixa reservam a faixa da coluna fixa e os botões não recolhem.
   ================================================================= */
(function () {
  'use strict';

  var column = document.querySelector('main aside');
  var filters = document.querySelector('.news-filters');
  var strip = document.querySelector('.news-filters__strip');
  var list = document.getElementById('news-article-list');
  var navbar = document.getElementById('navbar');

  if (!column || !filters || !strip || !list) return;

  strip.addEventListener('focusin', function (event) {
    if (strip.scrollWidth > strip.clientWidth) {
      event.target.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'instant' });
    }
  });

  // Quanto do 1º card precisa aparecer acima do fim da janela: a linha de
  // selos e data e o começo do título.
  var VISIBLE = 96;

  var firstCard = function () {
    var cards = list.querySelectorAll('[data-news-card]');

    for (var index = 0; index < cards.length; index += 1) {
      if (cards[index].getClientRects().length) return cards[index];
    }
    return null;
  };

  var revealResults = function () {
    // Lado a lado (1024 px ou mais): a lista começa no topo da coluna.
    if (column.getBoundingClientRect().bottom > list.getBoundingClientRect().top + 1) return;

    var card = firstCard();
    if (!card) return;

    var top = card.getBoundingClientRect().top;
    var header = navbar ? navbar.getBoundingClientRect().bottom : 0;

    if (top >= header && top <= window.innerHeight - VISIBLE) return;
    filters.scrollIntoView({ block: 'start', behavior: 'instant' });
  };

  filters.addEventListener('click', function (event) {
    if (event.target.closest('[data-news-category], [data-news-sort]')) revealResults();
  });
})();
