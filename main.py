import logging
import schedule
import time
import sys
from kiteconnect import KiteConnect
import pandas as pd

# Import configuration
try:
    import config
except ImportError:
    print("Error: config.py not found. Please create it based on the sample.")
    sys.exit(1)

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Main Trading Logic ---
def initialize_kite_api():
    """Handles the Zerodha Kite Connect API authentication."""
    logging.info("Initializing Kite Connect API...")
    kite = KiteConnect(api_key=config.API_KEY)

    # Check if we already have a valid access token
    if config.ACCESS_TOKEN:
        try:
            kite.set_access_token(config.ACCESS_TOKEN)
            # Validate the token by fetching profile information
            kite.profile()
            logging.info("Access token is valid. Authentication successful.")
            return kite
        except Exception as e:
            logging.warning(f"Existing access token is invalid, generating a new one. Reason: {e}")
            # Invalidate the stored token
            config.ACCESS_TOKEN = ""

    # If no access token, or if it's invalid, generate a new one
    # First, the user needs to manually get a request_token
    if not config.REQUEST_TOKEN:
        login_url = kite.login_url()
        logging.info(f"Please login to Kite and get the request_token. URL: {login_url}")
        logging.info("After logging in, you will be redirected to a URL. Copy the 'request_token' from that URL and paste it into config.py")
        sys.exit(1)

    try:
        data = kite.generate_session(config.REQUEST_TOKEN, api_secret=config.API_SECRET)
        access_token = data["access_token"]
        kite.set_access_token(access_token)

        # We can optionally save this to the config file for reuse, but it expires daily.
        # For this script, we'll just use it for the current session.
        logging.info("Authentication successful. Access token generated for the session.")

        return kite
    except Exception as e:
        logging.error(f"Authentication failed: {e}")
        sys.exit(1)


# Global variables to store instrument data and order details
instrument_df = None
placed_orders = []

def get_instrument_df(kite):
    """Fetches and caches the instrument list from Kite."""
    global instrument_df
    if instrument_df is None:
        logging.info("Fetching instrument list...")
        instruments = kite.instruments("NFO")
        instrument_df = pd.DataFrame(instruments)
        # Save to CSV for future use to avoid repeated API calls (optional)
        # instrument_df.to_csv("nfo_instruments.csv", index=False)
    return instrument_df

