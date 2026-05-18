"""Build data.json + detail.csv + universe-per-customer.csv as a current snapshot.

Universe = (customer, store, product) triples where, as of right now in the
support DB, an active order-guide row exists at the store AND a forecast
qualifies under the CAO v2 quality gates (forecast_priority.winning_model_id
IS NOT NULL).

Source: support DB (DATABASE_SUPPORT_URL from AWS Secrets Manager
`claude-credentials`, region us-east-1, profile claude). Read-only.
"""

from __future__ import annotations

import csv
import io
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import mean, median

REPO_ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = REPO_ROOT / "downloads"
DATA_JSON = REPO_ROOT / "data.json"
DETAIL_CSV = DOWNLOADS / "detail.csv"
UNIVERSE_CSV = DOWNLOADS / "universe-per-customer.csv"

SCOPE_CUSTOMERS = (4, 5, 36, 69, 102, 135, 168, 201, 234, 267, 300, 333)

# Direction: True means lower-is-better (AI wins when ai < legacy).
METRIC_DIRECTIONS = {
    "mae": True,
    "mape": True,
    "rmse": True,
    "r2": False,
    "within2": False,
}


def load_db_url() -> str:
    """Fetch DATABASE_SUPPORT_URL from Secrets Manager. Never print it."""
    raw = subprocess.check_output(
        [
            "aws",
            "secretsmanager",
            "get-secret-value",
            "--profile",
            "claude",
            "--region",
            "us-east-1",
            "--secret-id",
            "claude-credentials",
            "--query",
            "SecretString",
            "--output",
            "text",
        ],
        text=True,
    )
    return json.loads(raw)["DATABASE_SUPPORT_URL"]


def run_copy_csv(db_url: str, sql: str) -> list[dict]:
    """Run `COPY (sql) TO STDOUT WITH CSV HEADER` and return list-of-dicts."""
    copy_sql = f"COPY ({sql}) TO STDOUT WITH CSV HEADER"
    out = subprocess.check_output(
        ["psql", db_url, "-v", "ON_ERROR_STOP=1", "-c", copy_sql],
        text=True,
    )
    reader = csv.DictReader(io.StringIO(out))
    return list(reader)


UNIVERSE_SQL = f"""
WITH active_ogmi AS (
  SELECT customer_id, product_id,
         hide_for_store_ids, remove_for_store_ids
  FROM order_guide_master_item
  WHERE is_active
    AND NOT is_ignored
    AND (discontinued_ts IS NULL OR ignore_discontinue_ts IS NOT NULL)
    AND customer_id IN {SCOPE_CUSTOMERS}
),
universe AS (
  SELECT c.id AS customer_id, c.name AS customer_name,
         s.id AS store_id, o.product_id,
         fp.winning_source, fp.winning_model_id
  FROM customer c
  JOIN store s ON s.customer_id = c.id
  JOIN active_ogmi o ON o.customer_id = c.id
  JOIN forecast_priority fp
    ON fp.customer_id = c.id AND fp.store_id = s.id AND fp.product_id = o.product_id
  WHERE c.id IN {SCOPE_CUSTOMERS}
    AND fp.winning_model_id IS NOT NULL
    AND NOT (s.id = ANY(o.hide_for_store_ids))
    AND NOT (s.id = ANY(o.remove_for_store_ids))
),
ai_perf AS (
  SELECT DISTINCT ON (u.customer_id, u.store_id, u.product_id)
         u.customer_id, u.store_id, u.product_id,
         afp.model_type AS ai_model_type,
         afp.model_id AS ai_model_id,
         afp.analysis_run_ts AS ai_run_ts,
         afp.mean_absolute_error AS ai_mae,
         afp.mean_absolute_percentage_error AS ai_mape,
         afp.r_squared AS ai_r2,
         afp.root_mean_squared_error AS ai_rmse,
         afp.percentage_within_2_cases AS ai_within_2
  FROM universe u
  JOIN ai_forecast_performance afp
    ON afp.customer_id = u.customer_id
   AND afp.store_id = u.store_id
   AND afp.product_id = u.product_id
   AND afp.model_id = u.winning_model_id
  ORDER BY u.customer_id, u.store_id, u.product_id, afp.analysis_run_ts DESC
),
sales_perf AS (
  SELECT DISTINCT ON (u.customer_id, u.store_id, u.product_id)
         u.customer_id, u.store_id, u.product_id,
         sp.analysis_run_ts AS sales_run_ts,
         sp.mean_absolute_error AS sales_mae,
         sp.mean_absolute_percentage_error AS sales_mape,
         sp.r_squared AS sales_r2,
         sp.root_mean_squared_error AS sales_rmse,
         sp.percentage_within_2_cases AS sales_within_2
  FROM universe u
  JOIN analysis_product_sales_performance sp
    ON sp.product_id = u.product_id AND sp.store_id = u.store_id
   AND sp.forecasted_items_evaluated >= 10
  ORDER BY u.customer_id, u.store_id, u.product_id, sp.analysis_run_ts DESC
)
SELECT u.customer_id, u.customer_name, u.store_id, u.product_id,
       a.ai_model_type, a.ai_model_id, a.ai_run_ts,
       s.sales_run_ts,
       a.ai_mae, s.sales_mae,
       a.ai_mape, s.sales_mape,
       a.ai_r2, s.sales_r2,
       a.ai_rmse, s.sales_rmse,
       a.ai_within_2, s.sales_within_2,
       u.winning_source
FROM universe u
LEFT JOIN ai_perf a USING (customer_id, store_id, product_id)
LEFT JOIN sales_perf s USING (customer_id, store_id, product_id)
ORDER BY u.customer_id, u.store_id, u.product_id
"""

