# TrendCast — Full Project Explainer

## What Is This Project?

TrendCast is a **demand forecasting pipeline**. In plain English: you give it historical sales numbers over time, and it uses a machine learning model to **predict what future sales will look like**. It then honestly compares that prediction against a simple "dumb" baseline to show you whether the ML model is actually worth using.

It requires no internet connection, no API key, and no GPU — it runs entirely on your laptop.

---

## The Data — `monthly_car_sales.csv`

The dataset you're using is **108 months (9 years) of monthly car sales** recorded from January 1960 to December 1968. It has exactly two columns:

| Column | What It Means |
|--------|--------------|
| `Month` | The year and month (e.g. `1960-01` = January 1960) |
| `Sales` | How many cars were sold that month (e.g. `6550`) |

A quick look at the pattern in the data:

- **Seasonality**: Sales are consistently higher in spring/summer (April–June) and lower in winter (Jan–Feb). This repeats every year.
- **Trend**: Sales gradually grow over the 9-year period.
- **Noise**: There are random fluctuations month to month on top of the pattern.

This makes it an ideal dataset for a forecasting model — there's **real structure to learn**, not just random noise.

---

## The 5-Step Pipeline

Here's exactly what happens when you run `python train.py`:

### Step 1 — Load the Data (`load_data.py`)
The CSV is read in and cleaned into a simple two-column table: one date column, one number column. Rows with missing or unparseable values are dropped. The script also checks you have at least 30 rows (you have 108, so no problem).

### Step 2 — Detect the Frequency (`features.py`)
The code looks at the gaps between dates and figures out whether your data is **daily, weekly, or monthly**. For your dataset, the gaps are ~30 days, so it correctly identifies it as **monthly** data. This matters because it determines which features to build next.

### Step 3 — Build Features (`features.py`)
This is the most important step. A raw date column means nothing to a machine learning model — you need to turn time into numbers the model can reason about. TrendCast creates these feature columns from your data:

| Feature | What It Is |
|---------|-----------|
| `month` | The calendar month (1–12) — captures seasonal patterns |
| `quarter` | Q1/Q2/Q3/Q4 — a broader seasonal signal |
| `lag_1` | Last month's sales — "what happened most recently?" |
| `lag_2` | Sales 2 months ago |
| `lag_3` | Sales 3 months ago |
| `lag_12` | Sales exactly one year ago — the key seasonality feature |
| `rolling_mean_3` | Average of the last 3 months — smooths short-term noise |
| `rolling_mean_12` | Average of the last 12 months — captures the yearly trend |

> [!IMPORTANT]
> All lag features look **backwards only** — the model never sees future data. This is critical. A common mistake in time series ML is accidentally letting the model "cheat" by peeking at future values.

After building these features, 12 rows at the start are dropped (they don't have enough history to compute `lag_12`), leaving **96 usable rows**.

### Step 4 — Train/Test Split (`train.py`)
The data is split **chronologically** — never randomly. The most recent **12 months** (all of 1968) are held out as the test set. The model is trained on everything before that (1960–1967), then asked to predict 1968 without ever having seen it.

```
[───────── Training: 1960 → 1967 ─────────][── Test: 1968 ──]
```

### Step 5 — Train Two Models & Compare (`train.py`)

Two models are trained and compared on the 12 held-out months:

#### 🟠 The Naive Baseline
The simplest possible "model": **predict that next month's sales will be the same as this month's sales**. This is the bar the ML model must beat to prove it's actually useful.

#### 🟢 XGBoost
An industry-standard gradient boosting model. It learns from all 8 feature columns to produce more nuanced predictions. It's trained with:
- 200 decision trees
- Max depth of 3 (keeps each tree simple to avoid overfitting)
- Learning rate of 0.05 (small steps = more stable learning)

---

## The Results

```
Naive Baseline MAPE :  17.0%
XGBoost MAPE        :   9.6%
→ XGBoost beats the baseline by 43% relative error reduction
```

**MAPE** = Mean Absolute Percentage Error. Lower is better.

- The naive baseline was off by **17%** on average each month.
- XGBoost was off by only **9.6%** — nearly cutting the error in half.
- This 43% improvement shows the model genuinely learned the seasonal patterns from `lag_12` and the calendar features.

---

## The Output Plot — `forecast_plot.png`

![Forecast vs Actual](file:///c:/Users/Pablo/Documents/projects/trendcast/forecast_plot.png)

The chart shows the final 12-month test period (all of 1968):

| Line | Meaning |
|------|---------|
| **Grey** | Recent training history (context) |
| **Black (dots)** | The actual real sales figures |
| **Teal (dots)** | XGBoost's predictions |
| **Orange dashed** | Naive baseline predictions |

You can see that XGBoost (teal) tracks the actual values (black) much more closely than the naive baseline (orange), especially around the mid-year peak and the year-end decline.

---

## The 5 Files at a Glance

| File | Role |
|------|------|
| `load_data.py` | Reads and cleans the CSV; can also download from a URL or generate fake data |
| `features.py` | Converts raw dates into lag/rolling/calendar features the model can use |
| `train.py` | Orchestrates everything: splits data, trains both models, prints results, saves the plot |
| `monthly_car_sales.csv` | Your real-world dataset (108 months of car sales, 1960–1968) |
| `requirements.txt` | The 5 Python libraries needed: pandas, numpy, xgboost, scikit-learn, matplotlib |

---

## How to Run It Again

```powershell
# Using your CSV
.venv\Scripts\python train.py --source csv --path monthly_car_sales.csv --date-col Month --target-col Sales

# Using built-in synthetic data (no CSV needed — good for quick tests)
.venv\Scripts\python train.py --source synthetic

# Using any public CSV from the internet
.venv\Scripts\python train.py --source url --url https://raw.githubusercontent.com/jbrownlee/Datasets/master/monthly-car-sales.csv
```

> [!TIP]
> Swap in your own CSV with any date + numeric column and TrendCast will auto-detect the columns and handle it the same way. It works for daily, weekly, or monthly data.
