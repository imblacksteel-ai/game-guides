// Unciv social policy cost calculator.
// Formula from Unciv's PolicyManager.getPolicyCultureCost (MPL-2.0):
//   cost = (25 + (adopted*3)^2.01) * difficulty * speed * (1 + mapModifier * (cities - 1)), rounded, then down to a multiple of 5.
// Constants come from window.UNCIV_POLICY_CFG (written by scripts/build_unciv.py). UI strings live in data-* attributes.
(function () {
  var cfg = window.UNCIV_POLICY_CFG;
  var root = document.getElementById('policy-calc');
  if (!cfg || !root) return;
  var $ = function (id) { return document.getElementById(id); };
  function fill(sel, obj, def) {
    Object.keys(obj).forEach(function (k) {
      var o = document.createElement('option');
      o.value = k; o.textContent = (root.getAttribute('data-l' + k.toLowerCase()) || k);
      if (k === def) o.selected = true;
      sel.appendChild(o);
    });
  }
  fill($('pc-diff'), cfg.diff, 'Prince');
  fill($('pc-speed'), cfg.speed, 'Standard');
  fill($('pc-map'), cfg.map, 'Medium');
  function cost(n, cities, d, sp, mp) {
    var base = 25 + Math.pow(n * 3, 2.01);
    var c = Math.round(base * d * sp * (1 + mp * (cities - 1)));
    return c - (c % 5);
  }
  function run() {
    var n = Math.max(0, parseInt($('pc-n').value, 10) || 0);
    var cities = Math.max(1, parseInt($('pc-cities').value, 10) || 1);
    var d = cfg.diff[$('pc-diff').value], sp = cfg.speed[$('pc-speed').value], mp = cfg.map[$('pc-map').value];
    $('pc-out').textContent = cost(n, cities, d, sp, mp).toLocaleString();
    var rows = '';
    for (var i = 0; i < 6; i++) {
      rows += '<tr><td>' + (n + i + 1) + '</td><td>' + cost(n + i, cities, d, sp, mp).toLocaleString() +
        '</td><td>' + cost(n + i, cities + 2, d, sp, mp).toLocaleString() + '</td></tr>';
    }
    $('pc-rows').innerHTML = rows;
  }
  root.addEventListener('input', run);
  root.addEventListener('change', run);
  run();
})();
