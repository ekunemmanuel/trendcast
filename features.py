"""
features.py — Adaptive Frequency & Feature Engineering

Features:
  - Supports Hourly, Daily, Weekly, Monthly, Quarterly, Yearly data
  - Dynamically prunes lag windows so short datasets aren't wiped out
  - Generates calendar features, lag features, and rolling averages
"""

import numpy as np
import pandas as pd


def detect_frequency(dates: pd.Series) -> str:
    """
    Detect dataset frequency based on the median time delta between sorted dates.
    """
    diffs = dates.sort_values().diff().dropna()
    if len(diffs) == 0:
        return "monthly"

    median_seconds = diffs.dt.total_seconds().median()
    median_days = median_seconds / 86400.0

    if median_days <= 0.1:
        return "hourly"
    elif median_days <= 3.5:
        return "daily"
    elif median_days <= 12:
        return "weekly"
    elif median_days <= 45:
        return "monthly"
    elif median_days <= 120:
        return "quarterly"
    else:
        return "yearly"


# Default candidate configurations per frequency
FREQUENCY_CONFIG = {
    "hourly":    {"lags": [1, 2, 24, 168],    "rolling": [6, 24]},
    "daily":     {"lags": [1, 7, 14, 30, 90], "rolling": [7, 30]},
    "weekly":    {"lags": [1, 2, 4, 12, 52],  "rolling": [4, 12]},
    "monthly":   {"lags": [1, 2, 3, 6, 12],   "rolling": [3, 12]},
    "quarterly": {"lags": [1, 2, 4, 8],       "rolling": [2, 4]},
    "yearly":    {"lags": [1, 2, 3],          "rolling": [2, 3]},
}


def build_features(df: pd.DataFrame, date_col: str, target_col: str):
    """
    Turns a (date, target) DataFrame into a full feature matrix.
    Safely prunes lags to fit the dataset length.
    """
    df = df.sort_values(date_col).reset_index(drop=True).copy()
    freq = detect_frequency(df[date_col])
    config = FREQUENCY_CONFIG[freq]

    n_rows = len(df)

    # Calculate maximum lag allowed so we retain at least 12 rows after dropna()
    max_allowed_lag = max(1, n_rows - 15)

    lags = [l for l in config["lags"] if l <= max_allowed_lag]
    if not lags:
        lags = [1]

    rolling_windows = [w for w in config["rolling"] if w <= max_allowed_lag]

    # Calendar Features
    df["month"] = df[date_col].dt.month
    df["quarter"] = df[date_col].dt.quarter

    if freq in ("daily", "hourly"):
        df["dayofweek"] = df[date_col].dt.dayofweek
        df["day"] = df[date_col].dt.day
        df["is_weekend"] = (df[date_col].dt.dayofweek >= 5).astype(int)

    if freq == "hourly":
        df["hour"] = df[date_col].dt.hour

    # Lag features
    for lag in lags:
        df[f"lag_{lag}"] = df[target_col].shift(lag)

    # Rolling average features
    for w in rolling_windows:
        df[f"rolling_mean_{w}"] = df[target_col].shift(1).rolling(w).mean()

    # Naive baseline: "predict last period's value"
    df["naive_baseline"] = df[target_col].shift(1)

    # Drop NaNs created by lagging
    df = df.dropna().reset_index(drop=True)

    feature_cols = [
        c for c in df.columns
        if c not in [date_col, target_col, "naive_baseline"]
    ]

    return df, feature_cols, freq
