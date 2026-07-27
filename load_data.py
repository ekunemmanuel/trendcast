"""
load_data.py — Smart Data Loading & Column Auto-Detection

Supports:
  - CSV files (.csv)
  - Excel files (.xlsx, .xls)
  - Public URLs
  - Synthetic data generation

Features:
  - Smart priority-based date and numeric column auto-detection
  - Filter out low-variance date columns (e.g. metadata timestamps)
  - Automatic transaction aggregation (sums multiple orders/transactions per day/month)
"""

import numpy as np
import pandas as pd

# Keywords to prioritize date columns
DATE_KEYWORDS = [
    "date", "time", "month", "year", "day", "period",
    "timestamp", "saledate", "created_at", "order_date", "dt"
]

# Keywords to prioritize numeric target columns
TARGET_KEYWORDS = [
    "sales", "value", "target", "units", "revenue", "amount",
    "qty", "quantity", "count", "price", "ma", "total", "money", "demand"
]


def _auto_detect_columns(df, date_col, target_col):
    """
    Intelligent priority-based auto-detection of date and numeric target columns.
    """
    # ── 1. Date Column Auto-Detection ──
    if date_col is None or date_col not in df.columns:
        date_candidates = []

        for col in df.columns:
            col_str = str(col).strip().lower()
            try:
                # Try parsing as datetime with mixed format support
                parsed = pd.to_datetime(df[col], errors="coerce", format="mixed")
                valid_ratio = parsed.notna().mean()
                n_unique = parsed.nunique()

                # Must be mostly parseable and have variance (> 3 distinct dates)
                if valid_ratio > 0.70 and n_unique > 3:
                    priority = 0
                    # Check keyword match
                    for kw in DATE_KEYWORDS:
                        if kw in col_str:
                            priority += 10
                            break
                    # Bonus for higher unique date ratio (prevents picking fixed metadata dates)
                    priority += (n_unique / len(df)) * 5

                    date_candidates.append((priority, col))
            except Exception:
                continue

        if not date_candidates:
            raise ValueError(
                "Could not auto-detect a date column. Please specify your date column explicitly."
            )

        # Sort by priority score descending
        date_candidates.sort(key=lambda x: x[0], reverse=True)
        date_col = date_candidates[0][1]

    # ── 2. Target Column Auto-Detection ──
    if target_col is None or target_col not in df.columns:
        numeric_candidates = []

        for col in df.columns:
            if col == date_col:
                continue

            col_str = str(col).strip().lower()
            s_num = pd.to_numeric(df[col], errors="coerce")
            valid_ratio = s_num.notna().mean()
            n_unique = s_num.nunique()

            if valid_ratio > 0.60 and n_unique > 2:
                priority = 0
                for kw in TARGET_KEYWORDS:
                    if kw in col_str:
                        priority += 10
                        break

                # Penalize columns that look like auto-increment IDs or constant categories
                if col_str in ("id", "index", "unnamed: 0", "type", "category"):
                    priority -= 20
                if s_num.min() == 1 and s_num.max() == len(df):  # 1..N sequence
                    priority -= 15

                numeric_candidates.append((priority, col))

        if not numeric_candidates:
            raise ValueError(
                "Could not auto-detect a numeric target column. Please specify your value/target column explicitly."
            )

        numeric_candidates.sort(key=lambda x: x[0], reverse=True)
        target_col = numeric_candidates[0][1]

    return date_col, target_col


def _finalize(df, date_col, target_col):
    """
    Cleans, parses, aggregates transactional data if duplicate dates exist,
    and returns a clean (df, date_col, target_col) table sorted by date.
    """
    df = df.copy()

    # Convert date and target
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce", format="mixed")
    df[target_col] = pd.to_numeric(df[target_col], errors="coerce")

    # Drop invalid rows
    df = df.dropna(subset=[date_col, target_col])

    if len(df) == 0:
        raise ValueError("No valid numeric data found in the selected columns after cleaning.")

    # ── Handle Transactional / Duplicate Dates ──
    # Check if there are duplicate date stamps or timestamps with time component
    has_time = (df[date_col].dt.hour != 0).any() or (df[date_col].dt.minute != 0).any()
    has_dups = df[date_col].duplicated().any()

    if has_time or has_dups:
        # Normalize timestamps to date level if spans multiple days
        df[date_col] = df[date_col].dt.normalize()
        # Sum target values per day (e.g. aggregate transaction orders into daily sales)
        df = df.groupby(date_col, as_index=False)[target_col].sum()

    df = df[[date_col, target_col]].sort_values(date_col).reset_index(drop=True)

    if len(df) < 15:
        raise ValueError(
            f"Only {len(df)} usable data points after cleaning and aggregating duplicates. "
            "TrendCast needs at least 15 time periods to detect patterns and build forecasts."
        )

    return df, date_col, target_col


def load_csv(path, date_col=None, target_col=None):
    df = pd.read_csv(path)
    date_col, target_col = _auto_detect_columns(df, date_col, target_col)
    return _finalize(df, date_col, target_col)


def load_excel(path, date_col=None, target_col=None):
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        raise ImportError("openpyxl is required for Excel support. Install with: pip install openpyxl")
    df = pd.read_excel(path, engine="openpyxl")
    date_col, target_col = _auto_detect_columns(df, date_col, target_col)
    return _finalize(df, date_col, target_col)


def load_url(url, date_col=None, target_col=None):
    df = pd.read_csv(url)
    date_col, target_col = _auto_detect_columns(df, date_col, target_col)
    return _finalize(df, date_col, target_col)


def generate_synthetic(n_days=730, seed=42):
    rng = np.random.default_rng(seed)
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=n_days, freq="D")
    t = np.arange(n_days)

    trend = 50 + t * 0.05
    weekend_bump = np.where(dates.dayofweek.isin([5, 6]), 12, 0)
    weekly_season = 10 * np.sin(2 * np.pi * t / 7) + weekend_bump
    yearly_season = 20 * np.sin(2 * np.pi * (t - 60) / 365.25)
    noise = rng.normal(0, 8, n_days)

    sales = trend + weekly_season + yearly_season + noise
    sales = np.clip(sales, 5, None).round(1)

    df = pd.DataFrame({"date": dates, "sales": sales})
    return _finalize(df, "date", "sales")
