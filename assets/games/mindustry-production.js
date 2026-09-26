// Mindustry 生産計算機（英日共通）。データは scripts/build_mindustry_crafters.py が生成する
// /assets/data/mindustry-crafters.json。UI文言は各HTMLの window.MDT_I18N に持つ。
(function () {
  var I = window.MDT_I18N || {};
  var lang = document.documentElement.lang === 'ja' ? 'ja' : 'en';
  var root = document.getElementById('mdt-calc');
  if (!root) return;
  var $ = function (id) { return document.getElementById(id); };
  var fmt = function (v) { return (Math.round(v * 100) / 100).toLocaleString('en-US'); };
  var data, byId = {};

  // アイテムは1サイクルあたりの個数、液体は毎秒。どちらも「1棟あたり毎秒」に揃える。
  function perSec(x, c) { return x.kind === 'liquid' ? x.per_sec : x.amount * 60 / c.craft_time; }
  function resName(x) { return data.resources[x.kind + ':' + x.id][lang]; }
  function blockName(c) { return lang === 'ja' ? c.name_ja : c.name_en; }

  function producersOf(x, exclude) {
    return data.crafters.filter(function (c) {
      return c.id !== exclude && c.type !== 'Separator' &&
        c.outputs.some(function (o) { return o.kind === x.kind && o.id === x.id; });
    });
  }

  function update() {
    var c = byId[$('mdt-block').value];
    var mode = root.querySelector('input[name="mdt-mode"]:checked').value;
    var val = parseFloat($('mdt-value').value);
    if (!(val > 0)) val = 1;
    var main = c.outputs[0];
    var isSep = c.type === 'Separator';
    // 分離機は1サイクルでどれか1個なので、主出力は「アイテム合計」として扱う
    var mainRate = isSep ? 60 / c.craft_time : perSec(main, c);
    var count = mode === 'target' ? val / mainRate : val;

    $('mdt-target-label').textContent = isSep ? I.targetSep : I.target.replace('{x}', resName(main));
    $('mdt-count').textContent = fmt(count);
    $('mdt-count-ceil').textContent = I.build.replace('{n}', Math.ceil(count - 1e-9));

    var rows = [];
    c.inputs.forEach(function (x) {
      rows.push('<tr><td>' + I.input + '</td><td>' + resName(x) + '</td><td class="tag-mono">' + fmt(perSec(x, c) * count) + '</td></tr>');
    });
    if (isSep) {
      var total = c.outputs.reduce(function (a, o) { return a + o.weight; }, 0);
      c.outputs.forEach(function (o) {
        rows.push('<tr><td>' + I.output + '</td><td>' + resName(o) + '</td><td class="tag-mono">' + fmt(o.weight / total * 60 / c.craft_time * count) + '</td></tr>');
      });
    } else {
      c.outputs.forEach(function (o) {
        rows.push('<tr><td>' + I.output + '</td><td>' + resName(o) + '</td><td class="tag-mono">' + fmt(perSec(o, c) * count) + '</td></tr>');
      });
    }
    if (c.power_per_sec) rows.push('<tr><td>' + I.power + '</td><td>—</td><td class="tag-mono">' + fmt(c.power_per_sec * count) + '</td></tr>');
    if (c.heat) rows.push('<tr><td>' + I.heat + '</td><td>—</td><td class="tag-mono">' + fmt(c.heat * count) + '</td></tr>');
    $('mdt-rates').innerHTML = rows.join('');

    // 入力を自前で作る場合に必要な棟数（1段階だけ）
    var chain = [];
    c.inputs.forEach(function (x) {
      var need = perSec(x, c) * count;
      producersOf(x, c.id).forEach(function (p) {
        var out = p.outputs.filter(function (o) { return o.kind === x.kind && o.id === x.id; })[0];
        chain.push('<li>' + I.chain.replace('{x}', resName(x)).replace('{rate}', fmt(need))
          .replace('{n}', fmt(need / perSec(out, p))).replace('{b}', blockName(p)) + '</li>');
      });
    });
    $('mdt-chain').innerHTML = chain.join('') || '<li>' + I.noChain + '</li>';
    $('mdt-notes').textContent = [
      c.heat ? I.noteHeat : '', c.id === 'silicon-crucible' || c.id === 'cultivator' ? I.noteAttr : '', isSep ? I.noteSep : ''
    ].filter(Boolean).join(' ');
  }

  fetch('/assets/data/mindustry-crafters.json').then(function (r) { return r.json(); }).then(function (d) {
    data = d;
    var sel = $('mdt-block');
    ['serpulo', 'erekir'].forEach(function (planet) {
      var g = document.createElement('optgroup');
      g.label = I.planets[planet];
      d.crafters.filter(function (c) { return c.planet === planet; }).forEach(function (c) {
        byId[c.id] = c;
        var o = document.createElement('option');
        o.value = c.id;
        o.textContent = blockName(c);
        g.appendChild(o);
      });
      sel.appendChild(g);
    });
    var want = (location.hash || '').replace('#c-', '');
    sel.value = byId[want] ? want : 'silicon-smelter';
    root.addEventListener('input', update);
    root.addEventListener('change', update);
    update();
    initDrills();
  });

  // ---- ドリル計算機 ----
  // Drill: 1個あたり ticks（硬度込み）。ブースト時は速度と暖機の両方が上がるので boost_factor = 強度²。
  // BurstDrill: 1回で鉱石タイル数ぶん出す。boost_factor = 強度。どちらも 60/ticks × タイル数。
  function initDrills() {
    var box = $('mdt-drill');
    if (!box || !data.drills) return;
    var dSel = $('mdt-d-block'), oSel = $('mdt-d-ore');
    var drills = {};
    data.drills.forEach(function (d) {
      drills[d.id] = d;
      var o = document.createElement('option');
      o.value = d.id;
      o.textContent = blockName(d) + ' (' + I.planets[d.planet] + ')';
      dSel.appendChild(o);
    });

    function fillOres() {
      var d = drills[dSel.value], keep = oSel.value;
      oSel.innerHTML = '';
      d.ores.forEach(function (x) {
        var o = document.createElement('option');
        o.value = x.id;
        o.textContent = data.resources['item:' + x.id][lang];
        oSel.appendChild(o);
      });
      if (d.ores.some(function (x) { return x.id === keep; })) oSel.value = keep;
      $('mdt-d-tiles').max = d.size * d.size;
      $('mdt-d-tiles').value = Math.min(parseInt($('mdt-d-tiles').value, 10) || d.size * d.size, d.size * d.size);
    }

    function calc() {
      var d = drills[dSel.value];
      var ore = d.ores.filter(function (x) { return x.id === oSel.value; })[0];
      var tiles = Math.max(1, Math.min(d.size * d.size, parseInt($('mdt-d-tiles').value, 10) || 1));
      var n = Math.max(1, parseInt($('mdt-d-count').value, 10) || 1);
      var boosted = $('mdt-d-boost').checked && d.booster;
      var per = 60 / ore.ticks * tiles * (boosted ? d.boost_factor : 1);
      $('mdt-d-rate').textContent = fmt(per * n);
      $('mdt-d-unit').textContent = I.dUnit.replace('{x}', data.resources['item:' + ore.id][lang]);
      var lines = [I.dEach.replace('{r}', fmt(per)).replace('{t}', fmt(ore.ticks / 60 / tiles * (d.type === 'BurstDrill' ? tiles : 1)))];
      if (d.power_per_sec) lines.push(I.power + ': ' + fmt(d.power_per_sec * n) + ' /s');
      d.liquids.filter(function (l) { return !d.booster || l.id !== d.booster.id; }).forEach(function (l) {
        lines.push(data.resources['liquid:' + l.id][lang] + ': ' + fmt(l.per_sec * n) + ' /s');
      });
      if (boosted) lines.push(I.dBoost.replace('{x}', data.resources['liquid:' + d.booster.id][lang])
        .replace('{r}', fmt(d.booster.per_sec * n)).replace('{f}', fmt(d.boost_factor)));
      $('mdt-d-detail').innerHTML = lines.map(function (l) { return '<li>' + l + '</li>'; }).join('');
    }

    dSel.addEventListener('change', function () { fillOres(); calc(); });
    box.addEventListener('input', calc);
    box.addEventListener('change', calc);
    fillOres();
    calc();
  }
})();
