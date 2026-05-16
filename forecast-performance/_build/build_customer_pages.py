"""Generate one customer-facing impact page per customer."""
import json
import pathlib
import html

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / 'data.json').read_text())

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{name} · Forecast Accuracy Update</title>
  <link rel="icon" type="image/png" href="../../assets/favicon.png">
  <link rel="stylesheet" href="../../styles.css">
</head>
<body class="customer-page">
<div class="cust-wrap">

  <div class="cust-header">
    <div class="logo">
      <img src="../../assets/logo-wide-green.svg" alt="EmpowerFresh">
    </div>
    <div class="who">
      <div class="name">{name}</div>
      <div class="what">Produce forecasting update · May 2026</div>
    </div>
  </div>

  <section class="cust-hero">
    <h1>Smarter produce forecasts, more of your shelves covered.</h1>
    <p>Our new AI-driven demand engine is now forecasting your produce items more accurately than ever — and it's looking at far more of your assortment than the previous system ever did. Here's what that means for {name_short}.</p>
  </section>

  <div class="cust-cards">
    <div class="card highlight">
      <div class="number">{v2_pairs_fmt}</div>
      <div class="label">Items × stores forecasted</div>
      <div class="sub">vs {legacy_pairs_fmt} previously ({pairs_growth_pct} more)</div>
    </div>
    <div class="card">
      <div class="number">{products_fmt}</div>
      <div class="label">Unique produce items</div>
      <div class="sub">across {stores} {store_label}</div>
    </div>
    <div class="card">
      <div class="number">{ai_win_mae}</div>
      <div class="label">Of forecasts now more accurate</div>
      <div class="sub">vs the previous method (MAE)</div>
    </div>
    <div class="card">
      <div class="number">{error_drop_pct}</div>
      <div class="label">Average forecast miss reduced</div>
      <div class="sub">cases per item, per day</div>
    </div>
  </div>

  <div class="impact">
    <h2>What's improving for {name_short}</h2>

    <div class="impact-stat">
      <div class="big">{ai_win_mae}</div>
      <div class="label">of items are forecast more accurately than they were under the legacy method — meaning closer-to-real demand, less guesswork at the store level.</div>
    </div>

    <div class="impact-stat">
      <div class="big">+{delta_pairs_fmt}</div>
      <div class="label">additional item × store combinations now have a daily forecast — including {unit_pairs_v2_fmt} unit-sold items that the previous system never forecasted at all.</div>
    </div>

    <div class="impact-stat">
      <div class="big">{within2}</div>
      <div class="label">of daily forecasts land within 2 cases of actual sales — the practical accuracy threshold for produce ordering.</div>
    </div>

    <div class="impact-stat">
      <div class="big">{products_growth_pct}</div>
      <div class="label">growth in unique produce items covered vs the legacy system ({legacy_products_fmt} → {v2_products_fmt}).</div>
    </div>
  </div>

  <div class="impact">
    <h2>What we're doing next</h2>
    <div class="steps">
      <div class="step">
        <div class="step-num">1</div>
        <h3>More items, every day</h3>
        <p>Continued expansion to cover every produce item in your assortment — including slow movers and seasonal SKUs.</p>
      </div>
      <div class="step">
        <div class="step-num">2</div>
        <h3>Sharper short-horizon</h3>
        <p>Tighter accuracy on the next 1–7 days, where ordering decisions actually happen.</p>
      </div>
      <div class="step">
        <div class="step-num">3</div>
        <h3>Promo and event awareness</h3>
        <p>Better handling of ads, holidays, and weather so your forecasts adjust before sales spike.</p>
      </div>
      <div class="step">
        <div class="step-num">4</div>
        <h3>Store-level tuning</h3>
        <p>Per-store models that pick up the unique buying patterns at each location.</p>
      </div>
    </div>
  </div>

  <div style="display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-top:24px">
    <a class="dl-pdf" href="{slug}-forecast-report.pdf" download>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
      Download {name_short} PDF report
    </a>
    <a class="back-link" href="../../">← All forecast reports</a>
  </div>

  <div class="footer-note">
    EmpowerFresh · Forecast performance update · 2026-05-16
  </div>
</div>
</body>
</html>
"""

def f_int(n):
    return f"{n:,}"

def f_pct(n, signed=False):
    v = float(n) * 100
    return (("+" if v > 0 and signed else "") + f"{v:.1f}%")

def f_pct_growth(n):  # input already a ratio like 1.89
    v = float(n) * 100
    return f"+{v:.0f}%"

for c in DATA['customers']:
    lv = c.get('legacy_v2', {})
    m = c['metrics']
    # error reduction (MAE)
    ai_mae = m['mae']['ai_mean']
    sales_mae = m['mae']['sales_mean']
    err_drop = (sales_mae - ai_mae) / sales_mae if sales_mae else 0

    ctx = {
        'name': html.escape(c['name']),
        'name_short': html.escape(c['name']),
        'slug': c['slug'],
        'v2_pairs_fmt': f_int(lv.get('v2_pairs') or c['unique_pairs']),
        'legacy_pairs_fmt': f_int(lv.get('legacy_pairs', 0)),
        'pairs_growth_pct': f_pct_growth(lv.get('delta_pairs_pct', 0)),
        'products_fmt': f_int(lv.get('v2_products') or c['unique_products']),
        'stores': c['unique_stores'],
        'store_label': 'store' if c['unique_stores'] == 1 else 'stores',
        'ai_win_mae': f_pct(m['mae']['ai_win_rate']),
        'error_drop_pct': f"−{err_drop*100:.0f}%",
        'delta_pairs_fmt': f_int(lv.get('delta_pairs', 0)),
        'unit_pairs_v2_fmt': f_int(lv.get('unit_pairs_v2', 0)),
        'within2': f_pct(m['within2']['ai_mean']),
        'products_growth_pct': f_pct_growth(lv.get('delta_products_pct', 0)),
        'legacy_products_fmt': f_int(lv.get('legacy_products', 0)),
        'v2_products_fmt': f_int(lv.get('v2_products', 0)),
    }
    out_dir = ROOT / 'customers' / c['slug']
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'index.html').write_text(TEMPLATE.format(**ctx))
    print(f"Wrote customers/{c['slug']}/index.html")
