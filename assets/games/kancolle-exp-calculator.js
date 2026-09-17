(function () {
  var T = window.EXP_I18N;
  // exp per battle = base × rank × 1.5 (flagship) × 2 (MVP). E rank has no MVP.
  // Multipliers are kept as integers (rank ×10, flagship as 3/2): in floating point
  // 1.2 × 1.5 × 2 is 3.5999…, which would floor 100 base EXP to 359 instead of 360.
  var RANK10 = { S: 12, A: 10, B: 10, C: 8, D: 7, E: 5 };

  var $ = function (id) { return document.getElementById(id); };
  var total = null, maxLevel = 188, marriageLevel = 100;
  var ships = [], F = {}, byLabel = {}, byJp = {};

  function num(id) {
    var v = parseInt($(id).value, 10);
    return isNaN(v) ? null : v;
  }
  function fmt(n) { return n.toLocaleString(); }
  function fill(s, map) {
    return s.replace(/\{(\w+)\}/g, function (_, k) { return map[k]; });
  }
  function clampLevel(v) { return Math.max(1, Math.min(maxLevel, v)); }

  function expPerBattle(base, rank, flag, mvp) {
    var numerator = base * RANK10[rank] * (flag ? 3 : 2) * (mvp && rank !== 'E' ? 2 : 1);
    return Math.floor(numerator / 20);
  }

  function neededExp(cur, target, toNext) {
    if (target <= cur) return 0;
    if (toNext !== null && toNext > 0 && cur < maxLevel) {
      return toNext + (total[target] - total[cur + 1]);
    }
    return total[target] - total[cur];
  }

  function recalc() {
    if (!total) return;
    var cur = num('exp-current'), target = num('exp-target');
    var base = num('exp-base'), perSortie = num('exp-battles') || 1;
    var rank = $('exp-rank').value, flag = $('exp-flag').checked, mvp = $('exp-mvp').checked;
    var note = $('exp-note');
    note.textContent = '';

    if (cur === null || target === null) return;
    cur = clampLevel(cur); target = clampLevel(target);

    var needed = neededExp(cur, target, num('exp-to-next'));
    $('r-needed').textContent = fmt(needed);

    var notes = [];
    if (target <= cur) notes.push(T.targetNotAbove);
    if (cur < marriageLevel && target >= marriageLevel) notes.push(T.marriage);
    note.textContent = notes.join(' ');

    var per = base ? expPerBattle(base, rank, flag, mvp) : 0;
    $('r-per-battle').textContent = per ? fmt(per) : '—';
    if (!per || !needed) {
      $('r-battles').textContent = needed ? '—' : '0';
      $('r-sorties').textContent = needed ? '—' : '0';
    } else {
      var battles = Math.ceil(needed / per);
      $('r-battles').textContent = fmt(battles);
      $('r-sorties').textContent = fmt(Math.ceil(battles / perSortie));
    }

    var body = $('exp-scenarios');
    body.textContent = '';
    [['flagMvp', true, true], ['flagOnly', true, false], ['mvpOnly', false, true], ['neither', false, false]]
      .forEach(function (sc) {
        var p = base ? expPerBattle(base, rank, sc[1], sc[2]) : 0;
        var tr = document.createElement('tr');
        [T.scenarios[sc[0]], p ? fmt(p) : '—',
         p && needed ? fmt(Math.ceil(Math.ceil(needed / p) / perSortie)) : (needed ? '—' : '0')]
          .forEach(function (text, i) {
            var td = document.createElement('td');
            if (i > 0) td.className = 'tag-mono';
            td.textContent = text;
            tr.appendChild(td);
          });
        body.appendChild(tr);
      });
  }

  function label(s) { return s[F.en] + ' (' + s[F.jp] + ')'; }

  function findShip(q) {
    q = q.trim();
    if (!q) return null;
    if (byLabel[q]) return byLabel[q];
    var lower = q.toLowerCase();
    for (var i = 0; i < ships.length; i++) {
      if (ships[i][F.jp] === q || ships[i][F.en].toLowerCase() === lower) return ships[i];
    }
    return null;
  }

  function onShip() {
    var info = $('exp-ship-info');
    var s = findShip($('exp-ship').value);
    if (!s) { info.textContent = ''; return; }
    var lv = s[F.remodel_lv];
    if (!lv) {
      info.textContent = T.noRemodel;
      return;
    }
    var to = byJp[s[F.remodel_to]];
    info.textContent = fill(T.nextRemodel, { name: to ? label(to) : s[F.remodel_to], lv: lv });
    var cur = num('exp-current') || 1;
    if (lv > cur) {
      $('exp-target').value = lv;
      recalc();
    }
  }

  ['exp-current', 'exp-to-next', 'exp-target', 'exp-base', 'exp-battles'].forEach(function (id) {
    $(id).addEventListener('input', recalc);
  });
  ['exp-rank', 'exp-flag', 'exp-mvp'].forEach(function (id) {
    $(id).addEventListener('change', recalc);
  });
  $('exp-ship').addEventListener('change', onShip);
  $('exp-ship').addEventListener('input', onShip);

  Promise.all([
    fetch('/assets/data/kancolle-exp.json').then(function (r) { if (!r.ok) throw r.status; return r.json(); }),
    fetch('/assets/data/kancolle-ships.json').then(function (r) { if (!r.ok) throw r.status; return r.json(); })
  ]).then(function (res) {
    total = res[0].total;
    maxLevel = res[0].max_level;
    marriageLevel = res[0].marriage_level;
    ['exp-current', 'exp-target'].forEach(function (id) { $(id).max = maxLevel; });
    $('exp-max-level').textContent = maxLevel;

    res[1].fields.forEach(function (f, i) { F[f] = i; });
    ships = res[1].ships;
    var list = $('exp-ship-list'), frag = document.createDocumentFragment();
    ships.forEach(function (s) {
      byLabel[label(s)] = s;
      byJp[s[F.jp]] = s;
      var o = document.createElement('option');
      o.value = label(s);
      frag.appendChild(o);
    });
    list.appendChild(frag);
    recalc();
  }).catch(function () {
    $('exp-note').textContent = T.loadError;
  });
})();
