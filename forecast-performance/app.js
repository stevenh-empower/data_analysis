// Forecast Performance Dashboard
const GREEN = '#52A748';
const GREEN_DARK = '#1F381B';
const GREEN_FADED = '#d0e6cf';
const RED = '#BE123C';
const ACCENT = '#F15F2F';
const SECONDARY = '#0E29F4';

const fmt = {
  int: n => (n == null ? '—' : Number(n).toLocaleString('en-US')),
  num1: n => (n == null ? '—' : Number(n).toFixed(2)),
  num2: n => (n == null ? '—' : Number(n).toFixed(3)),
  pct: n => (n == null ? '—' : (Number(n) * 100).toFixed(1) + '%'),
  pctSigned: n => {
    if (n == null) return '—';
    const v = Number(n) * 100;
    const sign = v > 0 ? '+' : '';
    return sign + v.toFixed(0) + '%';
  },
  signedInt: n => {
    if (n == null) return '—';
    const v = Number(n);
    return (v > 0 ? '+' : '') + v.toLocaleString('en-US');
  },
};

const METRIC_DESCRIPTIONS = {
  mae: 'Mean Absolute Error — average miss in cases',
  rmse: 'Root Mean Squared Error — penalises large misses',
  mape: 'Mean Absolute Percent Error — % miss per pair',
  r2:   'R² — explained variance (higher = better)',
  within2: '% of forecast-days within 2 cases of actual',
};

let DATA = null;

async function init() {
  const res = await fetch('data.json');
  DATA = await res.json();

  buildSidebarNav();
  buildHeadlineCards();
  buildOverallTable();
  buildPerCustomerTable();
  buildFullMetricsTable();
  buildCharts();
  setupNavScroll();
}

function buildSidebarNav() {
  const el = document.getElementById('cust-nav');
  el.innerHTML = DATA.customers
    .map(c => `<a class="nav-item" href="customers/${c.slug}/">${c.name}</a>`)
    .join('');
}

function buildHeadlineCards() {
  const o = DATA.overall;
  const cards = [
    { number: fmt.int(DATA.customers.length), label: 'Grocers' },
    { number: fmt.int(o.unique_stores), label: 'Stores' },
    { number: fmt.int(o.unique_products), label: 'Unique products' },
    { number: fmt.int(o.unique_pairs), label: 'Pairs forecasted (V2)', highlight: true },
    { number: '+' + fmt.int(o.legacy_v2.delta_pairs), label: 'More pairs vs legacy', accent: true },
    { number: fmt.pct(o.metrics.mae.ai_win_rate), label: 'AI wins (MAE)' },
    { number: fmt.pct(o.metrics.rmse.ai_win_rate), label: 'AI wins (RMSE)' },
    { number: fmt.pct(o.metrics.r2.ai_win_rate), label: 'AI wins (R²)' },
  ];
  document.getElementById('headline-cards').innerHTML =
    cards.map(c => `
      <div class="card ${c.highlight ? 'highlight' : ''} ${c.accent ? 'accent' : ''}">
        <div class="number">${c.number}</div>
        <div class="label">${c.label}</div>
      </div>`).join('');
}

function buildOverallTable() {
  const o = DATA.overall.metrics;
  const order = ['mae', 'rmse', 'r2', 'mape', 'within2'];
  const labels = { mae: 'MAE', rmse: 'RMSE', r2: 'R²', mape: 'MAPE', within2: 'Within-2 cases' };
  const rows = order.map(k => {
    const m = o[k];
    const win = Number(m.ai_win_rate);
    // approximate ties: within2 has many ties (median 1 for both)
    const aiPct = win;
    const losePct = 1 - win;
    return `
      <tr>
        <td><strong>${labels[k]}</strong></td>
        <td style="color:var(--muted);font-size:12.5px">${METRIC_DESCRIPTIONS[k]}</td>
        <td>
          <div class="bar-h">
            <div class="seg seg-ai" style="width:${(aiPct*100).toFixed(2)}%">${(aiPct*100).toFixed(0)}%</div>
            <div class="seg seg-legacy" style="width:${(losePct*100).toFixed(2)}%">${losePct > 0.08 ? (losePct*100).toFixed(0) + '%' : ''}</div>
          </div>
        </td>
        <td class="num">${fmt.int(m.n)}</td>
        <td class="num"><span class="badge ${aiPct >= 0.5 ? 'badge-win' : 'badge-lose'}">${fmt.pct(aiPct)}</span></td>
      </tr>`;
  }).join('');
  document.querySelector('#overall-table tbody').innerHTML = rows;
}

