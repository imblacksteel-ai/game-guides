// 遠征条件一覧の絞り込み。表はHTMLに埋め込み済み（scripts/render_kancolle_expeditions.py）で、
// ここでは検索語と海域で行を表示/非表示にするだけ。
(function () {
  var table = document.getElementById('exped-table');
  var input = document.getElementById('exped-search');
  var btns = document.getElementById('exped-areas');
  var empty = document.getElementById('exped-empty');
  if (!table || !input || !btns) return;

  var rows = table.querySelectorAll('tbody tr[data-search]');
  var areaRows = table.querySelectorAll('tbody tr.area-row');
  var area = '';

  function apply() {
    var q = input.value.trim().toLowerCase();
    var shownPerArea = {};
    var shown = 0;
    rows.forEach(function (r) {
      var ok = (!area || r.getAttribute('data-area') === area) &&
               (!q || r.getAttribute('data-search').indexOf(q) !== -1);
      r.hidden = !ok;
      if (ok) {
        shown++;
        shownPerArea[r.getAttribute('data-area')] = true;
      }
    });
    areaRows.forEach(function (r) { r.hidden = !shownPerArea[r.getAttribute('data-area')]; });
    if (empty) empty.hidden = shown > 0;
  }

  input.addEventListener('input', apply);
  btns.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-area]');
    if (!b) return;
    area = b.getAttribute('data-area');
    btns.querySelectorAll('button').forEach(function (x) { x.classList.toggle('active', x === b); });
    apply();
  });

  // /games/kancolle/expedition-requirements/#exp-b4 のようなリンクで来たら該当行を強調する。
  if (location.hash) {
    var target = document.getElementById(location.hash.slice(1));
    if (target && target.hasAttribute('data-search')) target.classList.add('exped-hit');
  }
})();