def execute_straddle_strategy(kite):
    """Contains the core logic for the 9:27 AM Nifty straddle."""
    logging.info("--- Executing the 9:27 AM Nifty Straddle Strategy ---")

    # 1. Get instrument data
    inst_df = get_instrument_df(kite)

    # 2. Get Nifty 50 LTP
    try:
        quote = kite.quote("NSE:NIFTY 50")
        if not quote:
            logging.error("Could not fetch quote for NIFTY 50.")
            return
        nifty_ltp = quote["NSE:NIFTY 50"]['last_price']
        logging.info(f"Nifty 50 LTP is: {nifty_ltp}")
    except Exception as e:
        logging.error(f"Error fetching Nifty LTP: {e}")
        return

    # 3. Calculate ATM strike
    atm_strike = round(nifty_ltp / 50) * 50
    logging.info(f"Calculated ATM strike: {atm_strike}")

    # 4. Find nearest weekly expiry
    nifty_options = inst_df[(inst_df['name'] == 'NIFTY') &
                            (inst_df['segment'] == 'NFO-OPT')]
    nearest_expiry = sorted(nifty_options['expiry'].unique())[0]
    logging.info(f"Nearest weekly expiry: {nearest_expiry.date()}")

    # 5. Construct option symbols
    ce_symbol = f"NIFTY{nearest_expiry.strftime('%y%b').upper()}{atm_strike}CE"
    pe_symbol = f"NIFTY{nearest_expiry.strftime('%y%b').upper()}{atm_strike}PE"

    # Let's verify these symbols exist in the instrument list
    ce_instrument = nifty_options[(nifty_options['tradingsymbol'].str.upper() == ce_symbol.upper()) & (nifty_options['strike'] == atm_strike)]
    pe_instrument = nifty_options[(nifty_options['tradingsymbol'].str.upper() == pe_symbol.upper()) & (nifty_options['strike'] == atm_strike)]

    if ce_instrument.empty or pe_instrument.empty:
        logging.error(f"Could not find trading symbols for CE: {ce_symbol} or PE: {pe_symbol}. Please check the symbol format.")
        # Fallback for different symbol formats if necessary
        ce_symbol = f"NIFTY{nearest_expiry.strftime('%d%b%y').upper()}{atm_strike}CE"
        pe_symbol = f"NIFTY{nearest_expiry.strftime('%d%b%y').upper()}{atm_strike}PE"
        logging.info(f"Trying alternative format: {ce_symbol}, {pe_symbol}")
        ce_instrument = nifty_options[nifty_options['tradingsymbol'].str.upper() == ce_symbol.upper()]
        pe_instrument = nifty_options[nifty_options['tradingsymbol'].str.upper() == pe_symbol.upper()]
        if ce_instrument.empty or pe_instrument.empty:
             logging.error(f"Alternative format also failed. Exiting strategy.")
             return

    ce_tradingsymbol = ce_instrument.iloc[0]['tradingsymbol']
    pe_tradingsymbol = pe_instrument.iloc[0]['tradingsymbol']
    logging.info(f"Found Call Option: {ce_tradingsymbol}")
    logging.info(f"Found Put Option: {pe_tradingsymbol}")

    # 6. Place Orders
    orders_to_place = [
        {'symbol': ce_tradingsymbol, 'type': 'CE'},
        {'symbol': pe_tradingsymbol, 'type': 'PE'}
    ]

    for order in orders_to_place:
        try:
            order_id = kite.place_order(
                variety=kite.VARIETY_REGULAR,
                exchange=kite.EXCHANGE_NFO,
                tradingsymbol=order['symbol'],
                transaction_type=kite.TRANSACTION_TYPE_SELL,
                quantity=config.QUANTITY,
                product=config.PRODUCT_TYPE,
                order_type=config.ORDER_TYPE,
                price=None,
                validity=None,
                disclosed_quantity=None,
                trigger_price=None,
                squareoff=None,
                stoploss=None,
                trailing_stoploss=None,
                tag="StraddleBot_v1"
            )
            logging.info(f"Placed SELL order for {order['symbol']} with Order ID: {order_id}")
            placed_orders.append({'symbol': order['symbol'], 'order_id': order_id, 'status': 'OPEN', 'type': order['type']})
        except Exception as e:
            logging.error(f"Failed to place order for {order['symbol']}: {e}")
            # If one leg fails, we should ideally cancel the other. For now, we log and stop.
            return

    # After placing orders, we need to get their entry price and start monitoring.
    logging.info("Straddle orders placed successfully. Moving to monitoring.")
    monitor_and_exit_positions(kite)


def exit_all_positions(kite, reason):
    """Squares off all open positions."""
    logging.info(f"--- Exiting all positions due to: {reason} ---")
    for order in placed_orders:
        if order.get('status') == 'OPEN':
            try:
                exit_order_id = kite.place_order(
                    variety=kite.VARIETY_REGULAR,
                    exchange=kite.EXCHANGE_NFO,
                    tradingsymbol=order['symbol'],
                    transaction_type=kite.TRANSACTION_TYPE_BUY,
                    quantity=config.QUANTITY,
                    product=config.PRODUCT_TYPE,
                    order_type=config.ORDER_TYPE,
                    price=None,
                    validity=None,
                    disclosed_quantity=None,
                    trigger_price=None,
                    squareoff=None,
                    stoploss=None,
                    trailing_stoploss=None,
                    tag="StraddleBot_Exit_v1"
                )
                logging.info(f"Placed BUY order for {order['symbol']} to exit. Order ID: {exit_order_id}")
                order['status'] = 'CLOSED'
            except Exception as e:
                logging.error(f"Failed to place exit order for {order['symbol']}: {e}")

    # Clear the placed_orders list after closing all
    placed_orders.clear()
    # We can exit the script after the job is done for the day
    sys.exit("Trading task for the day is complete.")


