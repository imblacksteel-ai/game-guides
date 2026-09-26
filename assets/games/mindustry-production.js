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
  });
})();
