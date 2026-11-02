/* ================================================================
   Serviços (02/11/2026)
   ----------------------------------------------------------------
   Cada serviço é um <details> dentro de <article class="servico" id="...">.
   Quem chega por um endereço com âncora (por exemplo, o link
   /servicos/#servico-sncr da notícia do SNCR) encontra o serviço já aberto.
   Sem este script, a âncora continua levando ao serviço, fechado.
   ================================================================ */
(function () {
  'use strict';

  function abrirDoEndereco() {
    var id = location.hash.slice(1);
    if (!id) return;
    try {
      id = decodeURIComponent(id);
    } catch (erro) {
      return;
    }
    var alvo = document.getElementById(id);
    if (!alvo || !alvo.classList.contains('servico')) return;
    var detalhes = alvo.querySelector('details');
    if (detalhes) detalhes.open = true;
  }

  abrirDoEndereco();
  window.addEventListener('hashchange', abrirDoEndereco);
})();
