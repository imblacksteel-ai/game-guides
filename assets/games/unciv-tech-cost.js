// Unciv research cost / turns calculator.
// Formula from Unciv's TechManager.costOfTech (MPL-2.0):
//   cost = base * difficulty * speed / (1 + 0.3 * knownCivsWithTech / remainingMajorCivs) * mapMultiplier * (1 + perCity * (cities - 1)), truncated.
// Constants come from window.UNCIV_TECH_CFG (written by scripts/build_unciv.py). UI strings live in data-* attributes.
(function () {
  var cfg = window.UNCIV_TECH_CFG;
  var root = document.getElementById('tech-calc');
  if (!cfg || !root) return;
  var $ = function (id) { return document.getElementById(id); };
  var lab = function (k) { return root.getAttribute('data-l' + k.toLowerCase()) || k; };
  cfg.techs.forEach(function (t, i) {
    var o = document.createElement('option');
    o.value = i; o.textContent = t[0] + ' (' + t[2] + ', ' + t[1] + ')';
    $('tc-tech').appendChild(o);
  });
  [['tc-diff', cfg.diff, 'Prince'], ['tc-speed', cfg.speed, 'Standard'], ['tc-map', cfg.map, 'Medium']].forEach(function (a) {
    Object.keys(a[1]).forEach(function (k) {
      var o = document.createElement('option');
      o.value = k; o.textContent = lab(k); if (k === a[2]) o.selected = true;
      $(a[0]).appendChild(o);
    });
  });
  function run() {
    var t = cfg.techs[parseInt($('tc-tech').value, 10) || 0];
    var cities = Math.max(1, parseInt($('tc-cities').value, 10) || 1);
    var civs = Math.max(1, parseInt($('tc-civs').value, 10) || 1);
    var known = Math.min(civs, Math.max(0, parseInt($('tc-known').value, 10) || 0));
    var sci = Math.max(0, parseFloat($('tc-sci').value) || 0);
    var m = cfg.map[$('tc-map').value];
    var cost = t[1] * cfg.diff[$('tc-diff').value] * cfg.speed[$('tc-speed').value];
    cost /= 1 + 0.3 * known / civs;
    cost *= m[0] * (1 + m[1] * (cities - 1));
    cost = Math.floor(cost);
    $('tc-cost').textContent = cost.toLocaleString();
    $('tc-turns').textContent = sci > 0 ? Math.ceil(cost / sci) : '—';
  }
  root.addEventListener('input', run);
  root.addEventListener('change', run);
  run();
})();
