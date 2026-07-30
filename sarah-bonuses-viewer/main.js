import Papa from 'papaparse';

const SHEETS = {
  raw: '/sarah-bonuses.csv',
  cleaned: '/sarah-bonuses-cleaned.csv'
};

const HIDDEN_COLS_CLEANED = new Set(['rollover','claimconfig','claimcondition','bonus','bonusrandom','maxtopup','referlink','is_new']);
const CLEANED_COL_ORDER = ['url','mname','name','amount','minwithdraw','maxwithdraw','ratio','perceived_value','reset','mintopup'];
const HEADER_RENAME = { 'mintopup': 'Min $ In', 'perceived_value': 'Value' };

let currentSheet = 'cleaned';
let rawData = null;
let cleanedData = null;
let sortStates = {};
let nameExpandedRow = null;
let rawMnameMap = {};

const tabs = document.querySelectorAll('.tab');
const thead = document.getElementById('tableHead');
const tbody = document.getElementById('tableBody');
const sheetInfo = document.getElementById('sheetInfo');

tabs.forEach(tab => {
  tab.addEventListener('click', () => {
    tabs.forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    currentSheet = tab.dataset.sheet;
    sortStates = {};
    nameExpandedRow = null;
    renderTable();
  });
});

document.addEventListener('click', () => {
  if (nameExpandedRow !== null) {
    nameExpandedRow = null;
    renderTable();
  }
});

function truncate(str, len = 60) {
  if (!str) return '';
  const s = String(str);
  return s.length > len ? s.slice(0, len) + '…' : s;
}

