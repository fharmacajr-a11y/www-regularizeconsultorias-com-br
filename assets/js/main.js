/**
 * Regularize Consultoria – main.js
 * -----------------------------------------------------------------
 * Responsabilidades:
 *   1. Adicionar sombra na navbar ao fazer scroll
 *   2. Toggle do menu mobile (botão hamburguer)
 *   3. Marcar o link da página atual como "ativo" na navbar
 * -----------------------------------------------------------------
 */

(function () {
  'use strict';

  /* =================================================================
     1. NAVBAR: adiciona classe "scrolled" ao fazer scroll
        → custom.css aplica box-shadow quando #navbar tem .scrolled
     ================================================================= */
  var navbar = document.getElementById('navbar');

  if (navbar) {
    var handleScroll = function () {
      if (window.scrollY > 10) {
        navbar.classList.add('scrolled');
      } else {
        navbar.classList.remove('scrolled');
      }
    };

    // Listener de scroll com passive:true para melhor performance
    window.addEventListener('scroll', handleScroll, { passive: true });

    // Executar uma vez ao carregar (caso a página já comece com scroll)
    handleScroll();
  }

  /* =================================================================
     2. MENU MOBILE: toggle ao clicar no botão hamburguer
        Alterna visibilidade do #mobile-menu e troca os ícones
     ================================================================= */
  var menuToggle    = document.getElementById('menu-toggle');
  var mobileMenu    = document.getElementById('mobile-menu');
  var iconHamburger = document.getElementById('icon-hamburger');
  var iconClose     = document.getElementById('icon-close');

  if (menuToggle && mobileMenu) {

    menuToggle.addEventListener('click', function () {
      var isOpen = !mobileMenu.classList.contains('hidden');

      if (isOpen) {
        // ---------- Fechar menu ----------
        mobileMenu.classList.add('hidden');
        iconHamburger.classList.remove('hidden');
        iconClose.classList.add('hidden');
        menuToggle.setAttribute('aria-expanded', 'false');
      } else {
        // ---------- Abrir menu ----------
        mobileMenu.classList.remove('hidden');
        iconHamburger.classList.add('hidden');
        iconClose.classList.remove('hidden');
        menuToggle.setAttribute('aria-expanded', 'true');
      }
    });

    // Fechar automaticamente ao clicar em qualquer link do menu mobile
    mobileMenu.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        mobileMenu.classList.add('hidden');
        iconHamburger.classList.remove('hidden');
        iconClose.classList.add('hidden');
        menuToggle.setAttribute('aria-expanded', 'false');
      });
    });
  }

  /* =================================================================
     3. LINK ATIVO: detecta a página atual e adiciona classe "active"
        ao link correspondente na navbar
        → custom.css aplica cor e font-weight no link .active
     ================================================================= */
  var currentFile = window.location.pathname.split('/').pop() || 'index.html';

  document.querySelectorAll('#navbar nav a[href]').forEach(function (link) {
    var href = link.getAttribute('href');

    // Considera "/" ou "" como index.html
    if (
      href === currentFile ||
      (currentFile === '' && href === 'index.html')
    ) {
      link.classList.add('active');
    }
  });

  /* =================================================================
     4. BADGE DE AVISOS: atualiza contagem no botão de comunicados
        - Em comunicado.html: conta os <article> dentro de #avisos-lista
          automaticamente. Ao adicionar ou remover um aviso lá, o número
          já atualiza sozinho sem precisar alterar mais nada.
        - Nas demais páginas: use a variável AVISOS_COUNT abaixo.
          Atualize-a sempre que adicionar ou remover avisos.
     ================================================================= */
  var avisoLista = document.getElementById('avisos-lista');
  var AVISOS_COUNT = avisoLista
    ? avisoLista.querySelectorAll('article:not([data-placeholder])').length
    : 0; // Conta apenas avisos reais (sem data-placeholder="true")

  document.querySelectorAll('.aviso-badge').forEach(function (badge) {
    badge.textContent = AVISOS_COUNT;
    badge.style.display = AVISOS_COUNT > 0 ? 'flex' : 'none';
  });

})();