function buildPerCustomerTable() {
  const rows = DATA.customers.map(c => `
    <tr>
      <td><strong>${c.name}</strong></td>
      <td class="num">${fmt.int(c.unique_stores)}</td>
      <td class="num">${fmt.int(c.unique_products)}</td>
      <td class="num">${fmt.int(c.unique_pairs)}</td>
      <td class="num">${fmt.int(c.legacy_v2.legacy_pairs)}</td>
      <td class="num"><span class="badge badge-info">+${fmt.int(c.legacy_v2.delta_pairs)}</span></td>
      <td class="num"><span class="badge ${c.metrics.mae.ai_win_rate >= 0.5 ? 'badge-win' : 'badge-lose'}">${fmt.pct(c.metrics.mae.ai_win_rate)}</span></td>
      <td class="num"><span class="badge ${c.metrics.rmse.ai_win_rate >= 0.5 ? 'badge-win' : 'badge-lose'}">${fmt.pct(c.metrics.rmse.ai_win_rate)}</span></td>
      <td><a href="customers/${c.slug}/">View →</a></td>
    </tr>`).join('');
  document.querySelector('#per-cust-table tbody').innerHTML = rows;
}

function buildFullMetricsTable() {
  const rows = DATA.customers.map(c => {
    const m = c.metrics;
    return `
      <tr>
        <td><strong>${c.name}</strong></td>
        <td class="num">${fmt.num1(m.mae.ai_mean)}</td>
        <td class="num">${fmt.num1(m.mae.sales_mean)}</td>
        <td class="num">${fmt.num1(m.rmse.ai_mean)}</td>
        <td class="num">${fmt.num1(m.rmse.sales_mean)}</td>
        <td class="num">${fmt.pct(m.mape.ai_mean)}</td>
        <td class="num">${fmt.pct(m.mape.sales_mean)}</td>
        <td class="num">${fmt.num2(m.r2.ai_mean)}</td>
        <td class="num">${fmt.num2(m.r2.sales_mean)}</td>
        <td class="num">${fmt.pct(m.within2.ai_mean)}</td>
        <td class="num">${fmt.pct(m.within2.sales_mean)}</td>
      </tr>`;
  }).join('');
  document.querySelector('#full-metrics tbody').innerHTML = rows;
}

