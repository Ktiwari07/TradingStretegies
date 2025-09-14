import logging
import os
import sys
import time
from datetime import datetime, timedelta
import pandas as pd

# --- Add parent directory to path to import config ---
# This allows us to reuse the API credentials from the live bot's config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    import config
except ImportError:
    print("Error: config.py not found in the parent directory. Please ensure it exists.")
    sys.exit(1)

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# We need a KiteConnect instance to work with
from kiteconnect import KiteConnect

def initialize_kite_api():
    """Handles the Zerodha Kite Connect API authentication."""
    logging.info("Initializing Kite Connect API...")
    kite = KiteConnect(api_key=config.API_KEY)

    # The user must have a valid request_token in config.py for this to work
    if not config.REQUEST_TOKEN:
        login_url = kite.login_url()
        logging.error("REQUEST_TOKEN is not set in config.py.")
        logging.info(f"Please generate one by visiting this URL: {login_url}")
        logging.info("Then paste it into config.py and rerun the downloader.")
        sys.exit(1)

    try:
        data = kite.generate_session(config.REQUEST_TOKEN, api_secret=config.API_SECRET)
        access_token = data["access_token"]
        kite.set_access_token(access_token)
        logging.info("Authentication successful.")
        return kite
    except Exception as e:
        logging.error(f"Authentication failed: {e}")
        sys.exit(1)

def main():
    """Main function to download historical data."""
    kite = initialize_kite_api()

    # --- Define Date Range (last 365 days) ---
    to_date = datetime.now()
    from_date = to_date - timedelta(days=365)
    logging.info(f"Data download range: {from_date.date()} to {to_date.date()}")

    # --- Get NFO Instruments ---
    # We need this list to find the correct option contracts
    try:
        logging.info("Fetching NFO instrument list...")
        instruments_list = kite.instruments("NFO")
        instrument_df = pd.DataFrame(instruments_list)
        # Convert expiry to datetime objects for easier comparison
        instrument_df['expiry'] = pd.to_datetime(instrument_df['expiry']).dt.date
        logging.info("Successfully fetched and processed NFO instruments.")
    except Exception as e:
        logging.error(f"Could not fetch NFO instruments: {e}")
        sys.exit(1)

    # --- Main Loop: Iterate through each day ---
    current_date = from_date
    while current_date <= to_date:
        date_str = current_date.strftime('%Y-%m-%d')

        # We only care about weekdays
        if current_date.weekday() >= 5: # 5 = Saturday, 6 = Sunday
            current_date += timedelta(days=1)
            continue

        logging.info(f"--- Processing data for {date_str} ---")

        # --- Define the time for which we need the Nifty price ---
        time_9_27 = current_date.replace(hour=9, minute=27, second=0, microsecond=0)

        # --- 1. Get Nifty LTP at 9:27 to find the ATM strike ---
        try:
            # We fetch a 5-minute candle to ensure we get a price point
            nifty_instrument_token = 256265 # Instrument token for NIFTY 50 index
            nifty_hist_data = kite.historical_data(nifty_instrument_token, time_9_27 - timedelta(minutes=5), time_9_27, "minute")
            if not nifty_hist_data:
                raise ValueError("Nifty 50 historical data not found, likely a holiday.")

            nifty_ltp_at_9_27 = nifty_hist_data[-1]['close']
            atm_strike = round(nifty_ltp_at_9_27 / 50) * 50
            logging.info(f"Nifty LTP at 9:27 was {nifty_ltp_at_9_27}. ATM Strike: {atm_strike}")

        except Exception as e:
            logging.warning(f"Could not fetch Nifty LTP for {date_str}. Might be a holiday. Error: {e}")
            current_date += timedelta(days=1)
            time.sleep(1) # sleep to be safe
            continue

        # --- 2. Find the nearest weekly expiry ---
        # Filter for Nifty options that have not expired yet
        options_df = instrument_df[
            (instrument_df['name'] == 'NIFTY') &
            (instrument_df['expiry'] >= current_date.date()) &
            (instrument_df['strike'] == atm_strike) &
            (instrument_df['instrument_type'].isin(['CE', 'PE']))
        ]
        nearest_expiry = options_df['expiry'].min()
        logging.info(f"Nearest expiry for {date_str} is {nearest_expiry}")

        # --- 3. Get instrument tokens for the CE and PE options ---
        ce_instrument = options_df[(options_df['instrument_type'] == 'CE') & (options_df['expiry'] == nearest_expiry)]
        pe_instrument = options_df[(options_df['instrument_type'] == 'PE') & (options_df['expiry'] == nearest_expiry)]

        if ce_instrument.empty or pe_instrument.empty:
            logging.error(f"Could not find option contracts for strike {atm_strike} on {date_str}.")
            current_date += timedelta(days=1)
            continue

        ce_token = ce_instrument.iloc[0]['instrument_token']
        ce_symbol = ce_instrument.iloc[0]['tradingsymbol']
        pe_token = pe_instrument.iloc[0]['instrument_token']
        pe_symbol = pe_instrument.iloc[0]['tradingsymbol']
        logging.info(f"Found CE: {ce_symbol} ({ce_token}), PE: {pe_symbol} ({pe_token})")

        # --- 4. Download historical data for Nifty, CE, and PE for the whole day ---
        from_datetime_full_day = current_date.replace(hour=9, minute=15, second=0)
        to_datetime_full_day = current_date.replace(hour=15, minute=30, second=0)

        instruments_to_download = {
            'NIFTY50': nifty_instrument_token,
            ce_symbol: ce_token,
            pe_symbol: pe_token
        }

        for symbol, token in instruments_to_download.items():
            # Check if file already exists to avoid re-downloading
            file_path = f"backtester/data/{date_str}_{symbol}.csv"
            if os.path.exists(file_path):
                logging.info(f"Data for {symbol} on {date_str} already exists. Skipping.")
                continue

            try:
                logging.info(f"Downloading data for {symbol} on {date_str}...")
                hist_data = kite.historical_data(token, from_datetime_full_day, to_datetime_full_day, "minute")
                df = pd.DataFrame(hist_data)

                if df.empty:
                    logging.warning(f"No data returned for {symbol} on {date_str}.")
                    continue

                # 5. Save data to CSV
                df.to_csv(file_path, index=False)
                logging.info(f"Successfully saved data to {file_path}")

            except Exception as e:
                logging.error(f"Failed to download or save data for {symbol} on {date_str}. Error: {e}")

            # Rate limiting between each download call
            time.sleep(0.5)

        # This sleep is crucial to avoid hitting API rate limits between days
        time.sleep(1)

        current_date += timedelta(days=1)

    logging.info("Data download script finished.")


if __name__ == "__main__":
    main()
