// 建造時間の逆引き。表はHTMLに埋め込み済み（scripts/build_kancolle_construction.py）で、
// 入力が時間（1:25 / 01:25:00 / 85）ならその建造時間の行を、それ以外なら艦名で絞り込む。
(function () {
  var table = document.getElementById('build-table');
  var input = document.getElementById('build-search');
  var empty = document.getElementById('build-empty');
  if (!table || !input) return;
  var rows = table.querySelectorAll('tbody tr[data-time]');

  function toMinutes(q) {
    var m = q.match(/^(\d{1,2}):(\d{2})(?::\d{2})?$/);
    if (m) return parseInt(m[1], 10) * 60 + parseInt(m[2], 10);
    if (/^\d{1,3}$/.test(q)) return parseInt(q, 10);
    return null;
  }

  function apply() {
    var q = input.value.trim().toLowerCase();
    var mins = toMinutes(q);
    var shown = 0;
    rows.forEach(function (r) {
      var ok = !q || (mins !== null ? parseInt(r.getAttribute('data-time'), 10) === mins
                                    : r.getAttribute('data-search').indexOf(q) !== -1);
      r.hidden = !ok;
      if (ok) shown++;
    });
    if (empty) empty.hidden = shown > 0;
  }

  input.addEventListener('input', apply);
})();
