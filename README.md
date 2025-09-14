# Nifty 50 Automated Straddle Trading Bot

This script automates a specific options trading strategy for the Nifty 50 index on the Zerodha platform. It is designed to run daily, executing a short straddle at a specific time and monitoring the position for pre-defined exit conditions.

**DISCLAIMER: This is a software tool, not financial advice. Automated trading involves significant risk, including the risk of losing your entire capital. You are solely responsible for any trades placed by this bot and any financial outcomes. Use it at your own risk.**

---

## How It Works

1.  **Authentication**: The script authenticates with your Zerodha Kite Connect account.
2.  **Scheduling**: It waits until **9:27 AM** on a trading day.
3.  **Trade Entry**: At 9:27 AM, it automatically:
    -   Fetches the current price of the Nifty 50 index.
    -   Determines the At-The-Money (ATM) strike price.
    -   Places a **short straddle**, which involves selling one ATM Call Option and one ATM Put Option for the nearest weekly expiry.
4.  **Position Monitoring**: Once the orders are executed, the script continuously monitors the position.
5.  **Exit Conditions**: The script will automatically square off (exit) **both** positions if either of these conditions is met:
    -   **Take Profit**: The total combined profit from the two options reaches **₹25,000**.
    -   **Stop Loss**: The price of **either** the call or the put option increases by **30%** from its entry price.
    -   **End of Day**: If neither of the above conditions is met, it will exit the positions at 3:30 PM.

---

## Setup Instructions

Follow these steps carefully to set up and run the trading bot.

### Step 1: Install Dependencies

First, you need to install the required Python libraries. Open your terminal or command prompt and run the following command from the project's root directory:

```bash
pip install -r requirements.txt
```

### Step 2: Configure Your Credentials

Open the `config.py` file. You need to fill in your Zerodha API credentials.

1.  **API Key and Secret**:
    -   Log in to the [Kite Connect Developer Console](https://developers.kite.trade/apps) to create an app and get your `API_KEY` and `API_SECRET`.
    -   Paste these values into the `config.py` file.

    ```python
    API_KEY = "YOUR_API_KEY"
    API_SECRET = "YOUR_API_SECRET"
    ```

2.  **Strategy Parameters**: You can also adjust the `QUANTITY` and other parameters in this file if needed. By default, it's set to trade 1 lot (50 quantity).

### Step 3: The Authentication Flow (First Run)

Zerodha's API requires a manual login once per day to authorize the script.

1.  **Make sure `REQUEST_TOKEN` is empty** in `config.py`.
2.  **Run the script** from your terminal:
    ```bash
    python main.py
    ```
3.  The script will fail to authenticate and will **print a login URL** in the console. It will look something like this:
    ```
    INFO: Please login to Kite and get the request_token. URL: https://kite.trade/connect/login?v=3&api_key=YOUR_API_KEY...
    ```
4.  **Copy this URL** and paste it into your web browser.
5.  Log in with your Zerodha credentials (ID, password, and 2FA).
6.  After a successful login, you will be **redirected to a blank page**. The URL in your browser's address bar will now contain the `request_token`. It will look like this:
    `https://your-redirect-url.com/?status=success&request_token=THIS_IS_THE_TOKEN_YOU_NEED`
7.  **Copy the `request_token` value** from the URL.
8.  **Paste this token** into the `config.py` file:
    ```python
    REQUEST_TOKEN = "PASTE_THE_TOKEN_HERE"
    ```
9.  Save the `config.py` file.

### Step 4: Run the Bot

Now that you have the `request_token`, you are ready to run the bot.

Run the script again from your terminal:

```bash
python main.py
```

This time, the script will successfully authenticate, and you will see a message that the scheduler is running. It will then wait until 9:27 AM to place the trades. You can leave the script running in the background. It will automatically handle the trade entry, monitoring, and exit.