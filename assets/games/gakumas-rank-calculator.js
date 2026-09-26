// 学マス「初」プロデュースの評価値計算機（英日共通）。UI文言は各HTMLの window.GK_I18N に持つ。
// 式はコミュニティの検証結果（gakumas-tools, BSD-3-Clause ほか）を元にし、
// 通常難易度の係数・順位点・スコア換算は複数の攻略情報と一致を確認済み。
(function () {
  var I = window.GK_I18N || {};

  var DIFF = {
    regular: { cap: 1000, mult: 23, bonus: { 1: 30, 2: 20, 3: 10, 4: 0 } },
    pro:     { cap: 1500, mult: 23, bonus: { 1: 30, 2: 20, 3: 10, 4: 0 } },
    master:  { cap: 1800, mult: 23, bonus: { 1: 30, 2: 20, 3: 10, 4: 0 } },
    legend:  { cap: 3000, mult: 21, bonus: { 1: 160, 2: 80, 3: 40, 4: 0 } }
  };
  var PLACE_RATING = { 1: 1700, 2: 900, 3: 500, 4: 0 };

  // 最終試験スコア → 評価値。[この値を超えた分, 係数×10000] を上の区間から順に適用する。
  // 係数を整数で持つのは浮動小数点の誤差（例: 3090×2.3 = 7106.999…）で1ずれるのを防ぐため。
  var FINAL = [[40000, 100], [30000, 200], [20000, 400], [10000, 800], [5000, 1500], [0, 3000]];
  var FINAL_LEGEND = [[2000000, 0], [600000, 10], [500000, 80], [300000, 100], [0, 150]];
  var MID_LEGEND = [[200000, 0], [60000, 10], [50000, 20], [40000, 30], [30000, 80], [20000, 500], [10000, 800], [0, 1100]];

  var RANKS = [['S5', 35000], ['S4+', 30000], ['S4', 26000], ['SSS+', 23000], ['SSS', 20000], ['SS+', 18000],
    ['SS', 16000], ['S+', 14500], ['S', 13000], ['A+', 11500], ['A', 10000], ['B+', 8000], ['B', 6000],
    ['C+', 4500], ['C', 3000]];

  function scoreToRating(score, brackets) {
    var r = 0;
    for (var i = 0; i < brackets.length; i++) {
      if (score > brackets[i][0]) {
        r += (score - brackets[i][0]) * brackets[i][1];
        score = brackets[i][0];
      }
    }
    return Math.floor(r / 10000);
  }

  // 評価値 target に届く最小の最終試験スコア。届かなければ null。
  function requiredScore(target, brackets) {
    if (target <= 0) return 0;
    // 最上段の係数が0ならそこが上限。0でなければ上限なし（通常難易度は4万点超も0.01倍で加算される）。
    var lo = 0, hi = brackets[0][1] === 0 ? brackets[0][0] + 1 : 100000000;
    if (scoreToRating(hi, brackets) < target) return null;
    while (lo < hi) {
      var mid = Math.floor((lo + hi) / 2);
      if (scoreToRating(mid, brackets) >= target) hi = mid; else lo = mid + 1;
    }
    return lo;
  }

  var root = document.getElementById('gk-calc');
  if (!root) return;
  var state = { diff: 'pro', place: 1 };
  var $ = function (id) { return document.getElementById(id); };
  var fmt = function (n) { return n.toLocaleString('en-US'); };

  function num(id) {
    var v = parseInt($(id).value, 10);
    return isNaN(v) || v < 0 ? 0 : v;
  }

  function update() {
    var d = DIFF[state.diff];
    var legend = state.diff === 'legend';
    $('gk-mid-wrap').hidden = !legend;
    $('gk-cap').textContent = fmt(d.cap);
    $('gk-bonus').textContent = '+' + d.bonus[state.place];

    var paramSum = 0;
    ['gk-vo', 'gk-da', 'gk-vi'].forEach(function (id) {
      paramSum += Math.min(num(id) + d.bonus[state.place], d.cap);
    });
    var base = PLACE_RATING[state.place] + Math.floor(paramSum * d.mult / 10);
    if (legend) base += scoreToRating(num('gk-mid'), MID_LEGEND);
    var brackets = legend ? FINAL_LEGEND : FINAL;

    var final = $('gk-final').value === '' ? null : num('gk-final');
    var total = base + (final === null ? 0 : scoreToRating(final, brackets));
    $('gk-rating').textContent = fmt(total);
    var rank = '—';
    for (var i = 0; i < RANKS.length; i++) if (total >= RANKS[i][1]) { rank = RANKS[i][0]; break; }
    $('gk-rank').textContent = rank;
    $('gk-rating-label').textContent = final === null ? I.ratingBeforeFinal : I.rating;

    var rows = RANKS.map(function (r) {
      var need = requiredScore(r[1] - base, brackets);
      var cls = need === null ? ' class="gk-na"' : '';
      var cell = need === null ? I.unreachable : (need === 0 ? I.already : fmt(need));
      return '<tr' + cls + '><td>' + r[0] + '</td><td>' + fmt(r[1]) + '</td><td>' + cell + '</td></tr>';
    });
    $('gk-targets').innerHTML = rows.join('');
  }

  function bindGroup(id, key, parse) {
    var g = $(id);
    g.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-v]');
      if (!b) return;
      state[key] = parse(b.getAttribute('data-v'));
      g.querySelectorAll('button').forEach(function (x) { x.classList.toggle('active', x === b); });
      update();
    });
  }
  bindGroup('gk-diff', 'diff', String);
  bindGroup('gk-place', 'place', function (v) { return parseInt(v, 10); });
  root.addEventListener('input', update);
  update();
})();
