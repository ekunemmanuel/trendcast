# 📈 TrendCast — Universal AI Demand Forecasting

TrendCast is an end-to-end AI demand forecasting engine and web application. Upload any time series dataset (**CSV**, **XLSX**, or **XLS**), and TrendCast will auto-detect columns, handle transaction aggregations, engineer frequency-aware lag features, and train an **XGBoost** model — comparing its performance directly against a naive baseline.

Runs 100% locally on your machine with no external API keys, cloud subscriptions, or GPU required.

---

## ✨ Features

- **🌐 Interactive Web Application**: Drag-and-drop web UI with real-time analysis progress, MAPE accuracy comparisons, and high-resolution chart downloads.
- **📄 Universal File Support**: Works out of the box with `.csv`, `.xlsx`, and `.xls` files.
- **🔍 Smart Auto-Detection**: Priority-based auto-detection for date and target value columns.
- **⏰ Multi-Frequency Support**: Automatically detects **Hourly**, **Daily**, **Weekly**, **Monthly**, **Quarterly**, or **Yearly** data and adapts lag structures accordingly.
- **🛒 Automatic Transaction Aggregation**: Seamlessly aggregates individual retail order logs (e.g. thousands of coffee sales) into daily/monthly totals.
- **📊 Honest Model Evaluation**: Evaluates XGBoost using Mean Absolute Percentage Error (MAPE) against a naive "last period value" baseline on held-out test data.

---

## 📁 Repository Structure

```
trendcast/
├── app.py              # Flask Web Server & API endpoints
├── analyze.py          # Core analysis, XGBoost training & visualization engine
├── load_data.py        # Smart data loading, column auto-detection & aggregation
├── features.py         # Adaptive frequency detection & lag feature engineering
├── train.py            # CLI entry point for command-line runs
├── requirements.txt    # Python package dependencies
├── samples/            # Pre-loaded sample datasets (Car Sales, Coffee Orders, etc.)
├── static/             # Web UI frontend assets (index.html, CSS, JS) and generated plots
└── uploads/            # Temporary directory for uploaded files
```

---

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/your-username/trendcast.git
cd trendcast
```

### 2. Create a virtual environment & install dependencies
```bash
python -m venv .venv

# On Windows:
.venv\Scripts\activate
pip install -r requirements.txt

# On macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run the Web Application
```bash
python app.py
```
Open your browser to **`http://localhost:5000`**. You can try the 4 built-in sample datasets or drag and drop your own CSV/Excel files!

---

## 💻 CLI Usage

You can also run TrendCast directly from the command line:

```bash
# Synthetic data (no file needed)
python train.py --source synthetic

# Local CSV file
python train.py --source csv --path path/to/your_data.csv

# Custom column names (optional if auto-detection works)
python train.py --source csv --path my_sales.csv --date-col Month --target-col Sales

# Public CSV URL
python train.py --source url --url https://raw.githubusercontent.com/jbrownlee/Datasets/master/monthly-car-sales.csv
```

---

## 🔬 How It Works

1. **Load & Clean**: Normalizes input data, parses dates, and converts values to numeric types.
2. **Aggregate Transactions**: If multiple transactions exist for the same period (e.g., individual store orders), values are automatically summed into time-step totals.
3. **Detect Frequency**: Calculates median date gaps to identify hourly, daily, weekly, monthly, quarterly, or yearly frequencies.
4. **Engineer Features**: Creates calendar indicators, rolling averages, and adaptive lags pruned to the dataset size.
5. **Chronological Holdout Split**: Holds out recent periods (e.g. 30 days for daily, 12 months for monthly) to prevent future data leakage.
6. **Train & Evaluate**: Trains XGBoost Regressor and computes MAPE against the Naive Baseline on the holdout test set.

---

## 🛡️ License & Contributing

Built for local, privacy-first demand forecasting. Pull requests and feedback are welcome!
