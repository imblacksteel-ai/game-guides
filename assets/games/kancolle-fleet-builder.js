(function () {
  var T = window.FLEET_I18N;
  var F = { jp: 0, en: 1, type: 2, hp: 3, fire: 4, torp: 5, aa: 6, armor: 7, asw: 8, los: 9, luck: 10, slots: 11, speed: 12 };
  var TABLE_LIMIT = 60;
  var DEFAULT_FLEET = ['雪風改', '綾波改', '夕立改', '時雨改', '川内改', '那珂改'];

  var ships = [];
  var byLabel = {};

  var rowsEl = document.getElementById('fleet-rows');
  var pickerInput = document.getElementById('ship-picker');
  var datalist = document.getElementById('ship-list');
  var searchInput = document.getElementById('ship-search');
  var typeSelect = document.getElementById('ship-type-filter');
  var tbody = document.getElementById('ship-table-body');
  var countEl = document.getElementById('ship-count');

  function label(s) { return s[F.en] + ' (' + s[F.jp] + ')'; }

  function el(tag, attrs, text) {
    var e = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    if (text != null) e.textContent = text;
    return e;
  }

  // ---------- Ship lookup table ----------
  function renderTable() {
    var q = searchInput.value.trim().toLowerCase();
    var type = typeSelect.value;
    var matches = ships.filter(function (s) {
      if (type && s[F.type] !== type) return false;
      if (!q) return true;
      return s[F.en].toLowerCase().indexOf(q) !== -1 || s[F.jp].indexOf(q) !== -1;
    });

    tbody.textContent = '';
    matches.slice(0, TABLE_LIMIT).forEach(function (s) {
      var tr = el('tr');
      var nameTd = el('td');
      nameTd.appendChild(document.createTextNode(s[F.en]));
      nameTd.appendChild(el('br'));
      nameTd.appendChild(el('span', { 'class': 'romaji' }, s[F.jp]));
      tr.appendChild(nameTd);
      [F.type, F.hp, F.fire, F.torp, F.aa, F.armor, F.asw, F.los, F.luck].forEach(function (i) {
        tr.appendChild(el('td', { 'class': 'tag-mono' }, s[i]));
      });
      tr.appendChild(el('td', null, s[F.speed] ? T.high : T.low));
      tr.appendChild(el('td', { 'class': 'tag-mono' }, s[F.slots]));
      tbody.appendChild(tr);
    });

    countEl.textContent = matches.length
      ? T.showing.replace('{shown}', Math.min(matches.length, TABLE_LIMIT)).replace('{total}', matches.length)
      : T.noResults;
  }

  // ---------- Fleet builder ----------
  function speedSelect(speedIndex) {
    var sel = el('select', { 'class': 'r-speed' });
    [T.low, T.high].forEach(function (text, i) {
      var opt = el('option', { value: i }, text);
      if (i === speedIndex) opt.selected = true;
      sel.appendChild(opt);
    });
    return sel;
  }

  function input(cls, type, value) {
    var i = el('input', { type: type, 'class': cls });
    if (type === 'number') i.min = 0;
    i.value = value;
    return i;
  }

  function addRow(name, type, fire, aa, asw, los, speedIndex) {
    var row = el('div', { 'class': 'fleet-calc-row' });
    row.appendChild(input('r-name', 'text', name));
    row.appendChild(input('r-type', 'text', type));
    row.appendChild(input('r-fire', 'number', fire));
    row.appendChild(input('r-aa', 'number', aa));
    row.appendChild(input('r-asw', 'number', asw));
    row.appendChild(input('r-los', 'number', los));
    row.appendChild(speedSelect(speedIndex));
    var remove = el('button', { type: 'button', 'class': 'r-remove', 'aria-label': T.remove }, '×');
    row.appendChild(remove);

    rowsEl.appendChild(row);
    remove.addEventListener('click', function () { row.remove(); recalc(); });
    row.querySelectorAll('input, select').forEach(function (inp) {
      inp.addEventListener('input', recalc);
      inp.addEventListener('change', recalc);
    });
    recalc();
  }

  function addShip(s) {
    addRow(label(s), s[F.type], s[F.fire], s[F.aa], s[F.asw], s[F.los], s[F.speed]);
  }

  function recalc() {
    var rows = rowsEl.querySelectorAll('.fleet-calc-row');
    var fire = 0, aa = 0, asw = 0, los = 0, minSpeed = null, types = {};
    rows.forEach(function (row) {
      fire += parseFloat(row.querySelector('.r-fire').value) || 0;
      aa += parseFloat(row.querySelector('.r-aa').value) || 0;
      asw += parseFloat(row.querySelector('.r-asw').value) || 0;
      los += parseFloat(row.querySelector('.r-los').value) || 0;
      var sp = parseInt(row.querySelector('.r-speed').value, 10);
      if (minSpeed === null || sp < minSpeed) minSpeed = sp;
      var t = row.querySelector('.r-type').value.trim() || '?';
      types[t] = (types[t] || 0) + 1;
    });
    document.getElementById('f-count').textContent = rows.length;
    document.getElementById('f-fire').textContent = fire;
    document.getElementById('f-aa').textContent = aa;
    document.getElementById('f-asw').textContent = asw;
    document.getElementById('f-los').textContent = los;
    document.getElementById('f-speed').textContent = minSpeed === null ? '—' : [T.low, T.high][minSpeed];
    var typeStr = Object.keys(types).map(function (t) { return t + '×' + types[t]; }).join(', ');
    document.getElementById('f-types').textContent = typeStr || '—';
  }

  function findShip(query) {
    var q = query.trim();
    if (!q) return null;
    if (byLabel[q]) return byLabel[q];
    var lower = q.toLowerCase();
    for (var i = 0; i < ships.length; i++) {
      if (ships[i][F.jp] === q || ships[i][F.en].toLowerCase() === lower) return ships[i];
    }
    return null;
  }

  function init(data) {
    ships = data.ships;

    var frag = document.createDocumentFragment();
    ships.forEach(function (s) {
      byLabel[label(s)] = s;
      frag.appendChild(el('option', { value: label(s) }));
    });
    datalist.appendChild(frag);

    var typeList = [];
    ships.forEach(function (s) { if (typeList.indexOf(s[F.type]) === -1) typeList.push(s[F.type]); });
    typeList.sort().forEach(function (t) { typeSelect.appendChild(el('option', { value: t }, t)); });

    searchInput.addEventListener('input', renderTable);
    typeSelect.addEventListener('change', renderTable);
    renderTable();

    document.getElementById('picker-add').addEventListener('click', function () {
      var s = findShip(pickerInput.value);
      if (!s) { pickerInput.setCustomValidity(T.notFound); pickerInput.reportValidity(); return; }
      pickerInput.setCustomValidity('');
      addShip(s);
      pickerInput.value = '';
    });
    pickerInput.addEventListener('input', function () { pickerInput.setCustomValidity(''); });

    DEFAULT_FLEET.forEach(function (jp) {
      var s = ships.filter(function (x) { return x[F.jp] === jp; })[0];
      if (s) addShip(s);
    });
  }

  document.getElementById('fleet-add-row').addEventListener('click', function () {
    addRow(T.newShip, 'DD', 0, 0, 0, 0, 1);
  });

  fetch('/assets/data/kancolle-ships.json')
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(init)
    .catch(function () { countEl.textContent = T.loadError; recalc(); });
})();
