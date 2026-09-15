(function () {
  var LANGS = [
    { code: 'en', label: 'English', prefix: '' },
    { code: 'ja', label: '日本語', prefix: '/ja' },
    { code: 'ko', label: '한국어', prefix: '/ko' },
    { code: 'zh', label: '中文', prefix: '/zh' },
    { code: 'de', label: 'Deutsch', prefix: '/de' },
    { code: 'fr', label: 'Français', prefix: '/fr' },
    { code: 'ar', label: 'العربية', prefix: '/ar' }
  ];

  var path = window.location.pathname;
  var current = 'en';
  var base = path;

  for (var i = 0; i < LANGS.length; i++) {
    var L = LANGS[i];
    if (L.prefix && (path === L.prefix || path.indexOf(L.prefix + '/') === 0)) {
      current = L.code;
      base = path.slice(L.prefix.length) || '/';
      break;
    }
  }

  var mount = document.getElementById('lang-switch');
  if (!mount) return;

  var html = '<button type="button" class="lang-current" aria-haspopup="true" aria-expanded="false">' +
    LANGS.filter(function (L) { return L.code === current; })[0].label +
    '<svg viewBox="0 0 20 20" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 7l5 5 5-5"/></svg>' +
    '</button><ul class="lang-menu" role="menu">';

  LANGS.forEach(function (L) {
    var href = (L.prefix + base).replace(/\/{2,}/g, '/');
    var cls = (L.code === current) ? ' class="active"' : '';
    html += '<li><a role="menuitem" href="' + href + '"' + cls + '>' + L.label + '</a></li>';
  });
  html += '</ul>';

  mount.innerHTML = html;

  var btn = mount.querySelector('.lang-current');
  btn.addEventListener('click', function () {
    var open = mount.classList.toggle('open');
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  });
  document.addEventListener('click', function (e) {
    if (!mount.contains(e.target)) {
      mount.classList.remove('open');
      btn.setAttribute('aria-expanded', 'false');
    }
  });
})();
