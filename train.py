"""
train.py

Loads data (your CSV, a public URL, or synthetic data), builds forecasting
features, trains an XGBoost model, and compares it against a naive baseline
("predict last period's value") on held-out data. Saves a plot of the
result.

Usage:
    python train.py --source synthetic
    python train.py --source csv --path mydata.csv --date-col Date --target-col Sales
    python train.py --source url --url https://example.com/data.csv
"""

import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_percentage_error
from xgboost import XGBRegressor

from features import build_features
from load_data import generate_synthetic, load_csv, load_url


def parse_args():
    p = argparse.ArgumentParser(description="Train and evaluate a demand forecasting model.")
    p.add_argument("--source", choices=["csv", "url", "synthetic"], default="synthetic")
    p.add_argument("--path", help="Path to a local CSV (required for --source csv)")
    p.add_argument("--url", help="URL to a CSV (required for --source url)")
    p.add_argument("--date-col", default=None, help="Name of the date column (auto-detected if omitted)")
    p.add_argument("--target-col", default=None, help="Name of the target/value column (auto-detected if omitted)")
    p.add_argument("--test-size", type=int, default=12, help="Number of most recent periods to hold out for testing")
    p.add_argument("--output", default="forecast_plot.png", help="Where to save the result plot")
    return p.parse_args()


def load_data(args):
    if args.source == "csv":
        if not args.path:
            raise SystemExit("--path is required when --source csv")
        return load_csv(args.path, args.date_col, args.target_col)
    if args.source == "url":
        if not args.url:
            raise SystemExit("--url is required when --source url")
        return load_url(args.url, args.date_col, args.target_col)
    return generate_synthetic()


def main():
    args = parse_args()

    df, date_col, target_col = load_data(args)
    print(f"Loaded {len(df)} rows. date_col='{date_col}', target_col='{target_col}'")

    df, feature_cols, freq = build_features(df, date_col, target_col)
    print(f"Detected frequency: {freq}. {len(df)} rows usable after building lag features.")
    print(f"Features used: {feature_cols}")

    test_size = min(args.test_size, max(4, len(df) // 5))
    if len(df) - test_size < 20:
        raise SystemExit(
            f"Not enough data: {len(df)} rows total, need at least 20 for training "
            f"plus {test_size} for testing. Try a longer dataset or a smaller --test-size."
        )

    train_df = df.iloc[:-test_size]
    test_df = df.iloc[-test_size:]

    X_train, y_train = train_df[feature_cols], train_df[target_col]
    X_test, y_test = test_df[feature_cols], test_df[target_col]

    model = XGBRegressor(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=42)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    baseline_preds = test_df["naive_baseline"].values

    mape_model = mean_absolute_percentage_error(y_test, preds) * 100
    mape_baseline = mean_absolute_percentage_error(y_test, baseline_preds) * 100

    print(f"\nResults on {test_size} held-out periods:")
    print(f"  Naive baseline MAPE : {mape_baseline:5.1f}%")
    print(f"  XGBoost MAPE        : {mape_model:5.1f}%")

    if mape_model < mape_baseline:
        improvement = (mape_baseline - mape_model) / mape_baseline * 100
        print(f"  -> XGBoost beats the baseline, {improvement:.0f}% relative error reduction.")
    else:
        print("  -> XGBoost did NOT beat the naive baseline. See README 'If the model")
        print("     doesn't beat the baseline' section for things to try.")

    plt.figure(figsize=(10, 5))
    recent_train = train_df.tail(20)
    plt.plot(recent_train[date_col], recent_train[target_col], label="Train (recent)", color="#999999")
    plt.plot(test_df[date_col], y_test, label="Actual", marker="o", color="#1a1a1a")
    plt.plot(test_df[date_col], preds, label="XGBoost forecast", marker="o", color="#2c6e6b")
    plt.plot(test_df[date_col], baseline_preds, label="Naive baseline", linestyle="--", color="#c9772e")
    plt.legend()
    plt.title(f"Forecast vs Actual ({freq} data, {test_size}-period holdout)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(args.output, dpi=150)
    print(f"\nSaved plot to {args.output}")


if __name__ == "__main__":
    main()