# Legacy coverage is computed in Python from the universe rows
# (a pair "covered by legacy" = universe row where sales_perf joined and
#  qualified at ≥10 evaluated items, i.e. sales_mae is populated).


def to_float(v):
    if v is None or v == "":
        return None
    return float(v)


def to_int(v):
    if v is None or v == "":
        return None
    return int(v)


def round_or_none(v, places=4):
    return None if v is None else round(v, places)


def compute_metrics(rows: list[dict]) -> dict:
    """Per-metric stats over pairs_with_both (rows where both ai and legacy
    have a value for that metric)."""
    out: dict = {}
    for key, lower_is_better in METRIC_DIRECTIONS.items():
        ai_col, sales_col = f"ai_{key}", f"sales_{key}"
        # normalize "within2" -> "within_2"
        if key == "within2":
            ai_col, sales_col = "ai_within_2", "sales_within_2"
        pairs = [
            (to_float(r[ai_col]), to_float(r[sales_col]))
            for r in rows
            if r.get(ai_col) not in (None, "") and r.get(sales_col) not in (None, "")
        ]
        pairs = [(a, s) for a, s in pairs if a is not None and s is not None]
        n = len(pairs)
        if n == 0:
            out[key] = {
                "n": 0,
                "ai_mean": None, "sales_mean": None,
                "ai_median": None, "sales_median": None,
                "mean_diff": None, "median_diff": None,
                "ai_win_rate": None,
            }
            continue
        ai_vals = [a for a, _ in pairs]
        s_vals = [s for _, s in pairs]
        wins = sum(
            1 for a, s in pairs
            if (a < s if lower_is_better else a > s)
        )
        out[key] = {
            "n": n,
            "ai_mean": round_or_none(mean(ai_vals), 16),
            "sales_mean": round_or_none(mean(s_vals), 16),
            "ai_median": round_or_none(median(ai_vals)),
            "sales_median": round_or_none(median(s_vals)),
            "mean_diff": round_or_none(mean(ai_vals) - mean(s_vals), 16),
            "median_diff": round_or_none(median(ai_vals) - median(s_vals)),
            "ai_win_rate": round_or_none(wins / n, 16),
        }
    return out


def slugify(name: str) -> str:
    return name.lower().replace(" ", "_").replace("'", "").replace(",", "")


