import logging
import os
import sys
import glob
import pandas as pd

# --- Add parent directory to path to import config ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    import config
except ImportError:
    print("Error: config.py not found in the parent directory. Please ensure it exists.")
    sys.exit(1)

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_backtest():
    """Main function to run the backtest."""
    logging.info("--- Starting Backtest for 9:27 Straddle Strategy ---")

    # --- Get all downloaded data files ---
    data_path = os.path.join(os.path.dirname(__file__), 'data')
    all_files = glob.glob(os.path.join(data_path, "*.csv"))

    if not all_files:
        logging.error("No data files found in the /data directory. Please run the data_downloader.py first.")
        return

    # --- Group files by date ---
    dates = sorted(list(set([os.path.basename(f).split('_')[0] for f in all_files])))
    logging.info(f"Found data for {len(dates)} trading days.")

    daily_results = []

    # --- Main Loop: Iterate through each day ---
    for date_str in dates:
        logging.info(f"--- Backtesting for {date_str} ---")

        # Find the relevant files for the day
        try:
            ce_file = glob.glob(os.path.join(data_path, f"{date_str}_*CE.csv"))[0]
            pe_file = glob.glob(os.path.join(data_path, f"{date_str}_*PE.csv"))[0]
        except IndexError:
            logging.warning(f"Could not find both CE and PE data files for {date_str}. Skipping.")
            continue

        # --- Load Data ---
        try:
            ce_df = pd.read_csv(ce_file, parse_dates=['date']).set_index('date')
            pe_df = pd.read_csv(pe_file, parse_dates=['date']).set_index('date')
        except Exception as e:
            logging.error(f"Error loading data for {date_str}. Error: {e}")
            continue

        # --- Simulate Entry at or just after 9:27 AM ---
        entry_time_str = f"{date_str} 09:27:00"
        try:
            # Get the first available candle at or after 9:27
            ce_entry_candle = ce_df[ce_df.index >= entry_time_str].iloc[0]
            pe_entry_candle = pe_df[pe_df.index >= entry_time_str].iloc[0]

            entry_price_ce = ce_entry_candle['close']
            entry_price_pe = pe_entry_candle['close']
            actual_entry_time = ce_entry_candle.name # Timestamp from the index

            logging.info(f"Entry at {actual_entry_time.time()} -> CE Price: {entry_price_ce}, PE Price: {entry_price_pe}")
        except IndexError:
            logging.warning(f"No data available at or after 9:27 AM for {date_str}. Skipping day.")
            continue

        # --- Simulate Monitoring Loop ---
        trade_open = True
        exit_reason = "EOD"
        pnl = 0
        current_pnl = 0

        # The monitoring loop must start AFTER the actual entry time
        monitoring_start_time = actual_entry_time + pd.Timedelta(minutes=1)
        monitoring_df = ce_df.loc[monitoring_start_time : f"{date_str} 15:30:00"]

        for timestamp, row in monitoring_df.iterrows():
            ltp_ce = row['close']
            ltp_pe = pe_df.loc[timestamp]['close']

            # --- Check SL condition ---
            sl_price_ce = entry_price_ce * (1 + config.STOP_LOSS_PERCENT / 100)
            sl_price_pe = entry_price_pe * (1 + config.STOP_LOSS_PERCENT / 100)

            if ltp_ce >= sl_price_ce:
                exit_reason = f"SL Hit on CE"
                pnl = (entry_price_ce - ltp_ce) * config.QUANTITY + (entry_price_pe - ltp_pe) * config.QUANTITY
                trade_open = False
                logging.info(f"Exit at {timestamp} due to {exit_reason}. PnL: {pnl:.2f}")
                break

            if ltp_pe >= sl_price_pe:
                exit_reason = f"SL Hit on PE"
                pnl = (entry_price_ce - ltp_ce) * config.QUANTITY + (entry_price_pe - ltp_pe) * config.QUANTITY
                trade_open = False
                logging.info(f"Exit at {timestamp} due to {exit_reason}. PnL: {pnl:.2f}")
                break

            # --- Check TP condition ---
            current_pnl = (entry_price_ce - ltp_ce) * config.QUANTITY + (entry_price_pe - ltp_pe) * config.QUANTITY
            if current_pnl >= config.TAKE_PROFIT_POINTS:
                exit_reason = "TP Hit"
                pnl = current_pnl
                trade_open = False
                logging.info(f"Exit at {timestamp} due to {exit_reason}. PnL: {pnl:.2f}")
                break

        # --- Handle End-of-Day (EOD) exit ---
        if trade_open:
            eod_time_str = f"{date_str} 15:29:00+05:30" # Use 15:29 to be safe
            try:
                eod_price_ce = ce_df.loc[eod_time_str]['close']
                eod_price_pe = pe_df.loc[eod_time_str]['close']
                pnl = (entry_price_ce - eod_price_ce) * config.QUANTITY + (entry_price_pe - eod_price_pe) * config.QUANTITY
            except KeyError:
                logging.warning(f"No data available at 15:29 for EOD exit on {date_str}. Using last known PnL.")
                pnl = current_pnl # Fallback to last known PnL

            logging.info(f"Exit at EOD. PnL: {pnl:.2f}")

        daily_results.append({
            'date': date_str,
            'pnl': pnl,
            'exit_reason': exit_reason,
            'entry_ce': entry_price_ce,
            'entry_pe': entry_price_pe
        })

    logging.info("--- Backtest Simulation Complete ---")

    # --- Performance Reporting ---
    if daily_results:
        results_df = pd.DataFrame(daily_results)
        generate_performance_report(results_df)
    else:
        logging.warning("No trades were simulated.")

