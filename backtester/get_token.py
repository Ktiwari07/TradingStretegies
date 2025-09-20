import logging
import webbrowser
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- Add parent directory to path to import config ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    import config
except ImportError:
    print("Error: config.py not found. Please ensure it exists in the parent directory.")
    sys.exit(1)

# --- Configuration ---
PORT = 8080
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "request_token.txt")
CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config.py'))
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TokenRequestHandler(BaseHTTPRequestHandler):
    """
    A simple request handler to catch the redirect from Kite and extract the token.
    """
    def do_GET(self):
        # The request_token is in the query parameters
        if 'request_token' in self.path:
            # Extract the token
            query = self.path.split('?')[1]
            params = dict(qc.split("=") for qc in query.split("&"))
            token = params.get("request_token")

            if token:
                logging.info(f"Successfully captured request_token: {token}")
                # Save the token to a file so the main thread can access it
                with open(TOKEN_FILE, "w") as f:
                    f.write(token)

                # Respond to the browser
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>Authentication successful!</h1>")
                self.wfile.write(b"<p>You can close this tab now.</p>")
            else:
                self.send_error(400, "Bad Request: request_token not found in URL.")

        else:
            self.send_error(400, "Bad Request: Invalid redirect URL.")

        # Tell the server to stop after handling this request
        self.server.should_shutdown = True

class StoppableHTTPServer(HTTPServer):
    """
    A custom HTTPServer that can be stopped from a request handler.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.should_shutdown = False

    def serve_forever(self, poll_interval=0.5):
        """Handle one request at a time until `should_shutdown` is True."""
        while not self.should_shutdown:
            self.handle_request()

def update_config_file():
    """
    Reads the token from the temporary file and updates config.py.
    """
    if not os.path.exists(TOKEN_FILE):
        logging.error("Token file not found. Cannot update config.")
        return

    with open(TOKEN_FILE, 'r') as f:
        new_token = f.read().strip()

    logging.info(f"Updating REQUEST_TOKEN in {CONFIG_PATH}")
    with open(CONFIG_PATH, 'r') as f:
        lines = f.readlines()

    with open(CONFIG_PATH, 'w') as f:
        for line in lines:
            if line.strip().startswith("REQUEST_TOKEN"):
                f.write(f'REQUEST_TOKEN = "{new_token}"\n')
            else:
                f.write(line)

    # Clean up the temporary token file
    os.remove(TOKEN_FILE)
    logging.info("config.py updated successfully and temporary token file removed.")

def main():
    """
    Main function to get the request token.
    """
    # --- Step 1: Check for API Key ---
    if not config.API_KEY or config.API_KEY == "YOUR_API_KEY":
        logging.error("API_KEY is not set in config.py. Please add it to proceed.")
        return

    # --- Step 2: Start the local server ---
    server_address = ('127.0.0.1', PORT)
    httpd = StoppableHTTPServer(server_address, TokenRequestHandler)
    logging.info(f"Starting local server on http://127.0.0.1:{PORT}")
    logging.info("The server will shut down automatically after receiving the token.")

    # --- Step 3: Open the browser for the user to log in ---
    login_url = f"https://kite.zerodha.com/connect/login?api_key={config.API_KEY}&v=3"
    logging.info("Opening browser for authentication...")
    logging.info(f"If the browser does not open, please manually visit:\n{login_url}")
    webbrowser.open(login_url)

    # --- Step 4: Wait for the server to handle the request and shut down ---
    httpd.serve_forever()
    logging.info("Server has been shut down.")

    # --- Step 5: Update config.py with the new token ---
    if os.path.exists(TOKEN_FILE):
        update_config_file()
    else:
        logging.error("Failed to retrieve token. The token file was not created.")
        logging.error(f"Please ensure your redirect URL in the Kite app is set to http://127.0.0.1:{PORT}/")

if __name__ == "__main__":
    print("--- Zerodha Request Token Generator ---")
    print("This script will help you get a request_token by logging in through your browser.")
    print(f"Please ensure your Zerodha app's redirect URL is set to: http://127.0.0.1:{PORT}/")

    # Give the user a chance to abort if the URL is not set
    try:
        input("Press Enter to continue or Ctrl+C to exit...")
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        sys.exit(0)

    main()