function stripUrl(url) {
  return url.replace(/^https?:\/\//, '').replace(/\/.*$/, '');
}

function isEmptyRow(row) {
  return row.every(cell => !cell || String(cell).trim() === '');
}

function getDisplayText(row, colIdx, headers, sheet) {
  const h = headers[colIdx];
  let val = row[colIdx] ?? '';
  if (h === 'url') {
    if (sheet === 'raw') return stripUrl(val);
    return rawMnameMap[val] || stripUrl(val);
  }
  return val;
}

function numVal(v) {
  const n = parseFloat(v);
  return isNaN(n) ? null : n;
}

function compareRows(a, b, colIdx, dir, headers, sheet) {
  const h = headers[colIdx];
  const rawA = a[colIdx] ?? '';
  const rawB = b[colIdx] ?? '';

  // Custom: maxwithdraw — 0/empty at top, then descending
  if (h === 'maxwithdraw' && dir === 'desc-zero-top') {
    const na = numVal(rawA);
    const nb = numVal(rawB);
    const aEmpty = na === null || na === 0;
    const bEmpty = nb === null || nb === 0;
    if (aEmpty && !bEmpty) return -1;
    if (!aEmpty && bEmpty) return 1;
    if (aEmpty && bEmpty) return 0;
    return nb - na;
  }

  // Name/url: sort by display text
  if (h === 'name' || h === 'url') {
    const da = getDisplayText(a, colIdx, headers, sheet).toLowerCase();
    const db = getDisplayText(b, colIdx, headers, sheet).toLowerCase();
    if (dir === 'asc') return da.localeCompare(db);
    return db.localeCompare(da);
  }

  // Numeric columns
  const na = numVal(rawA);
  const nb = numVal(rawB);
  if (na !== null && nb !== null) {
    return dir === 'asc' ? na - nb : nb - na;
  }
  if (na !== null) return -1;
  if (nb !== null) return 1;

  // String fallback
  const sa = String(rawA).toLowerCase();
  const sb = String(rawB).toLowerCase();
  if (dir === 'asc') return sa.localeCompare(sb);
  return sb.localeCompare(sa);
}

function renderTable() {
  const data = currentSheet === 'raw' ? rawData : cleanedData;
  if (!data) return;

  let [headers, ...rows] = data;
  rows = rows.filter(r => !isEmptyRow(r));

  // Determine visible columns
  const hidden = currentSheet === 'cleaned' ? HIDDEN_COLS_CLEANED : new Set();
  const visIdxs = headers.map((h, i) => hidden.has(h) ? -1 : i).filter(i => i !== -1);
  const visHeaders = visIdxs.map(i => headers[i]);

  const urlIdx = headers.indexOf('url');
  const nameIdx = headers.indexOf('name');
  const maxwIdx = headers.indexOf('maxwithdraw');

  // Apply sorts
  for (const [colIdx, dir] of Object.entries(sortStates)) {
    if (dir === 'default') continue;
    const idx = parseInt(colIdx);
    rows.sort((a, b) => compareRows(a, b, idx, dir, headers, currentSheet));
  }

  sheetInfo.textContent = `${visHeaders.length} columns · ${rows.length} rows`;

  thead.innerHTML = '';
  const tr = document.createElement('tr');
  visIdxs.forEach((origIdx) => {
    const h = headers[origIdx];
    const th = document.createElement('th');
    th.textContent = HEADER_RENAME[h] || h;
    th.dataset.col = origIdx;

    const dir = sortStates[origIdx];
    const arrowSpan = document.createElement('span');
    arrowSpan.className = 'sort-arrow';
    if (dir && dir !== 'default') {
      const label = dir === 'desc-zero-top' ? ' ▼' : dir === 'asc' ? ' ▲' : ' ▼';
      th.classList.add('sorted', dir);
      arrowSpan.textContent = label;
    } else {
      arrowSpan.textContent = '  ';
    }
    th.appendChild(arrowSpan);

    th.addEventListener('click', (e) => {
      e.stopPropagation();
      const current = sortStates[origIdx] || 'default';
      for (const key of Object.keys(sortStates)) {
        if (key !== String(origIdx)) sortStates[key] = 'default';
      }
      if (current === 'default') sortStates[origIdx] = 'desc';
      else if (current === 'desc-zero-top') sortStates[origIdx] = 'desc';
      else if (current === 'desc') sortStates[origIdx] = 'asc';
      else sortStates[origIdx] = 'default';
      renderTable();
    });

    // Column width classes
    const seq = visIdxs.indexOf(origIdx);
    if (h === 'amount') th.classList.add('col-narrow');
    else if (['minwithdraw','maxwithdraw','rollover','ratio','perceived_value'].includes(h)) th.classList.add('col-mid');

    tr.appendChild(th);
  });
  thead.appendChild(tr);

  tbody.innerHTML = '';
  rows.forEach((row, ri) => {
    const tr = document.createElement('tr');
    visIdxs.forEach((origIdx, seq) => {
      const h = headers[origIdx];
      const td = document.createElement('td');
      let val = row[origIdx] ?? '';

      if (origIdx === urlIdx) {
        const display = getDisplayText(row, origIdx, headers, currentSheet);
        if (val) {
          const a = document.createElement('a');
          a.href = val;
          a.textContent = display;
          a.target = '_blank';
          a.rel = 'noopener';
          td.appendChild(a);
        } else {
          td.textContent = display;
        }
        td.classList.add('col-url');
        if (currentSheet === 'cleaned') td.classList.add('cleaned-width');
      } else {
        td.textContent = truncate(val);
      }

      if (['amount','minwithdraw','maxwithdraw','rollover','ratio','perceived_value'].includes(h)) {
        td.style.textAlign = 'right';
        const n = parseFloat(val);
        if (!isNaN(n)) td.textContent = h === 'amount' || h === 'ratio' || h === 'perceived_value' ? n.toFixed(2) : n.toFixed(0);
      }

      // Column width classes for tds
      if (h === 'amount') td.classList.add('col-narrow');
      else if (['minwithdraw','maxwithdraw','rollover','ratio','perceived_value'].includes(h)) td.classList.add('col-mid');

      if (origIdx === nameIdx) {
        td.classList.add('col-name');
        if (nameExpandedRow === ri) td.classList.add('expanded');
        td.addEventListener('click', (e) => {
          e.stopPropagation();
          nameExpandedRow = (nameExpandedRow === ri) ? null : ri;
          renderTable();
        });
        td.style.cursor = 'pointer';
      }

      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
}

function buildRawMnameMap(headers, rows) {
  const urlIdx = headers.indexOf('url');
  const mnameIdx = headers.indexOf('mname');
  const map = {};
  rows.forEach(row => {
    if (urlIdx !== -1 && mnameIdx !== -1 && row[urlIdx]) {
      map[row[urlIdx]] = row[mnameIdx];
    }
  });
  return map;
}

async function loadSheet(path) {
  const res = await fetch(path);
  const csv = await res.text();
  return new Promise(resolve => {
    Papa.parse(csv, { complete: results => resolve(results.data) });
  });
}

async function init() {
  const rawRaw = await loadSheet(SHEETS.raw);
  const [rh, ...rr] = rawRaw;
  const rawRows = rr.filter(r => !isEmptyRow(r));
  rawData = [rh, ...rawRows];
  rawMnameMap = buildRawMnameMap(rh, rawRows);

  const cleanedRaw = await loadSheet(SHEETS.cleaned);
  const [ch, ...cr] = cleanedRaw;
  cleanedData = [ch, ...cr.filter(r => !isEmptyRow(r))];

  // Default sort: maxwithdraw descending, 0s/empty at top
  const mwIdx = ch.indexOf('maxwithdraw');
  if (mwIdx !== -1) sortStates[mwIdx] = 'desc-zero-top';

  renderTable();
}

document.addEventListener('DOMContentLoaded', init);
