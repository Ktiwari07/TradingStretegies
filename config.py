# --- ZERODHA API CREDENTIALS ---
# Enter your API Key and API Secret below.
# To get your credentials, you need to create an app on Kite Connect Developer:
# https://kite.trade/docs/connect/v3/getting-started/
API_KEY = "0eorlgl5aufz2vb9"
API_SECRET = "ari48qjt4t2to74yhy9rkqwo3owbmj0k"

# --- USER TOKENS ---
# After the first successful login, the script will generate an access_token.
# You can paste it here to avoid logging in every time, but it expires daily.
# The script is designed to generate this token automatically.
REQUEST_TOKEN = "k8XOSetHnv4vtzElAIo3FJeS310WilAQ"  # Get this after manual login
ACCESS_TOKEN = ""                     # This will be generated and can be stored

# --- STRATEGY PARAMETERS ---
TRADING_INSTRUMENT = "NIFTY 50"
PRODUCT_TYPE = "MIS"  # Margin Intraday Squareoff
ORDER_TYPE = "MARKET"

# The quantity of Nifty lots to trade. 1 lot = 50 quantity for Nifty 50.
# Example: For 2 lots, set QUANTITY = 100
QUANTITY = 1125

# Exit conditions
TAKE_PROFIT_POINTS = 25000  # In absolute currency amount (e.g., 25000 for ₹25,000)
STOP_LOSS_PERCENT = 30.0    # 30% stop loss on the premium of an individual leg
