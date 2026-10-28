"""Assign parameter codes to the analysis groups of config/parameter_groups.yaml.

Shared by the pipeline and the UI so both group codes identically.
"""

from __future__ import annotations

from typing import Any, Mapping

import pandas as pd

OTHER = "other"


def assign_group(code: str, category: str | None, groups: Mapping[str, Mapping[str, Any]]) -> str:
    """Return the first group whose rule matches the code, else ``"other"``.

    A group matches on an exact code (``codes``), on the dictionary category
    (``category``, i.e. ``P_categorie``) or on a code prefix (``prefixes``).
    """
    for key, rule in groups.items():
        if code in rule.get("codes", ()):
            return key
        if category is not None and rule.get("category") == category:
            return key
        if any(code.startswith(p) for p in rule.get("prefixes", ())):
            return key
    return OTHER


def add_group_column(df: pd.DataFrame, groups: Mapping[str, Mapping[str, Any]],
                     code_col: str = "parameter", category_col: str = "category") -> pd.DataFrame:
    """Return a copy of ``df`` with a ``parameter_group`` column."""
    codes = df[code_col].astype(str).tolist()
    cats = df[category_col].tolist() if category_col in df else [None] * len(df)
    cats = [None if pd.isna(c) else str(c) for c in cats]
    lookup = {key: assign_group(*key, groups) for key in set(zip(codes, cats))}
    out = df.copy()
    out["parameter_group"] = [lookup[key] for key in zip(codes, cats)]
    return out


def group_label(key: str, groups: Mapping[str, Mapping[str, Any]]) -> str:
    """Human-readable label for a group key."""
    return groups.get(key, {}).get("label", "Other parameters" if key == OTHER else key)