def aggregate(rows: list[dict]) -> dict:
    by_customer: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        by_customer[int(r["customer_id"])].append(r)

    def coverage_block(subset: list[dict]) -> dict:
        # Coverage is measured WITHIN the orderable universe. The legacy
        # number answers: "of the pairs in the order today, how many would
        # the legacy model also have qualified to forecast?"
        legacy_subset = [r for r in subset if r.get("sales_mae") not in (None, "")]
        v2_pairs = len(subset)
        v2_products = len({r["product_id"] for r in subset})
        legacy_pairs = len(legacy_subset)
        legacy_products = len({r["product_id"] for r in legacy_subset})
        delta_pairs = v2_pairs - legacy_pairs
        delta_products = v2_products - legacy_products
        return {
            "legacy_pairs": legacy_pairs,
            "legacy_products": legacy_products,
            "v2_pairs": v2_pairs,
            "v2_products": v2_products,
            "delta_pairs": delta_pairs,
            "delta_products": delta_products,
            "delta_pairs_pct": (delta_pairs / legacy_pairs) if legacy_pairs else None,
            "delta_products_pct": (delta_products / legacy_products) if legacy_products else None,
        }

    def base_block(subset: list[dict]) -> dict:
        with_both = [
            r for r in subset
            if r.get("ai_mae") not in (None, "") and r.get("sales_mae") not in (None, "")
        ]
        return {
            "unique_products": len({r["product_id"] for r in subset}),
            "unique_pairs": len(subset),
            "unique_stores": len({r["store_id"] for r in subset}),
            "pairs_with_winning_source": len(subset),
            "pairs_with_ai": len(subset),
            "pairs_with_both": len(with_both),
            "pairs_ai_only": len(subset) - len(with_both),
            "metrics": compute_metrics(subset),
        }

    customers_out: list[dict] = []
    for cid in SCOPE_CUSTOMERS:
        subset = by_customer.get(cid, [])
        if not subset:
            continue
        name = subset[0]["customer_name"]
        block = base_block(subset)
        block["legacy_v2"] = coverage_block(subset)
        customers_out.append({
            "id": cid,
            "name": name,
            "slug": slugify(name),
            **block,
        })

    overall = base_block(rows)
    overall["legacy_v2"] = coverage_block(rows)

    return {
        "generated_at": date.today().isoformat(),
        "as_of": date.today().isoformat(),
        "description": (
            "Current orderable snapshot: active order-guide items at each store, "
            "with the AI forecast that passes CAO v2 quality gates "
            "(forecast_priority.winning_model_id IS NOT NULL)."
        ),
        "overall": overall,
        "customers": customers_out,
    }


def write_detail_csv(rows: list[dict]) -> None:
    DOWNLOADS.mkdir(exist_ok=True)
    cols = [
        "customer_id", "customer_name", "store_id", "product_id",
        "ai_model_type", "ai_model_id", "ai_run_ts", "sales_run_ts",
        "ai_mae", "sales_mae", "ai_mape", "sales_mape",
        "ai_r2", "sales_r2", "ai_rmse", "sales_rmse",
        "ai_within_2", "sales_within_2",
    ]
    with DETAIL_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def write_universe_csv(data: dict) -> None:
    cols = [
        "customer_id", "customer_name", "unique_products",
        "unique_pairs", "pairs_with_winning_source", "unique_stores",
    ]
    with UNIVERSE_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for c in data["customers"]:
            w.writerow({
                "customer_id": c["id"],
                "customer_name": c["name"],
                "unique_products": c["unique_products"],
                "unique_pairs": c["unique_pairs"],
                "pairs_with_winning_source": c["pairs_with_winning_source"],
                "unique_stores": c["unique_stores"],
            })


def main() -> int:
    db_url = load_db_url()
    print("Loading universe + metrics from support DB...", file=sys.stderr)
    rows = run_copy_csv(db_url, UNIVERSE_SQL)
    print(f"  {len(rows):,} universe pairs", file=sys.stderr)

    print("Aggregating...", file=sys.stderr)
    data = aggregate(rows)

    write_detail_csv(rows)
    write_universe_csv(data)
    DATA_JSON.write_text(json.dumps(data, indent=2, default=str))
    print(f"Wrote {DATA_JSON.relative_to(REPO_ROOT.parent)}", file=sys.stderr)
    print(f"Wrote {DETAIL_CSV.relative_to(REPO_ROOT.parent)}", file=sys.stderr)
    print(f"Wrote {UNIVERSE_CSV.relative_to(REPO_ROOT.parent)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