def generate_performance_report(results_df):
    """Calculates and prints a detailed performance report."""
    logging.info("--- Generating Performance Report ---")

    total_pnl = results_df['pnl'].sum()
    num_trades = len(results_df)

    winners = results_df[results_df['pnl'] > 0]
    losers = results_df[results_df['pnl'] <= 0]

    num_winners = len(winners)
    num_losers = len(losers)
    win_rate = (num_winners / num_trades) * 100 if num_trades > 0 else 0

    avg_profit = winners['pnl'].mean() if num_winners > 0 else 0
    avg_loss = losers['pnl'].mean() if num_losers > 0 else 0

    risk_reward_ratio = abs(avg_profit / avg_loss) if avg_loss != 0 else float('inf')

    max_win = results_df['pnl'].max()
    max_loss = results_df['pnl'].min()

    exit_reasons = results_df['exit_reason'].value_counts()

    # --- Print Report ---
    report = f"""
    -------------------------------------------------
    |          Backtest Performance Report          |
    -------------------------------------------------
    | Metric                | Value                 |
    -------------------------------------------------
    | Total P&L             | {total_pnl:,.2f}          |
    | Total Trading Days    | {num_trades:<21} |
    | Winning Days          | {num_winners:<21} |
    | Losing Days           | {num_losers:<21} |
    | Win Rate (%)          | {win_rate:.2f}%                |
    | Average Profit        | {avg_profit:,.2f}          |
    | Average Loss          | {avg_loss:,.2f}          |
    | Risk/Reward Ratio     | {risk_reward_ratio:.2f} : 1              |
    | Max Daily Profit      | {max_win:,.2f}          |
    | Max Daily Loss        | {max_loss:,.2f}          |
    -------------------------------------------------
    | Exit Reasons          | Count                 |
    -------------------------------------------------
    """
    print(report)
    for reason, count in exit_reasons.items():
        print(f"    | {reason:<21} | {count:<21} |")
    print("    -------------------------------------------------")

    # Save the detailed daily results to a CSV file
    report_file_path = os.path.join(os.path.dirname(__file__), 'backtest_results.csv')
    results_df.to_csv(report_file_path, index=False)
    logging.info(f"Detailed daily results saved to {report_file_path}")


if __name__ == "__main__":
    run_backtest()
