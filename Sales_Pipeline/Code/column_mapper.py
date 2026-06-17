"""
column_mapper.py
================
Responsible for mapping arbitrary / human-typed Excel column headers
to the canonical set expected by the staging table.

Uses ``thefuzz`` (Levenshtein) so that common errors like:
  "Customar_Name", "SALE DATE", "Qty", "Prcie_Per_Unit"
are automatically corrected before any data touches the database.
"""

from thefuzz import fuzz, process

from config import Config
from logger import logger

# ── Canonical column names (must match init.sql table columns) ────────────────
CANONICAL_COLUMNS: list[str] = [
    "sale_date",
    "customer_name",
    "city",
    "state",
    "region",
    "product_category",
    "product_name",
    "quantity",
    "price_per_unit",
    "sales_amount",
]

# ── Alias dictionary: canonical → list of accepted variants ──────────────────
# The fuzzy matcher also uses these as a hint corpus.
_ALIASES: dict[str, list[str]] = {
    "sale_date": [
        "sale_date", "saledate", "sale date", "date", "order_date",
        "transaction_date", "sale_dt", "date_of_sale",
    ],
    "customer_name": [
        "customer_name", "customer name", "customername", "client",
        "client_name", "buyer", "customer", "cust_name",
    ],
    "city": [
        "city", "town", "locality", "city_name",
    ],
    "state": [
        "state", "province", "state_name", "st",
    ],
    "region": [
        "region", "area", "zone", "territory",
    ],
    "product_category": [
        "product_category", "category", "product category",
        "productcategory", "cat", "prod_category",
    ],
    "product_name": [
        "product_name", "product", "product name", "item",
        "item_name", "productname", "prod_name", "product_desc",
    ],
    "quantity": [
        "quantity", "qty", "units", "count", "no_of_units",
        "amount_sold", "num_units", "unit_count",
    ],
    "price_per_unit": [
        "price_per_unit", "unit_price", "price", "rate",
        "price per unit", "unitprice", "cost", "selling_price",
    ],
    "sales_amount": [
        "sales_amount", "total", "total_amount", "revenue",
        "sales amount", "total_sales", "amount", "sale_value",
        "order_value", "net_sales",
    ],
}

# Build a flat reverse-lookup:  alias_string → canonical_name
_ALIAS_TO_CANONICAL: dict[str, str] = {
    alias: canonical
    for canonical, aliases in _ALIASES.items()
    for alias in aliases
}
_ALL_ALIASES: list[str] = list(_ALIAS_TO_CANONICAL.keys())


def _normalise(header: str) -> str:
    """Strip, lowercase, and collapse whitespace → underscore."""
    return str(header).strip().lower().replace(" ", "_").replace("-", "_")


def map_columns(
    input_columns: list[str],
    threshold: int | None = None,
) -> dict[str, str]:
    """
    Map each incoming column name to a canonical column name.

    Parameters
    ----------
    input_columns : list of raw column names from the Excel file.
    threshold     : minimum fuzzy score (0-100) to accept a match.
                    Falls back to ``Config.FUZZY_THRESHOLD`` if None.

    Returns
    -------
    dict mapping  original_column_name → canonical_column_name
    for every column that was successfully matched.
    Unmatched columns are omitted (the caller validates completeness).
    """
    if threshold is None:
        threshold = Config.FUZZY_THRESHOLD

    mapping: dict[str, str] = {}

    for col in input_columns:
        normalised = _normalise(col)

        # ── 1. Exact alias match ──────────────────────────────────────────────
        if normalised in _ALIAS_TO_CANONICAL:
            canonical = _ALIAS_TO_CANONICAL[normalised]
            mapping[col] = canonical
            logger.debug(f"Column exact match : '{col}' → '{canonical}'")
            continue

        # ── 2. Fuzzy match against full alias corpus ──────────────────────────
        result = process.extractOne(
            normalised,
            _ALL_ALIASES,
            scorer=fuzz.token_sort_ratio,
        )
        if result is None:
            logger.warning(f"Column no match    : '{col}' — skipped.")
            continue

        best_alias, score, *_ = result
        if score >= threshold:
            canonical = _ALIAS_TO_CANONICAL[best_alias]
            mapping[col] = canonical
            logger.info(
                f"Column fuzzy match : '{col}' → '{canonical}' "
                f"(via '{best_alias}', score={score})"
            )
        else:
            logger.warning(
                f"Column low score   : '{col}' best='{best_alias}' "
                f"score={score} < threshold={threshold} — skipped."
            )

    return mapping


def validate_required_columns(
    mapping: dict[str, str],
) -> tuple[bool, list[str]]:
    """
    Check every canonical column has been mapped.

    Returns
    -------
    (True, [])                  — all required columns present
    (False, [missing, ...])     — list of missing canonical names
    """
    mapped_set = set(mapping.values())
    missing    = [c for c in CANONICAL_COLUMNS if c not in mapped_set]
    return len(missing) == 0, missing