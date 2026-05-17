(function () {
  'use strict';
  var KEY = 'di-home-theme';
  var THEMES = ['broadsheet', 'editorial'];
  var root = document.getElementById('home');
  if (!root) { return; }

  function apply(theme) {
    if (THEMES.indexOf(theme) === -1) { theme = 'broadsheet'; }
    root.className = 'theme-' + theme;
    var buttons = document.querySelectorAll('[data-theme]');
    for (var i = 0; i < buttons.length; i++) {
      var match = buttons[i].getAttribute('data-theme') === theme;
      buttons[i].classList.toggle('is-active', match);
      buttons[i].setAttribute('aria-pressed', match ? 'true' : 'false');
    }
  }

  var stored = null;
  try { stored = localStorage.getItem(KEY); } catch (e) {}
  apply(stored || 'broadsheet');

  var buttons = document.querySelectorAll('[data-theme]');
  for (var i = 0; i < buttons.length; i++) {
    buttons[i].addEventListener('click', function () {
      var theme = this.getAttribute('data-theme');
      apply(theme);
      try { localStorage.setItem(KEY, theme); } catch (e) {}
    });
  }
})();