def monitor_and_exit_positions(kite):
    """Monitors open positions for TP/SL and exits them."""
    if not placed_orders:
        logging.warning("No open orders to monitor.")
        return

    # --- Step 1: Get Entry Prices ---
    logging.info("Fetching execution details for entry orders...")
    time.sleep(2) # Give a moment for orders to execute and appear in order book

    for order in placed_orders:
        try:
            order_history = kite.order_history(order['order_id'])
            executed_trades = [trade for trade in order_history if trade['status'] == 'COMPLETE']
            if executed_trades:
                # Calculate average execution price
                total_price = sum(t['quantity'] * t['average_price'] for t in executed_trades)
                total_quantity = sum(t['quantity'] for t in executed_trades)
                avg_price = total_price / total_quantity
                order['entry_price'] = avg_price
                logging.info(f"Entry price for {order['symbol']} is {avg_price}")
            else:
                logging.error(f"Order for {order['symbol']} did not execute. Cancelling strategy.")
                exit_all_positions(kite, "Entry order failed to execute.")
                return
        except Exception as e:
            logging.error(f"Could not fetch order history for {order['order_id']}: {e}")
            exit_all_positions(kite, "Error fetching order history.")
            return

    # --- Step 2: Start Monitoring Loop ---
    logging.info("--- Starting Position Monitoring Loop ---")
    while True:
        try:
            # Get current time to check for market close
            current_time = time.localtime()
            if current_time.tm_hour >= 15 and current_time.tm_min >= 30:
                exit_all_positions(kite, "Market Closing Time")
                break

            # Fetch LTP for all open positions
            symbols_to_quote = ['NFO:' + o['symbol'] for o in placed_orders if o.get('status') == 'OPEN']
            if not symbols_to_quote:
                logging.info("All positions seem to be closed. Stopping monitor.")
                break

            quotes = kite.ltp(symbols_to_quote)

            total_pnl = 0
            for order in placed_orders:
                if order.get('status') == 'OPEN':
                    ltp = quotes['NFO:' + order['symbol']]['last_price']
                    entry_price = order['entry_price']

                    # Calculate PnL for this leg
                    pnl_leg = (entry_price - ltp) * config.QUANTITY
                    total_pnl += pnl_leg

                    # --- Check SL condition ---
                    stop_loss_price = entry_price * (1 + config.STOP_LOSS_PERCENT / 100)
                    if ltp >= stop_loss_price:
                        logging.warning(f"STOP LOSS HIT for {order['symbol']}! LTP: {ltp}, SL Price: {stop_loss_price}")
                        exit_all_positions(kite, f"SL Hit for {order['symbol']}")
                        return # Exit the function

            # --- Check TP condition ---
            logging.info(f"Current PnL: {total_pnl:.2f}")
            if total_pnl >= config.TAKE_PROFIT_POINTS:
                logging.info(f"TAKE PROFIT HIT! Total PnL: {total_pnl:.2f}")
                exit_all_positions(kite, "Take Profit Hit")
                return # Exit the function

            time.sleep(1) # Interval between checks

        except Exception as e:
            logging.error(f"An error occurred in the monitoring loop: {e}")
            time.sleep(5) # Wait a bit longer if there's an API error


def main():
    """The main function to run the trading bot."""
    logging.info("Trading Bot Started.")

    # Initialize the Kite API client
    kite = initialize_kite_api()

    # Get instrument data once at the start
    get_instrument_df(kite)

    # Schedule the strategy to run at 9:27 AM every day
    # We pass the 'kite' object to the scheduled job
    schedule.every().day.at("09:27").do(execute_straddle_strategy, kite=kite)

    logging.info("Scheduler is running. Waiting for 9:27 AM to execute the strategy.")

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    logging.info("Starting the Nifty Straddle Trading Bot.")
    logging.info("Please ensure your config.py is set up correctly.")
    logging.info("The bot will first attempt to authenticate and then wait for the scheduled time.")
    main()