function buildCharts() {
  Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", sans-serif';
  Chart.defaults.color = '#1F381B';

  const o = DATA.overall;

  // Coverage bar (legacy vs V2 pairs - overall)
  new Chart(document.getElementById('coverageBar'), {
    type: 'bar',
    data: {
      labels: ['Legacy (forecasted, 60d)', 'V2 (currently eligible)'],
      datasets: [{
        label: 'Pairs',
        data: [o.legacy_v2.legacy_pairs, o.legacy_v2.v2_pairs],
        backgroundColor: [RED, GREEN],
        borderRadius: 6,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => `${fmt.int(ctx.parsed.x)} pairs` } },
      },
      scales: { x: { ticks: { callback: v => fmt.int(v) } } },
    },
  });

  // Case vs Unit pairs total
  new Chart(document.getElementById('caseUnitBar'), {
    type: 'bar',
    data: {
      labels: ['Case pairs', 'Unit pairs'],
      datasets: [
        { label: 'Legacy', data: [28140, 19], backgroundColor: RED, borderRadius: 6 },
        { label: 'V2',     data: [60093, 21384], backgroundColor: GREEN, borderRadius: 6 },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${fmt.int(ctx.parsed.y)}` } } },
      scales: { y: { ticks: { callback: v => fmt.int(v) } } },
    },
  });

  // Per-customer charts
  const labels = DATA.customers.map(c => c.name);
  const maeWin = DATA.customers.map(c => +(c.metrics.mae.ai_win_rate * 100).toFixed(1));
  const rmseWin = DATA.customers.map(c => +(c.metrics.rmse.ai_win_rate * 100).toFixed(1));
  const r2Win = DATA.customers.map(c => +(c.metrics.r2.ai_win_rate * 100).toFixed(1));
  const mapeWin = DATA.customers.map(c => +(c.metrics.mape.ai_win_rate * 100).toFixed(1));

  new Chart(document.getElementById('winRateBar'), {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'MAE',  data: maeWin,  backgroundColor: GREEN, borderRadius: 4 },
        { label: 'RMSE', data: rmseWin, backgroundColor: GREEN_DARK, borderRadius: 4 },
        { label: 'R²',   data: r2Win,   backgroundColor: SECONDARY, borderRadius: 4 },
        { label: 'MAPE', data: mapeWin, backgroundColor: ACCENT, borderRadius: 4 },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y}%` } } },
      scales: {
        y: { min: 0, max: 100, ticks: { callback: v => v + '%' }, title: { display: true, text: 'AI win rate' } },
        x: { ticks: { autoSkip: false, maxRotation: 40, minRotation: 30 } },
      },
    },
  });

  new Chart(document.getElementById('maeBar'), {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'AI MAE',     data: DATA.customers.map(c => +c.metrics.mae.ai_mean.toFixed(2)),     backgroundColor: GREEN, borderRadius: 4 },
        { label: 'Legacy MAE', data: DATA.customers.map(c => +c.metrics.mae.sales_mean.toFixed(2)), backgroundColor: RED, borderRadius: 4 },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(2)} cases` } } },
      scales: { x: { ticks: { autoSkip: false, maxRotation: 40, minRotation: 30 } } },
    },
  });

  new Chart(document.getElementById('coverageCust'), {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'Legacy pairs', data: DATA.customers.map(c => c.legacy_v2.legacy_pairs), backgroundColor: RED, borderRadius: 4 },
        { label: 'V2 pairs',     data: DATA.customers.map(c => c.legacy_v2.v2_pairs),     backgroundColor: GREEN, borderRadius: 4 },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${fmt.int(ctx.parsed.y)}` } } },
      scales: {
        y: { ticks: { callback: v => fmt.int(v) } },
        x: { ticks: { autoSkip: false, maxRotation: 40, minRotation: 30 } },
      },
    },
  });

  new Chart(document.getElementById('mapeBar'), {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'AI MAPE',     data: DATA.customers.map(c => +(c.metrics.mape.ai_mean * 100).toFixed(1)),     backgroundColor: GREEN, borderRadius: 4 },
        { label: 'Legacy MAPE', data: DATA.customers.map(c => +(c.metrics.mape.sales_mean * 100).toFixed(1)), backgroundColor: RED, borderRadius: 4 },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(1)}%` } } },
      scales: {
        y: { ticks: { callback: v => v + '%' } },
        x: { ticks: { autoSkip: false, maxRotation: 40, minRotation: 30 } },
      },
    },
  });
}

function setupNavScroll() {
  const links = document.querySelectorAll('aside .nav-item[href^="#"]');
  const sections = [...links].map(a => document.querySelector(a.getAttribute('href'))).filter(Boolean);
  function onScroll() {
    let active = sections[0];
    for (const s of sections) {
      if (s.getBoundingClientRect().top < 120) active = s;
    }
    links.forEach(a => a.classList.toggle('active', a.getAttribute('href') === '#' + active.id));
  }
  window.addEventListener('scroll', onScroll, { passive: true });
}

init();
