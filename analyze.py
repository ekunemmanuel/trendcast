"""
analyze.py — Intelligent TrendCast Analysis & Visualization Engine

Features:
  - Adaptive frequency-based train/test splits
  - Smart X-axis date formatting using matplotlib.dates
  - Frequency-aware training history display range (shows full annual trend)
  - Full support for CSV, XLSX, XLS
"""

import os
import uuid

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import mean_absolute_percentage_error
from xgboost import XGBRegressor

from features import build_features
from load_data import load_csv, load_excel

PLOTS_DIR = os.path.join("static", "plots")


def _calculate_adaptive_test_size(df_len: int, freq: str, requested_test: int = None) -> int:
    """
    Computes an appropriate holdout test size based on dataset frequency and length.
    """
    if requested_test is not None and requested_test > 0:
        return min(requested_test, max(2, df_len // 4))

    if freq == "hourly":
        default_test = 168  # 1 week
    elif freq == "daily":
        default_test = 30   # 1 month
    elif freq == "weekly":
        default_test = 12   # ~1 quarter
    elif freq == "monthly":
        default_test = 12   # 1 year
    elif freq == "quarterly":
        default_test = 4    # 1 year
    else:  # yearly
        default_test = 2

    # Constrain test size so at least 15 rows remain for training
    max_test = max(2, df_len - 15)
    test_size = min(default_test, max_test, max(3, df_len // 4))
    return max(1, test_size)


def _get_history_window(freq: str) -> int:
    """Returns how many past training periods to display on the plot."""
    if freq == "hourly":
        return 336  # 2 weeks
    elif freq == "daily":
        return 365  # 1 year
    elif freq == "weekly":
        return 104  # 2 years
    elif freq == "monthly":
        return 36   # 3 years
    elif freq == "quarterly":
        return 24   # 6 years
    else:
        return 20   # 20 years


def analyze_file(file_path: str, date_col: str = None, target_col: str = None,
                 test_size: int = None) -> dict:
    """
    Runs full TrendCast pipeline on an uploaded file and returns analysis dictionary.
    """
    os.makedirs(PLOTS_DIR, exist_ok=True)

    ext = os.path.splitext(file_path)[1].lower()
    if ext in (".xlsx", ".xls"):
        df, date_col, target_col = load_excel(file_path, date_col, target_col)
    elif ext == ".csv":
        df, date_col, target_col = load_csv(file_path, date_col, target_col)
    else:
        raise ValueError(f"Unsupported file format '{ext}'. Upload .csv, .xlsx, or .xls.")

    raw_row_count = len(df)

    # Build features & detect frequency
    df, feature_cols, freq = build_features(df, date_col, target_col)
    usable_rows = len(df)

    # Determine adaptive test split size
    effective_test = _calculate_adaptive_test_size(usable_rows, freq, test_size)

    if usable_rows - effective_test < 10:
        raise ValueError(
            f"Not enough data: {usable_rows} usable observations after building lag features. "
            "TrendCast needs at least 15 observations for model training and evaluation."
        )

    train_df = df.iloc[:-effective_test]
    test_df = df.iloc[-effective_test:]

    X_train, y_train = train_df[feature_cols], train_df[target_col]
    X_test, y_test = test_df[feature_cols], test_df[target_col]

    # Train XGBoost Regressor
    model = XGBRegressor(
        n_estimators=250, max_depth=4, learning_rate=0.04, random_state=42
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    baseline_preds = test_df["naive_baseline"].values

    # Calculate MAPE
    mape_model = round(mean_absolute_percentage_error(y_test, preds) * 100, 1)
    mape_baseline = round(mean_absolute_percentage_error(y_test, baseline_preds) * 100, 1)

    improvement_pct = None
    if mape_model < mape_baseline and mape_baseline > 0:
        improvement_pct = round((mape_baseline - mape_model) / mape_baseline * 100, 1)

    # ── High-Quality Plot Visualization ──────────────────────────────────────────
    plot_filename = f"plot_{uuid.uuid4().hex[:10]}.png"
    plot_path = os.path.join(PLOTS_DIR, plot_filename)

    BG = "#0c1121"
    GRID_CLR = "#1e293b"

    fig, ax = plt.subplots(figsize=(11, 4.8))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    # Select training history window appropriate for frequency
    hist_window = _get_history_window(freq)
    recent_train = train_df.tail(hist_window)

    # Plot lines
    ax.plot(
        recent_train[date_col], recent_train[target_col],
        label="Training History", color="#475569", linewidth=1.5, zorder=1
    )
    ax.plot(
        test_df[date_col], y_test,
        label="Actual Ground Truth", marker="o", color="#f1f5f9",
        linewidth=2.2, markersize=4.5, zorder=4
    )
    ax.fill_between(test_df[date_col], y_test, alpha=0.05, color="#f1f5f9", zorder=2)

    ax.plot(
        test_df[date_col], preds,
        label="XGBoost Forecast", marker="o", color="#6366f1",
        linewidth=2.4, markersize=5.0, zorder=5
    )
    ax.fill_between(test_df[date_col], preds, alpha=0.12, color="#6366f1", zorder=3)

    ax.plot(
        test_df[date_col], baseline_preds,
        label="Naive Baseline (Last Value)", linestyle="--", color="#f59e0b",
        linewidth=1.6, alpha=0.80, zorder=3
    )

    # ── Intelligent X-Axis Date Formatting ──
    combined_dates = pd.concat([recent_train[date_col], test_df[date_col]])
    total_days = (combined_dates.max() - combined_dates.min()).days

    if total_days <= 60:
        date_fmt = mdates.DateFormatter("%b %d")
    elif total_days <= 365:
        # Check if dates fall within a single calendar year
        if combined_dates.dt.year.nunique() == 1:
            date_fmt = mdates.DateFormatter("%b %d")
        else:
            date_fmt = mdates.DateFormatter("%b %Y")
    else:
        date_fmt = mdates.DateFormatter("%b %Y")

    ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=10))
    ax.xaxis.set_major_formatter(date_fmt)
    plt.xticks(rotation=30, ha="right", color="#94a3b8", fontsize=8.5)

    # Y-axis formatting & styling
    ax.tick_params(colors="#64748b", labelsize=8.5)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID_CLR)
    ax.grid(True, color=GRID_CLR, linewidth=0.8, linestyle="-")
    ax.set_axisbelow(True)

    ax.legend(
        facecolor="#111827", edgecolor="#1e293b",
        labelcolor="#cbd5e1", fontsize=8.5, framealpha=0.92,
        loc="upper left"
    )

    # Frequency description string
    freq_desc = {
        "hourly": "Hourly",
        "daily": "Daily",
        "weekly": "Weekly",
        "monthly": "Monthly",
        "quarterly": "Quarterly",
        "yearly": "Yearly"
    }.get(freq, freq.capitalize())

    ax.set_title(
        f"Demand Forecast vs Actual  ·  {freq_desc} Data  ·  {effective_test}-period Test Holdout",
        color="#f1f5f9", fontsize=10.5, fontweight="600", pad=12
    )

    plt.tight_layout()
    plt.savefig(plot_path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)

    return {
        "date_col": date_col,
        "target_col": target_col,
        "frequency": freq,
        "row_count": raw_row_count,
        "usable_rows": usable_rows,
        "test_size": effective_test,
        "mape_model": mape_model,
        "mape_baseline": mape_baseline,
        "improvement_pct": improvement_pct,
        "plot_url": f"/static/plots/{plot_filename}",
        "features": feature_cols,
    }
