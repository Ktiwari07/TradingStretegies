# Strategy Backtester for 9:27 Nifty Straddle

This project backtests the 9:27 Nifty short straddle strategy using historical data from Zerodha. It is designed to work in conjunction with the live trading bot in the parent directory.

The process is split into two main steps:
1.  **Downloading Data**: A script to fetch one year of historical minute-level data for Nifty and the relevant options.
2.  **Running the Backtest**: A script to simulate the trading strategy on the downloaded data and generate a performance report.

---

## How to Use

### Step 1: Initial Setup

1.  **Configure Credentials**: This backtester uses the same `config.py` file as the live trading bot. Ensure that your `API_KEY` and `API_SECRET` are set in the `config.py` file in the parent directory.
2.  **Generate a Request Token**: The data downloader needs a valid `REQUEST_TOKEN` to access the Zerodha API. Follow the authentication flow described in the main project's README to generate a `request_token` and add it to `config.py`.
3.  **Install Dependencies**: Open a terminal in the `backtester/` directory and run:
    ```bash
    pip install -r requirements.txt
    ```

### Step 2: Download Historical Data

Before you can run a backtest, you must download the necessary historical data.

Run the data downloader script from the `backtester/` directory:
```bash
python data_downloader.py
```
This script will:
-   Connect to the Zerodha API.
-   Iterate through the last 365 days.
-   For each trading day, it will find the correct Nifty option contracts and download the minute-by-minute price data.
-   It will save this data into many small CSV files inside the `backtester/data/` directory.

**Note:** This process can take a significant amount of time (potentially hours) due to API rate limits. It is designed to be run once. If you run it again, it will skip any data that has already been downloaded.

### Step 3: Run the Backtest

Once the data download is complete, you can run the backtester:

```bash
python backtester.py
```

This script will:
-   Read all the data from the `data/` directory.
-   Simulate the 9:27 straddle strategy for each day.
-   Print a detailed **Performance Report** to the console, summarizing the strategy's effectiveness over the past year.
-   Save a detailed log of each day's simulated trade into a file named `backtest_results.csv` in the `backtester/` directory for further analysis.

You can run the backtester as many times as you like after the data has been downloaded.
