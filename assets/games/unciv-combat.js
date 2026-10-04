// Unciv combat damage calculator.
// Formula from Unciv's BattleDamage.kt (MPL-2.0):
//   attack  = max(1, attackerStrength * (1 + sum(attack bonuses)/100))
//   defense = max(1, defenderStrength * (1 + sum(defense bonuses)/100))
//   ratio = attack / defense, s = max(ratio, 1/ratio), m = (((s + 3) / 4)^4 + 1) / 2
//   damage to defender = (24 + 12 * rand) * (ratio >= 1 ? m : 1/m) * (1 - (100 - attackerHP) / 300)
//   damage to attacker = (24 + 12 * rand) * (ratio > 1 ? 1/m : m) * (1 - (100 - defenderHP) / 300)   (0 for ranged attackers)
// rand is between 0 and 1 (fixed per turn and tile in the game). UI strings live in data-* attributes.
(function () {
  var root = document.getElementById('combat-calc');
  if (!root) return;
  var $ = function (id) { return document.getElementById(id); };
  var t = function (k) { return root.getAttribute('data-' + k) || k; };
  function num(id, def) { var v = parseFloat($(id).value); return isNaN(v) ? def : v; }
  function dmg(ratio, toAttacker, rand, hpFactor) {
    var s = ratio < 1 ? 1 / ratio : ratio;
    var m = (Math.pow((s + 3) / 4, 4) + 1) / 2;
    if ((toAttacker && ratio > 1) || (!toAttacker && ratio < 1)) m = 1 / m;
    return Math.round((24 + 12 * rand) * m * hpFactor);
  }
  function run() {
    var as = num('cc-as', 10), ahp = Math.min(100, Math.max(1, num('cc-ahp', 100))), ab = num('cc-ab', 0);
    var ds = num('cc-ds', 10), dhp = Math.min(100, Math.max(1, num('cc-dhp', 100))), db = num('cc-db', 0);
    var fort = parseInt($('cc-fort').value, 10) || 0, terr = parseInt($('cc-terr').value, 10) || 0;
    var ranged = $('cc-ranged').checked;
    var A = Math.max(1, as * (1 + ab / 100));
    var D = Math.max(1, ds * (1 + (db + fort + terr) / 100));
    var r = A / D;
    var aF = 1 - (100 - ahp) / 300, dF = 1 - (100 - dhp) / 300;
    var toDmin = dmg(r, false, 0, aF), toDmax = dmg(r, false, 1, aF);
    var toAmin = ranged ? 0 : dmg(r, true, 0, dF), toAmax = ranged ? 0 : dmg(r, true, 1, dF);
    $('cc-A').textContent = A.toFixed(1);
    $('cc-D').textContent = D.toFixed(1);
    $('cc-r').textContent = r.toFixed(2);
    $('cc-tod').textContent = toDmin + '–' + toDmax;
    $('cc-toa').textContent = ranged ? t('noretaliation') : (toAmin + '–' + toAmax);
    var kills = toDmin >= dhp ? t('killsalways') : (toDmax >= dhp ? t('killssometimes') : t('killsnever'));
    $('cc-kill').textContent = kills;
  }
  root.addEventListener('input', run);
  root.addEventListener('change', run);
  run();
})();
